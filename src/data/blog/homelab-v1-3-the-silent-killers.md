---
author: Kayra
pubDatetime: 2025-01-09T00:00:00Z
title: "Homelab v1.3 – The Silent Killers: DNS, Firewalls, and the Unbound Crash"
slug: homelab-v1-3-the-silent-killers
featured: false
draft: false
tags: ["selfhosting", "kubernetes", "networking"]
category: journal
format: writeup
description: Four hours of debugging silent failures. A crashed DNS resolver, a CNI power struggle between Flannel and Cilium, an IPAM overlap that hijacked my LAN, and a hairpin loop I "fixed" by building a BGP highway before I realized I was fixing the wrong thing.
---

It always bites you back when you don't expect it. Remember the firewall rules I set in the beginning? They came back for me.

**Level 1:** Before I could even start debugging the cluster, I got locked out of my own nodes. I had destroyed and re-provisioned the VMs to fix a configuration drift, but when I tried to SSH back into `10.0.0.11`:

```text
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@    WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!     @
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
IT IS POSSIBLE THAT SOMEONE IS DOING SOMETHING NASTY!
```

SSH caches the unique identity (host public key) of every server in a `known_hosts` file. Since I replaced the VM but kept the IP (`10.0.0.11`), my laptop suspected a Man-in-the-Middle attack. I had to wipe the old fingerprint to tell my laptop "It's okay, I know this guy."

```bash
ssh-keygen -R 10.0.0.11
```

**Level 2:** Now that I have access, let's debug.

My K3s installation command was hanging silently. No errors, just an infinite timeout. I enabled logging on my firewall rules to see what was getting dropped, and I found something weird:

```text
Jan 1 18:40:31 LAN Block Lab to Home LAN ... 10.0.0.11:60075 -> 192.168.1.1:53 UDP
```

My cluster was cheating on my firewall with my router. My firewall was correctly blocking it because of the "Block Lab to Home" rule.

Why was it asking the Home Router? It should have been asking pfSense (`10.0.0.1`). The issue was in my provisioning script. I was cloning a Debian template that defaulted to the home network DNS settings. I updated the script to enforce the lab DNS and it worked.

**Level 3:** Even after fixing the DNS IP on the nodes, resolution was still failing. This time, there were no logs.

I started debugging it:

- **Validate Layer 1/2:** Were the IPs correct? Yes.
- **Validate Upstream:** Could pfSense itself resolve `google.com`? Yes. So the WAN link was fine.
- **Packet Capture:** I ran a listener on the pfSense interface. I saw the packets coming from the K3s node (`10.0.0.11`), but pfSense wasn't replying. It was just ghosting them.
- **Service Check:** Since the network was fine, the service had to be broken.

I checked the DNS Resolver status. It looked enabled. But when I randomly tried to save the settings without changing anything, the UI finally showed the error:

```text
fatal error: failed local-zone, local-data configuration ... Empty label
```

The Unbound DNS service wasn't running at all. It had crashed silently on startup because the System Hostname and Domain were empty. I suspect this happened when I restored the config backup after manually editing the XML previously. But we will never know... Once I re-entered the Hostname and Domain, the service started.

Side note: since I rely heavily on AI, for this problem they were as helpful as it gets :). LLM 1 was confident it was my "Block Lab to Home" rule and that I had to remove it. LLM 2 said it was a complex NAT issue and suggested outbound rules and all. LLM 3 hallucinated config options that didn't even exist. Guess I will still have a job for a few more months.

## Quality of Life

Now let's do some quality of life edits.

I have 3 nodes for HA, but in the `kubeconfig` there is a hardcoded IP for node 1. So if that node crashes, the API will be unreachable even when the other 2 nodes are fine, which defeats the purpose. So I needed a VIP, a virtual IP address. I used something called kube-vip for that: `10.0.0.100` is the IP of whichever leader node is active.

I applied the change, but then, level 4: I needed to explicitly define the pool:

- Range: `10.0.0.200` - `10.0.0.220` (For LoadBalancer services)
- VIP: `10.0.0.100` (For the Control Plane)

Once it was there, it worked until level 5: K3s comes with a default networking stack called Flannel, and I installed Cilium on top of it, so 2 network systems were fighting each other: conflicting network policies. The easy way out was to reinstall with Flannel stopped:

```bash
curl -sfL https://get.k3s.io | sh -s - server --flannel-backend=none --disable-network-policy
```

The reason I chose Cilium is that I wanted to use eBPF for better observability and performance. (When I read this now, I don't even remember what that means...)

**Level 6:** I installed Cilium with the defaults, and then the nodes didn't have internet access anymore. They couldn't even ping the gateway.

It took me a while of debugging, reinstalling, and trying before I found the root cause. The traffic was being swallowed by Cilium. My Lab Network is `10.0.0.0/24`. Cilium's default Pod Network is `10.0.0.0/8`. Cilium installed a route claiming the entire `10.x.x.x` range. When the OS tried to reach the physical gateway (`10.0.0.1`), the kernel routing table prioritized the Cilium interface because it thought `10.0.0.1` belonged to that network. I had to uninstall Cilium and reinstall it with a correctly scoped IPAM (IP Address Management) configuration that didn't overlap with my physical network: `--cluster-pool-ipv4-cidr=10.42.0.0/16`

Now, Cilium defaults to VXLAN, which creates a virtual tunnel network that sits on top of the physical network. It works out of the box, but I wanted native routing: packets routed normally without the overhead of wrapping them in UDP headers. I reinstalled with `routingMode=native`. Some things worked, but Hubble (the observability UI) was unreachable, and DNS lookups were timing out.

I looked at pfSense. I saw traffic from my nodes hitting the firewall and getting dropped. I spent hours adjusting rules. I even deleted the Hubble TLS secrets because an LLM suggested they might be stale (bad idea. They don't regenerate automatically, so I had to rebuild the certificate authority).

At one point I did a happy dance after adding the `10.43.0.0/16` network to the firewall, so the DNS resolved and it worked. But then I paused and thought about what the hell I am doing with my life, and contemplated jumping out of the window. At that moment it was the second floor and I wouldn't have died. Why was I making the nodes that were next to each other go through the firewall to talk to each other?!

I stopped looking at the firewall and looked at the source: the kernel routing table on Node 1 (`ip route`). I expected to see routes telling Node 1 how to reach the other nodes' PodCIDRs (like `10.42.0.0/24` via `10.0.0.13`, and `10.42.2.0/24` via `10.0.0.12`).

That route didn't exist. Because the route was missing, the Linux kernel fell back to the Default Gateway (`10.0.0.1` - pfSense):

1. Packet leaves Node 1.
2. Goes to pfSense.
3. pfSense doesn't know where `10.42.1.x` is (or blocks it).
4. Packet dies.

This is called Hairpinning. I was unintentionally forcing internal cluster traffic to go out to the router and back. There is a specific flag in Cilium for this exact scenario: `autoDirectNodeRoutes=true`

As soon as I enabled this, Cilium injected the correct routes into the Linux kernel on every node:

```text
default via 10.0.0.1 dev eth0 proto static
10.0.0.0/24 dev eth0 proto kernel scope link src 10.0.0.11
10.42.0.0/24 via 10.0.0.13 dev eth0 proto kernel
10.42.1.0/24 via 10.42.1.171 dev cilium_host proto kernel src 10.42.1.171
10.42.1.171 dev cilium_host proto kernel scope link
10.42.2.0/24 via 10.0.0.12 dev eth0 proto kernel
```

Now that this level is cleared, I could finally set up BGP correctly. I didn't need BGP for the nodes to talk to each other (that's what `autoDirectNodeRoutes` handled), but I did need it to access the pods and services from my desktop.

Good so far, we are getting somewhere. A few notable mistakes: struggling with the golden image that had the network config of the home network and not the lab. And while debugging BGP, I disabled one rule and thought the setup worked without it, because it did. But it was working because pfSense states were not cleared, so it was stale.

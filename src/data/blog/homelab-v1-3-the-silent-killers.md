---
author: Kayra
pubDatetime: 2025-01-09T00:00:00Z
title: "Homelab v1.3 — The Silent Killers: DNS, Firewalls, and the Unbound Crash"
slug: homelab-v1-3-the-silent-killers
featured: false
draft: false
tags: ["selfhosting"]
category: journal
series: homelab
seriesOrder: 1.3
description: Four hours of debugging silent failures — a crashed DNS resolver, a CNI power struggle between Flannel and Cilium, an IPAM overlap that hijacked my LAN, and a hairpin loop I "fixed" by building a BGP highway before I realized I was fixing the wrong thing.
---

## 1.3.1 Introduction: The "It Should Just Work" Fallacy

We have the hardware, the secured network, the "Golden Image" templates, and our supply chain in place. In theory, I should run one script, sip my coffee, and watch a Kubernetes cluster appear. In reality, I spent 4 hours staring at the terminal and screaming at a firewall log that was not even appearing.

The transition from "Infrastructure Provisioning" to "Cluster Bootstrapping" hit a wall of silent failures. Here is how I debugged the "Black Box" of networking to finally get my K3s cluster running.

## 1.3.2 The SSH Panic: "Someone is doing something nasty!"

Before I could even start debugging the cluster, I got locked out of my own nodes. I had destroyed and re-provisioned the VMs to fix a configuration drift, but when I tried to SSH back into `10.0.0.11`:

```text
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@    WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!     @
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
IT IS POSSIBLE THAT SOMEONE IS DOING SOMETHING NASTY!
```

This looks terrifying, but in a lab environment, it's usually benign. SSH caches the unique identity of every server in a `known_hosts` file. Since I replaced the VM but kept the IP (`10.0.0.11`), my laptop suspected a Man-in-the-Middle attack. I had to wipe the old fingerprint to tell my laptop "It's okay, I know this guy."

```bash
ssh-keygen -R 10.0.0.11
```

## 1.3.3 The Firewall Mystery: Why is my Cluster talking to my Router?

My K3s installation command was hanging silently. No errors, just an infinite timeout. I enabled logging on my Firewall Rules to see what was getting dropped, and I found something bizarre:

```text
Jan 1 18:40:31 LAN Block Lab to Home LAN ... 10.0.0.11:60075 -> 192.168.1.1:53 UDP
```

My cluster was cheating on my firewall with my router. My firewall was correctly blocking it because of the "Block Lab to Home" rule.

Why was it asking the Home Router? It should have been asking pfSense (`10.0.0.1`). The issue was in my **Provisioning Script**. I was cloning a Debian template that defaulted to the home network DNS settings. I hadn't explicitly forced the `nameserver` in the `qm set` command, so the new VMs inherited the "wrong" DNS server. I updated `02-provision-k3s-nodes.sh` to strictly enforce the Lab DNS and proceeded.

## 1.3.4 The "Unbound" Crash: When the Firewall Ghosts You

Even after fixing the DNS IP on the nodes, resolution was _still_ failing. This time, there were no logs.

I started debugging it:

- **Validate Layer 1/2:** Were the IPs correct? Yes.
- **Validate Upstream:** Could pfSense itself resolve `google.com`? Yes. So the WAN link was fine.
- **Packet Capture:** I ran a listener on the pfSense interface. I saw the packets coming from the K3s node (`10.0.0.11`), but pfSense wasn't replying. It was just ghosting them.
- **Service Check:** Since the network was fine, the service had to be broken.

I checked the DNS Resolver status. It looked enabled. But when I randomly tried to save the settings without changing anything, the UI finally vomited the error:

```text
fatal error: failed local-zone, local-data configuration ... Empty label
```

The Unbound DNS service wasn't running at all. It had crashed silently on startup because the **System Hostname and Domain** were empty. I suspect this happened when I restored the config backup after manually editing the XML previously. Once I re-entered the Hostname and Domain, the service started, and the floodgates opened.

## 1.3.5 The AI Gaslighting: Trust but Verify

A quick sidebar on using AI for debugging. Obviously, I am relying hard on LLMs. However, in debugging this issue it was a disaster.

When the internet didn't work, one model confidently told me to delete my "Block Lab to Home" rule (compromising my security). Another insisted it was a complex NAT issue requiring advanced outbound rules. A third hallucinated configuration options that didn't exist.

They were all wrong. The issue was a crashed service and a bad template config.

## 1.3.6 The VIP Entrance: Making an Entrance

Before tackling the complex pod networking, I had a more immediate problem: accessing the cluster.

I set up a 3-node cluster to achieve high availability. The issue is that my `kubeconfig` file pointed to `10.0.0.11` (Node 1). If Node 1 goes down for maintenance or crashes, the API is unreachable, even if the other two nodes are fine. I needed a **Virtual IP (VIP)**, a stable address that floats between the nodes. That's what **kube-vip** exists for. It uses ARP leader election to broadcast a shared IP (`10.0.0.100`) from whichever node is currently the "leader."

I applied the manifests, expecting it to just work. It didn't. The logs showed: `no address pools could be found`

I thought kube-vip would just know to use the IP I put in the manifest. In reality, it needed a specific Cloud Provider configuration map to define the allowable range. I had to patch the config to explicitly define the pool:

- **Range:** `10.0.0.200 - 10.0.0.220` (For LoadBalancer services)
- **VIP:** `10.0.0.100` (For the Control Plane)

Once that config map was applied, the VIP came up. I could finally treat the cluster as a single entity rather than three separate VMs.

**The Power Struggle: Flannel vs. Cilium** — Before I could even hit the IP overlap issue, I made a classic rookie mistake. K3s comes with a default networking stack called Flannel. When I ran my initial installation, I didn't tell K3s to stay in its lane. I installed Cilium right on top of it, essentially giving my cluster two different brains trying to control the same nervous system.

The result was a mess of conflicting network policies and pods that couldn't decide which interface to use. I realized that Cilium doesn't like sharing. I had to nuke the entire installation and start over, this time explicitly telling K3s: "Do not install a CNI. I've got this."

```bash
curl -sfL https://get.k3s.io | sh -s - server --flannel-backend=none --disable-network-policy
```

## 1.3.7 The Network Hijack: Dealing with IP Overlaps

With the control plane stable, I moved to the CNI (Container Network Interface). I chose **Cilium** because I wanted to use eBPF for better observability and performance and I think I have a weird relationship with suffering.

I installed Cilium using the defaults. Suddenly, my nodes stopped being able to talk to the internet, and they couldn't even ping the gateway (`10.0.0.1`).

I ran a `traceroute` to `10.0.0.1` from one of the nodes. Instead of seeing my pfSense router, I saw this:

```text
1 10.0.1.170 (cilium_host) 0.045 ms
2 * * *
```

It took me a while of debugging, reinstalling, and trying before I found the root cause. The traffic was being swallowed by Cilium. My Lab Network is `10.0.0.0/24`. Cilium's default Pod Network is `10.0.0.0/8`. Cilium installed a route claiming the entire `10.x.x.x` range. When the OS tried to reach the physical gateway (`10.0.0.1`), the kernel routing table prioritized the Cilium interface because it thought `10.0.0.1` belonged to that network. I had to uninstall Cilium and reinstall it with a correctly scoped IPAM (IP Address Management) configuration that didn't overlap with my physical network: `--cluster-pool-ipv4-cidr=10.42.0.0/16`

This splits the `10.42.x.x` range into smaller `/24` subnets for each node. Now, `10.0.x` is physical, and `10.42.x` is virtual.

## 1.3.8 Native Routing: The "Hairpin" Issue

Cilium defaults to **VXLAN** (encapsulation). It works out of the box because it creates a virtual tunnel network that sits on top of your physical network. However, I wanted **Native Routing**. I wanted the packets to be routed normally without the overhead of wrapping them in UDP headers. I reinstalled with `routingMode=native`. Some things worked, but Hubble (the observability UI) was unreachable, and DNS lookups were timing out.

I looked at pfSense. I saw traffic from my nodes hitting the firewall and getting dropped. I spent hours adjusting rules. I even deleted the Hubble TLS secrets because an LLM suggested they might be stale (bad idea. They don't regenerate automatically, so I had to rebuild the certificate authority).

**The Service IP Red Herring** — While I was stuck in this loop, I convinced myself the issue was the Service CIDR (`10.43.0.0/16`). I thought, "If my pods can't reach the DNS service, I should just tell pfSense where that network is!" I started manually advertising these internal Kubernetes routes via BGP. DNS resolved. I thought I'd won.

But then I paused. **Why was traffic between two nodes on the same switch even hitting my firewall?**

It shouldn't have been. By "fixing" the firewall rules and BGP, I was just building a massive, unnecessary highway through my router to bridge two nodes that were sitting right next to each other. I was treating the symptom, not the root cause.

I stopped looking at the firewall and looked at the source: the kernel routing table on Node 1 (`ip route`). I expected to see routes telling Node 1 how to reach the other nodes' PodCIDRs (like `10.42.0.0/24` via `10.0.0.13`, and `10.42.2.0/24` via `10.0.0.12`)

That route didn't exist. Because the route was missing, the Linux kernel fell back to the **Default Gateway** (`10.0.0.1` - pfSense).

1. Packet leaves Node 1.
2. Goes to pfSense.
3. pfSense doesn't know where `10.42.1.x` is (or blocks it).
4. Packet dies.

This is called **Hairpinning**. I was unintentionally forcing internal cluster traffic to go out to the router and back. There is a specific flag in Cilium for this exact scenario: `autoDirectNodeRoutes=true`

As soon as I enabled this, Cilium injected the correct routes into the Linux kernel on every node.

```text
default via 10.0.0.1 dev eth0 proto static
10.0.0.0/24 dev eth0 proto kernel scope link src 10.0.0.11
10.42.0.0/24 via 10.0.0.13 dev eth0 proto kernel
10.42.1.0/24 via 10.42.1.171 dev cilium_host proto kernel src 10.42.1.171
10.42.1.171 dev cilium_host proto kernel scope link
10.42.2.0/24 via 10.0.0.12 dev eth0 proto kernel
```

Traffic immediately flowed directly between nodes. The "firewall issues" vanished because the traffic stopped hitting the firewall entirely. After some clean up, it was finally a "Data Center" network.

## 1.3.9 BGP: The Final Polish

With the internal routing fixed, I could finally set up **BGP** correctly. I didn't need BGP for the nodes to talk to _each other_ (that's what `autoDirectNodeRoutes` handled), but I did need it for _me_ to access the pods and services from my desktop.

I configured pfSense as the BGP listener and Cilium as the speaker.

- **pfSense:** ASN 64512
- **Cilium:** ASN 64513

My BGP sessions came up, but pfSense showed **0 accepted prefixes** with errors like "updates discarded due to missing policy." FRR will happily establish a session and still drop every route unless you explicitly permit them via prefix lists / route maps and apply those policies to each neighbor.

During validation, I made a rookie mistake: I disabled my "Allow TCP/179 (BGP)" rule and the BGP session stayed **Established**. I thought the rule wasn't needed.

It was. pfSense is **stateful**, existing sessions keep flowing as long as the state exists. The real test was clearing the state table (or forcing the session to re-establish). After clearing states, the peering immediately fell back to "Active" until the TCP/179 rule was restored.

I cleaned up my configuration to stop advertising the entire cluster IP range and focused only on the routes that mattered. Now, pfSense dynamically learns where the pod subnets are (`10.42.x.x`).

If I add a Node 4 later, BGP will automatically tell pfSense about the new routes. No manual static routes required.

## 1.3.10 The "Ouch I Fucked Up" Scoreboard

**Current Score: 7 Ls**

### Mistake #3: The Template Oversight (1 Point)

- **The Crime:** I assumed my new VMs would "just know" to use the Lab DNS. In reality, they cloned the DNS settings from the Template, which pointed to my Home Router.
- **The Consequence:** My security rules did exactly what I told them to do: block traffic from the Lab to the Home Network. I essentially locked myself out.
- **The Fix:** Explicitly define `--nameserver 10.0.0.1` in the provisioning script.
- **Lesson:** If you don't explicitly define a configuration, you inherit someone else's mistake. Automation requires you to be explicit about _every_ state.

### Mistake #4: The CNI Power Struggle (0.5 Points)

- **The Crime:** Installing Cilium without disabling K3s' default networking (Flannel).
- **The Consequence:** Two network "brains" fighting for control. I had to nuke the install and start over with `--flannel-backend=none`.
- **The Lesson:** Read the "Custom CNI" section of the docs before hitting enter on the install script (or ask the LLM agent you are using a few times).

### Mistake #5: The IPAM Overlap (1 Point)

- **The Issue:** I used the default Cilium pod CIDR (`10.0.0.0/8`), which overlapped with my physical LAN (`10.0.0.0/24`).
- **The Consequence:** The cluster hijacked the routing table, trying to route physical LAN traffic through the virtual overlay. Connectivity to the gateway was lost.
- **The Fix:** Explicitly defined a non-overlapping range: `10.42.0.0/16`.
- **Lesson:** Check the defaults.

### Mistake #6: The Hairpin Loop (1 Point)

- **The Issue:** Enabling Native Routing without `autoDirectNodeRoutes=true`.
- **The Result:** I spent hours "fixing" my firewall to allow traffic that should have never been there in the first place. I built a BGP highway to solve a problem that a simple local route could fix.
- **The Lesson:** If your nodes are on the same Layer 2 network, they should talk directly. If you see pod-to-pod traffic in your WAN firewall logs, you've done something wrong.

### Mistake #7: The Secret Deletion (0.5 Points)

- **The Issue:** During the debugging, I blindly deleted Hubble's TLS secrets based on bad advice.
- **The Consequence:** The secrets did not auto-regenerate, breaking the observability stack even after the network was fixed.
- **The Lesson:** Don't delete security credentials unless you know the regeneration mechanism.

### Mistake #8: The BGP Policy Blind Spot (0.5 Point)

- **The Issue:** Assumed "BGP Established" meant routing worked; didn't apply prefix-list/route-map to each neighbor.
- **The Consequence:** 0 accepted prefixes / updates discarded; wasted time debugging "BGP".
- **Fix:** Create prefix-list + route-map and attach it.

### Mistake #9: Stateful Firewall Validation Trap (1 Point)

- **The Issue:** Disabled the BGP allow rule and believed the still-established session proved it wasn't needed.
- **Consequence:** False confidence; inconsistent testing.
- **Fix:** Clear pfSense states / force session re-establish to validate.
- **Lesson:** State tables can mask broken rules.

### Honorable Mention: The Nameless DNS (Bug)

- **The Issue:** The Unbound DNS Resolver service refuses to start if the System Hostname or Domain are empty. It fails with a cryptic "Empty label" error.
- **The Context:** My hostname/domain fields were blank (possibly from a config restore, or maybe I just forgot).
- **The Result:** I spent hours debugging firewall rules and packet captures for a service that wasn't even running.
- **The Lesson:** Check `Status > Services` before you start tearing apart your firewall rules. If the binary isn't running, the firewall doesn't matter.

## 1.3.11 Conclusion

The infrastructure is finally stable.

- **Control Plane:** High Availability via kube-vip.
- **Data Plane:** Native Routing with no encapsulation.
- **Edge:** BGP peering with the upstream router.

It was a painful process, but there was a lot of learning. Now that K3s is set up, it's time for the rest of the platform.

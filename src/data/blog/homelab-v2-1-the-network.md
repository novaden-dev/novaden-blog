---
author: Kayra
pubDatetime: 2026-09-23T12:00:00Z
title: "Homelab v2.1 – The Network, Explained Enough to Rebuild"
slug: homelab-v2-1-the-network
featured: false
draft: false
tags: ["selfhosting"]
category: journal
format: writeup
description: "How the network layer of the homelab works: two uplinks with metric failover, two bridges instead of VLANs, dnsmasq for guest DHCP and DNS, nftables rules that isolate the lab, Tailscale for my own access, and a locked account for the AI assistant."
---

After v2.0 I said the series was done. A few weeks later I tried to explain my own network setup to an LLM and caught myself hand-waving over half of it. If I cannot explain how a piece works, I cannot rebuild it after a disk dies, so I went through the whole network layer and wrote it down.

## Two default routes and a metric

A Linux machine holds a routing table: a list of rules that map destination networks to interfaces and gateways. `ip route` prints it. On my host it currently reads:

```text
default via 192.168.1.1 dev nic0 metric 100
default via 192.168.8.1 dev wlp4s0 metric 200
172.20.0.0/24 dev vmbr0 scope link
172.21.0.0/24 dev vmbr1 scope link
```

A default route matches every destination that no more specific rule covers, which in practice means the internet. I have two of them because I have two uplinks: an ethernet cable and the mini-PC's wifi card.

When two routes are equally specific, the kernel picks with the metric, a priority number where lower wins. Ethernet has 100 and wifi has 200, so all traffic uses ethernet while the cable is connected. When the cable disconnects, the kernel drops that route and wifi handles the traffic. The failover mechanism is the two routes and their metrics.

The ethernet cable only gets connected when I want it to, and the lab is expected to run on wifi the rest of the time.

## Where those routes come from

Proxmox runs Debian underneath, and the permanent network setup lives in `/etc/network/interfaces`. A package called ifupdown2 (Proxmox's fork of Debian's ifupdown) reads the file at boot and applies each line as `ip` commands. Mine:

```text
auto nic0
iface nic0 inet static
    address 192.168.1.50/24
    gateway 192.168.1.1
    metric 100

allow-hotplug wlp4s0
iface wlp4s0 inet dhcp
    metric 200
```

`auto` brings the interface up at boot, `gateway` installs a default route, and `metric` sets the priority from the previous section. On the wifi side, `allow-hotplug` brings the interface up whenever it appears and `iface wlp4s0 inet dhcp` requests an address from the router.

Authentication to the access point is handled by wpa_supplicant, whose per-interface config lives in `/etc/wpa_supplicant/wpa_supplicant-wlp4s0.conf` and holds the SSID and pre-shared key. Without that file, the ethernet cable would be the lab's only uplink.

## Two bridges instead of VLANs

Inside the host I run two bridges:

```text
vmbr0  172.20.0.1/24   trusted guests (services, vaultwarden, immich)
vmbr1  172.21.0.1/24   the isolated lab (vulnerable machines)
```

A bridge is a software switch. Guests attach virtual interfaces to it, the host attaches its own address, and everything on the same bridge reaches everything else directly, with no routing involved. Two bridges are two separate switches.

The standard alternative is VLANs: tags on ethernet frames that let one physical cable carry several separated LANs, which requires a managed switch that understands the tags. I have one ethernet port and consumer hardware, so I used two bridges with two subnets instead and made the host the only router between them.

For guests to reach the internet at all, the host forwards their packets (`net.ipv4.ip_forward=1`) and rewrites the source address on the way out so replies can come back. One nftables rule does that: traffic from 172.20.0.0/24 or 172.21.0.0/24 leaving through nic0 or wlp4s0 is masqueraded.

## dnsmasq

A fresh guest knows nothing about itself, so it broadcasts a DHCP request. dnsmasq on the host assigns it an address from a pool (172.20.0.100 to 172.20.0.200 on vmbr0) and sets the guest's gateway and DNS server. It then serves DNS for the guests and forwards their queries upstream to 1.1.1.1.

Its whole config is one file, `/etc/dnsmasq.d/homelab.conf`, and it runs on both bridges. On vmbr1 it provides DNS plus a small temporary DHCP range (172.21.0.200 to 172.21.0.220) that only Packer, the VM provisioning tool, uses while booting fresh lab machines; the deployed lab VMs use static addresses. It does not serve DHCP on the physical uplinks, so it never competes with the home router.

## nftables

Isolation is done with nftables, the Linux kernel firewall. Rules are loaded into kernel memory with `nft -f /etc/nftables.conf`, and from then on the kernel checks every packet itself. An `input` chain sees packets addressed to the host itself, a `forward` chain sees packets the host routes between interfaces. Since the host is the only router between the two bridges, every packet crossing between them passes through that forward chain.

There are three tables.

**lab_isolation** exists because I run deliberately vulnerable machines on vmbr1, for security practice. GOAD, an Active Directory lab, is one of them; any other lab VM can take its place, and all of them inherit the same rules:

```text
iifname "vmbr1" oifname "vmbr1" accept                                # lab machines reach each other
ip saddr 172.20.0.16 oifname "vmbr1" accept                           # provisioner may manage the lab
ip saddr 100.112.206.25 iifname "tailscale0" oifname "vmbr1" accept   # Kali may attack the lab
iifname "vmbr1" oifname { "vmbr0", "tailscale0" } drop                # lab machines cannot reach the trusted net or tailnet
iifname "vmbr1" ip daddr { 10/8, 172.16/12, 192.168/16, 100.64/10 } drop  # lab machines cannot reach the LAN ranges
iifname "vmbr1" oifname { "nic0", "wlp4s0" } accept                   # lab machines may reach the internet
iifname "vmbr1" counter drop                                          # every other destination is dropped
oifname "vmbr1" counter drop                                          # nothing may initiate into the lab
```

Rules are evaluated top to bottom and the first match wins. A lab machine may talk to the other lab machines, be managed by the provisioner guest, be attacked by the single Kali machine, and download updates. Everything else is dropped, in both directions.

**novaden_ops** restricts a second SSH listener on the host: port 2222 accepts connections only from source 172.20.0.11 and drops the rest. The assistant's account below uses that listener.

**homelab_filter** separates the trusted guests from each other. services (.11), vaultwarden (.12) and immich (.13) cannot connect to one another, except for services to immich on port 45876, where Beszel collects metrics. The drop rule has a counter on it and it has blocked hundreds of thousands of packets. If a guest is compromised, the attacker starts with no access to the others.

My forward chains are default-accept with specific drop rules, rather than default-deny. The paths I care about are covered, but default-deny would be safer. If I revise this file, that is the change to make.

## Tailscale

Tailscale is a WireGuard-based VPN where each device registers an identity tied to my account, gets a stable 100.x address, and connects directly to its peers.

My laptop is a tailnet member, and MagicDNS resolves the name `pve` to the host's tailnet address, so `ssh root@pve` works from anywhere the laptop has internet.

SSH authentication is handled the same way. The host enables Tailscale SSH, which intercepts SSH sessions arriving over the tailnet and checks the tailnet identity of the caller. Both devices are registered to the same account, so my logins need no SSH key. The host's SSH daemon only listens on the tailnet addresses, so machines on the home LAN cannot reach port 22 at all.

The isolated lab also depends on it. The lab firewall rule that allows an outside attacker accepts exactly one source: the tailnet address of my Kali machine.

## The assistant's account

The AI assistant (OpenClaw, in the services guest at 172.20.0.11) can also reach the host, over the SSH listener on port 2222 that only accepts connections from that guest. There is a dedicated Unix account, novadenops, used only by the software. My own logins do not touch it.

Its SSH key carries a forced command:

```text
command="/usr/bin/sudo -n /usr/local/sbin/novaden-ops --forced",restrict ssh-ed25519 ...
```

Whatever command the client requests, the server runs exactly that one. The `restrict` option also disables port forwarding, agent forwarding and PTYs. The account has no password, so it cannot be used for interactive logins, and the sudoers file allows that one account to run that one script as root. The script, novaden-ops, accepts only fixed verbs (inventory, status, health, bounded logs, start, stop with repeated confirmation) against a registry of known targets. There is no shell access, no Docker socket, and no arbitrary commands.

To revoke the assistant's access, delete `/home/novadenops/.ssh/authorized_keys` on the host.

## The files that define this layer

- `/etc/network/interfaces`: uplinks, metrics, bridges
- `/etc/wpa_supplicant/wpa_supplicant-wlp4s0.conf`: wifi credentials
- `/etc/nftables.conf`: the three tables above
- `/etc/dnsmasq.d/homelab.conf`: guest DHCP and DNS
- `/etc/ssh/sshd_config.d/10-hardening.conf` and `/etc/sudoers.d/novaden-ops`: the two SSH setups
- the Tailscale node registration: rejoin and re-authorize after a rebuild

Everything else in the lab comes back from compose files and backups. This layer decides what the rebuilt lab is allowed to talk to, so read each rule while copying it rather than pasting blindly.

VLANs with a managed switch would be tidier than metric failover, but that hardware is not part of the setup. What matters is that the current config has run like this for months, and the isolation rules decide exactly which machines can talk to which. That is what I needed this layer to do.

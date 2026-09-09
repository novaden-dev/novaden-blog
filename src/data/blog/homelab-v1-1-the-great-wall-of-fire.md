---
author: Kayra
pubDatetime: 2024-12-31T00:00:00Z
title: "Homelab v1.1 — The Great Wall of Fire: pfSense & Network Isolation"
slug: homelab-v1-1-the-great-wall-of-fire
featured: false
draft: false
tags: ["selfhosting"]
category: journal
series: homelab
seriesOrder: 1.1
description: Isolating the lab network from the home network with pfSense — default-deny rules, aliases, and the anti-lockout trap that stumped me until I remembered DNS lives on the gateway.
---

## 1.1.1 Introduction: Paranoia as a Service

In the last post, I bragged about my "Data Center" architecture. But a Data Center without security is just a public playground for hackers.

I had two goals for my network, which sound simple but are mutually exclusive:

1. **Isolation:** My experimental "Lab" network (`10.0.0.0/24`) must not be able to talk to my "Home" network (`192.168.1.0/24`). I don't want a rogue malware sample from a Kali Linux VM sniffing packets from my dad's iPad or my smart fridge.
2. **Integration:** My Lab still needs internet access, and critically, it needs to back up data to my NAS (which is on the Home network) and pull code from my Git server (also on the Home network).

To achieve this, I deployed **pfSense** virtualized on Proxmox. It acts as a "Router on a Stick" a digital bouncer standing between my chaotic lab and the peaceful home network.

## 1.1.2 The Physical Router: The "Dumb" Gateway

Before diving into the cool pfSense stuff, I had to configure my ISP-provided router.

My ISP router knows about `192.168.1.x` (Home). It has no idea `10.0.0.x` (Lab) exists. If a packet from the Lab goes out to the Internet, the return packet hits my ISP router, which looks at the destination (`10.0.0.50`) and says, _"I don't know her,"_ and drops it.

To fix this, I added a **Static Route** on the main router:

- **Destination Network:** `10.0.0.0`
- **Subnet Mask:** `255.255.255.0`
- **Gateway:** `192.168.1.5` (The WAN IP of my pfSense VM)

I also set a **DHCP Reservation** for pfSense to ensure it always gets `192.168.1.5`. Now, my ISP router knows: _"Oh, traffic for the Lab? Hand it to that pfSense guy over at .5."_

## 1.1.3 pfSense: Defining the "Objects" (Aliases)

One thing I learned the hard way: **Never use raw IP addresses in firewall rules.** You _will_ forget what `192.168.1.60` is in six months.

I set up **Aliases** to give human-readable names to my infrastructure:

- **`ADMIN_LAPTOP`** (`192.168.1.18`): My laptop. The "Master Key" allowed to access everything.
- **`PROXMOX_HOST`** (`192.168.1.x`): Holds the NFS backup target.
- **`HOME_SERVICES`** (`192.168.1.60`): My Gitea instance (Code & Container Registry).
- **`LAB_LAN`** (`10.0.0.0/24`): The Danger Zone.
- **HTTP_S_NTP_DNS**: A port alias for 80, 443, 53, and 123 (NTP).

## 1.1.4 The Firewall Rules: Default Deny

I adopted a "Default Deny" strategy. By default, the Lab can do **nothing**. I only opened the exact holes needed for survival.

Here is the logic flow for the **Lab Interface (LAN)**:

### 1. Protect the King (Anti-Lockout)

**Rule:** `BLOCK TCP` from `LAB_LAN` to `PFSENSE_FW` on ports `80, 443, 22`.
**Why:** If a container in my cluster gets compromised, I don't want the attacker logging into my firewall admin panel. The cluster has no business talking to the router's GUI.

### 2. DNS is Life

**Rule:** `PASS UDP` from `LAB_LAN` to `PFSENSE_FW` on port `53`.
**The "Oopsy":** I initially blocked access to the gateway entirely. Turns out, if you block the gateway, you block the DNS resolver running _on_ the gateway. My cluster screamed in confusion because it couldn't resolve `github.com`. This rule fixes that.

### 3. The "Authorized" Holes (Git & Backups)

**Rule:** `PASS TCP` to `HOME_SERVICES_ALLOWED` (Ports 22, 443).
**Rule:** `PASS TCP/UDP` to `PROXMOX_HOST` (NFS Ports).
**Why:** The cluster needs to pull docker images from Gitea and push backups to the NFS share. These are the _only_ things on my home network the cluster is allowed to touch.

### 4. The Great Wall (Isolation)

**Rule:** `BLOCK Any` from `LAB_LAN` to `HOME_LAN`.
**Why:** This is the big one. It prevents the Lab from accessing my printer, TV, or PC. If the Lab burns down, the fire stays in the Lab.

### 5. Strict Egress (The Funnel)

**Rule:** `PASS TCP/UDP` from `LAB_LAN` to `Any` on ports `WEB_PORTS_DNS`.
**Why:** Most home setups allow "Any" outbound traffic. Not here. My cluster can only speak Web (HTTP/S), DNS, and Time (NTP). If a rogue script tries to open a reverse shell on a weird port or connect to an IRC botnet, the firewall drops it.

## 1.1.5 Conclusion

I now have a segmented network where my Kubernetes cluster is:

1. **Isolated** from my personal devices.
2. **Allowed** to access the internet (strictly).
3. **Permitted** to back itself up to my storage server.

It's secure, it's over-engineered, and it effectively doubles my troubleshooting time whenever something doesn't work. **Perfect.**

Next up: We finally start building the virtual machines and bootstrapping the K3s cluster.

## 1.1.6 The "Ouch I Fucked Up" Scoreboard

No lab is built without tears. I am keeping a running tally of my "Learning Opportunities" (stupid mistakes).

**Current Score: 1.5 Ls**

### Mistake #1: The Phantom Interface (1 Point)

**The Crime:** I deleted a network interface in Proxmox *before* removing the firewall rules associated with it in pfSense.
**The Consequence:** pfSense hid the interface from the GUI, but the rules remained active in the backend. When I tried to clean up my Aliases, I got hit with: `Cannot delete alias. Currently in use by filter rule...`
**The Fix:** I had to download the pfSense XML configuration backup, manually surgical-remove the phantom rules with a text editor, and restore the config.
**Lesson:** Software first, Hardware second.

### Mistake #2: The Offline Install (0.5 Points)

**The Crime:** I installed Proxmox on the Mini-PC without connecting the Ethernet cable because I was too lazy to reach behind the desk.
**The Consequence:** The installer couldn't pull a DHCP address, so it defaulted to a mess. Post-install networking was broken.
**The Fix:** instead of debugging `/etc/network/interfaces` like a pro, I just formatted the drive and reinstalled it.
**Lesson:** I don't know to be honest, don't be lazy? plug the cable in? maybe

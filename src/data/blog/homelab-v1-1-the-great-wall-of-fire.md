---
author: Kayra
pubDatetime: 2024-12-31T00:00:00Z
title: "Homelab v1.1 – The Great Wall of Fire: pfSense & Network Isolation"
slug: homelab-v1-1-the-great-wall-of-fire
featured: false
draft: false
tags: ["selfhosting"]
category: journal
description: Isolating the lab network from the home network with pfSense. Default-deny rules, aliases, and the anti-lockout trap that stumped me until I remembered DNS lives on the gateway.
---

Good, so I have a data center to manage, but before that I need to do proper isolation.

Isolation: my experimental "Lab" network (`10.0.0.0/24`) must not be able to talk to my "Home" network (`192.168.1.0/24`). I don't want a malware sample from a Kali Linux VM sniffing packets from my network's devices.

I went for pfSense, which is an open-source firewall.

## The "Dumb" Gateway

Before diving into that, I had to configure my router.

My router knows about the network it is managing, `192.168.1.x` (Home). It has no idea `10.0.0.x` (Lab) exists. If a packet from the Lab goes out to the Internet, the return packet hits my router, which looks at the destination (`10.0.0.50`) and says, "I don't know that," and drops it.

To fix this, I added a Static Route on the main router:

- **Destination Network:** `10.0.0.0`
- **Subnet Mask:** `255.255.255.0`
- **Gateway:** `192.168.1.5` (The WAN IP of my pfSense VM)

I also set a DHCP Reservation for pfSense to ensure it always gets `192.168.1.5`. Now, my router knows: "Oh, traffic for the Lab? Hand it to that pfSense guy over at .5."

## The Aliases

I then started setting up pfSense. I started with aliases:

- **`ADMIN_LAPTOP`** (`192.168.1.18`): My laptop. The "Master Key" allowed to access everything.
- **`PROXMOX_HOST`** (`192.168.1.x`): The Proxmox host, holds the NFS backup target.
- **`HOME_SERVICES`** (`192.168.1.60`): My Gitea instance (Code & Container Registry).
- **`LAB_LAN`** (`10.0.0.0/24`): The Danger Zone.
- **`HTTP_S_NTP_DNS`**: A port alias for 80, 443, 53, and 123 (NTP).

## The Rules

Then I started with the rules. Default deny: by default, the Lab can do **nothing**. I only opened the exact holes needed for its survival.

**Rule 1:** `BLOCK TCP` from `LAB_LAN` to `PFSENSE_FW` on ports `80, 443, 22`. **Why:** If a container in my cluster gets compromised, I don't want the attacker logging into my firewall admin panel.

**Rule 2:** `PASS UDP` from `LAB_LAN` to `PFSENSE_FW` on port `53`. The first fuck-up I had: I initially blocked access to the gateway entirely. Turns out, if you block the gateway, you block the DNS resolver running on the gateway.

**Rule 3:** `PASS TCP` to `HOME_SERVICES_ALLOWED` (ports 22, 443), and `PASS TCP/UDP` to `PROXMOX_HOST` (NFS ports). **Why:** The cluster needs to pull Docker images from Gitea and push backups to the NFS share.

**Rule 4:** `BLOCK Any` from `LAB_LAN` to `HOME_LAN`. **Why:** It prevents the Lab from accessing my printer, TV, or PC. If the Lab burns down, the fire stays in the Lab.

**Rule 5:** `PASS TCP/UDP` from `LAB_LAN` to `Any` on ports `WEB_PORTS_DNS`. **Why:** Most home setups allow "Any" outbound traffic. My cluster only needs to speak Web (HTTP/S), DNS, and Time (NTP). If a rogue script tries to open a reverse shell on a weird port, the firewall drops it.

It's secure for now, it's over-engineered, and it effectively doubles my troubleshooting time whenever something doesn't work. **Perfect.**

## The Mistakes

I did 2 mistakes. I kept a tally of the mistakes I did initially, but then I removed it. For this episode I did:

**First mistake:** I deleted a network interface in Proxmox before removing the firewall rules associated with it in pfSense. It was not showing in the GUI, but the rules remained active in the backend. When I tried to clean up my aliases, I got `Cannot delete alias. Currently in use by filter rule...` To fix that, I had to download the pfSense XML configuration backup, manually remove the phantom rules with a text editor, and restore the config.

**Second mistake:** I installed Proxmox on the mini PC without connecting the Ethernet cable because I was too lazy to reach behind the desk. The installer couldn't pull a DHCP address, so it defaulted to a mess. Post-install networking was broken. Instead of debugging, I just formatted the drive and reinstalled it.

---
author: Kayra
pubDatetime: 2024-12-27T00:00:00Z
title: "Homelab v0.1 — Why I Bought a Mini-PC Instead of Therapy"
slug: homelab-v0-1-why-i-bought-a-mini-pc-instead-of-therapy
featured: false
draft: false
tags: ["selfhosting"]
category: journal
series: homelab
seriesOrder: 0.1
description: The hardware-shopping-and-hallucinating-an-architecture origin story of this homelab series. Also known as "how I replaced therapy with a GMKtec K8 Plus."
---

## 0.1.1 Introduction: The Gateway Drug

It's been a while since I doubled down on FOSS. I finally ditched Windows for Fedora, and I am using more and more open-source alternatives for most of my software. That switch was just the start. It was the gateway drug to my new addiction: **Homelabbing**.

Homelabbing is a hobby that involves building things, screaming at 12 AM _"FUCK, HOW DIDN'T I NOTICE THIS EARLIER?"_ or _"WHY THE FUCK IS IT NOT WORKING!?"_ It costs you a lot of money, social aura, and brain nerves, and gets you a Vitamin D deficiency. However, it can be done from the comfort of your desk, and that feeling when things finally link up and start working is just on another level.

It usually starts like this: "I want to replace Google Cloud," or "I want full control over my data," or "I want a virtual girlfriend to tell me _Keep Going Honey, it gets better._" Then, you keep digging yourself deeper into the rabbit hole until you end up with a full data center with firewalls, SIEM, IDS, IPS, while your government calls to ask about the suspiciously increasing electricity usage.

I _started_ with something simple:

- **Nextcloud** (Bye, Google)
- **EVE-NG** & **Kali Linux** (Labs)
- **VPN** & **n8n** (Utility)
- A small local **AI model**
- My blog rants & custom apps

Pretty simple, right? I have the experience. I have the technical knowledge. It's just practice for professional services. (Spoiler: It was not simple).

## 0.1.2 Buying Hardware I Definitely Don't Need

I settled on the **GMKtec K8 Plus**, but I spent a lot of time justifying the purchase before pulling the trigger.

My first thought was, naturally, a **Raspberry Pi**. It's the standard for home labs. However, a Pi is designed for lightweight services. My plan involved running multiple resource-heavy VMs (EVE-NG, Kali Linux), storage-intensive apps like Nextcloud, and potentially local AI models. That led me to the world of **Mini PCs**, full desktop performance in a tiny form factor.

I initially looked at the **GMKtec K6** as a budget-friendly option. It looked good on paper, but further research (reading Reddit comments) revealed consistent reports of thermal issues and fan noise. Since this device would be running 24/7 on my desk (optimistic, naive me), I couldn't compromise on cooling. That's when I found the **K8 Plus**. It's the upgraded version of the K6, addressing many of the thermal concerns while staying within my budget.

- **Ryzen 7 8845HS (8 Cores / 16 Threads):** Since I plan to virtualize extensively, having 16 threads is critical to keep things running smoothly without resource contention.
- **Radeon 780M iGPU:** It is powerful enough to handle basic local AI models out of the box.
- **32GB RAM & 1TB SSD:** The minimum entry fee for a lab this size. Anything less would choke under the weight of my poor architectural decisions.
- **Oculink Support:** This was a key differentiator. It gives me the option to connect an external desktop GPU (eGPU) later if I need more power, providing a clear upgrade path.

Compared to other models with similar specs, the K8 Plus offered the best price-to-performance ratio. Everything else was significantly more expensive for the same hardware. When the Black Friday discounts hit, I made the purchase.

## 0.1.3 The Plan (A.K.A. The Hallucination)

Before I even got my hands on the device, I started planning how my setup would look. The idea was to just throw an Ubuntu server on it and run my apps, right? :)

I listed out my needs:

- Nextcloud
- Local AI Model
- n8n Flows
- EVE-NG & Kali Linux
- Custom Apps & Blogs

Okay, simple. But then the voices of reason (and paranoia) kicked in. How do I host all of this on a single Ubuntu Server without it becoming a security and computing nightmare? That's when I realized I needed virtualization. I know VMware ESXi, so I figured I would just use that. However, VMware killed their free version. Also, I'm trying to be a FOSS purist here. **Proxmox** it is. An open-source, enterprise-grade hypervisor. Good. The host OS is solved.

Now for the network diagram. I had two simple rules:

- My hacker tools (Kali/EVE-NG) should _not_ be able to talk to my personal photos (Nextcloud).
- My public-facing apps should _not_ have access to my private internal network.

No big deal. I'll just set up **VLANs**. I logged into my ISP-provided router to configure them. Turns out my router has no VLAN support. I either had to buy a new router, or I could just deploy a virtual firewall. I decided to deploy **pfSense** as a VM to manage the entire network, handle VLANs, and enforce rules. That was the moment I realized I was trapped like a butterfly drawn to an insect-eating flower. (I absolutely loved it).

So we have Proxmox and pfSense. Still manageable. But then I started digging the rabbit hole:

- I have public apps, so I need a reverse proxy. **Enter Caddy.**
- I need analytics without Google spying on me. **Enter Matomo.**
- I need to know if the server is actually alive. **Enter Prometheus & Grafana.**
- I need to scan my code for vulnerabilities. **Enter SonarQube.**
- I need to aggregate logs because I apparently hate sleep. **Enter Wazuh.**

You get the idea. The rabbit hole didn't just have a bottom; it had a basement.

## 0.1.4 The "Final" Architecture

I spent the rest of the night trying to keep my eyes open, drawing lines and boxes. The result was this "final" architecture diagram:

![My Homelab Architecture](/images/migrated/MyHomeLab.png)

A beauty that lasted less than 24 hours. But that's a story for **v1.0**.

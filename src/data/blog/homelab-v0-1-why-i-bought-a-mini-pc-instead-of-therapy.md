---
author: Kayra
pubDatetime: 2024-12-27T00:00:00Z
title: "Homelab v0.1 – Why I Bought a Mini-PC Instead of Therapy"
slug: homelab-v0-1-why-i-bought-a-mini-pc-instead-of-therapy
featured: false
draft: false
tags: ["selfhosting"]
category: journal
description: The hardware-shopping-and-hallucinating-an-architecture origin story of this homelab series. Also known as "how I replaced therapy with a GMKtec K8 Plus."
---

You wake up one day and wonder _why am I not getting good morning messages_, and you have some money to spend because, unlike your peers, you gave up on marriage. After some thinking and multiple chats with LLMs, you end up with 2 options: I can do therapy, or I can buy a homelab and set up a local LLM gf. I decided on the homelab.

Let's define it first: a homelab is a personal, at-home computer setup used to experiment with servers, networks, and software. I have been looking more and more into free open-source apps, most of which need a place to be hosted. With the rise of LLMs, I have also been creating a few scripts here and there of my own, and sometimes you need a place to host these. Then I wanted to practice a few things in IT: get better at DevOps, security tools, architecture, etc. The mix of all of these made homelabbing a good new hobby. I could've bought a simple, cheap VPS. However, on these you can't host your own SIEM, IDS, or IPS, and you can't be sure it will exist when the AI revolution/takeover comes, so I wanted something that I could take with me to a farm off-grid and be able to have all my apps/tools. A toxic relationship with tech, I guess.

## The Wishlist

I started with a simple thing:

- Nextcloud, which is a bunch of services. Think Microsoft 365, but open-source.
- EVE-NG for spawning network labs.
- A Kali Linux machine to sound scary.
- A small local AI model for the "Good Mornings", "Keep going honey", and other such messages.
- A blog maybe? Some custom apps.

## The Hardware

So, shopping time. I started checking the hardware I would get. I thought of a Raspberry Pi, but I need something that will grow with me. A Raspberry Pi is good for small scripts or apps, but not what I had in mind. So I found out about mini PCs, basically a PC that's small. After detailed research (read: a few Reddit posts), I decided on the GMKtec K8 Plus: good hardware, nothing fancy, but good enough for most of my needs. And it has Oculink support, which means I can add an eGPU later when my AI model (aka gf) needs an upgrade and I have the money for it.

## The Plan

I then started with the plan: Ubuntu Server, then Nextcloud, the local model, etc. But then, I am not sure if I have a thing for complicating my life and taking the hard route, or if it was actually justified, but I moved from a simple server to a virtualization operating system. Let's say I want to spawn a Windows machine to test something, or I want to test myself and see if I can get past installing Arch. Doing that on an Ubuntu server wouldn't be that easy. So, a hypervisor for the host operating system. VMware ESXi, I remember that one from one of my internships, but VMware killed their free version and I want to be relying more on FOSS. Proxmox is a good open-source alternative. Now that this is solved, the network diagram.

I will have some hacking tools, and then my personal data. These should be isolated from each other. Then I will have public-facing apps, and those should be in a DMZ. I logged into the router admin page and it doesn't have VLAN support. I can buy a new one, or I can host my own firewall and do the isolation using that (see, it is the thing I told you about: complicating shit. Maybe it is part of the hobby rules or something.)

Then that night it went something like this:

- I will have multiple public apps, and will probably need a reverse proxy. Enter Caddy.
- I would love to have analytics without giving the data to Google. Enter Matomo.
- Some monitoring and visibility. Enter Prometheus & Grafana.
- Some security, source code scanning. Enter SonarQube.
- ...

I ended up with this architecture:

![My Homelab Architecture](/images/migrated/MyHomeLab.png)

A beauty that lasted less than 24 hours. But that's a story for **v1.0**.

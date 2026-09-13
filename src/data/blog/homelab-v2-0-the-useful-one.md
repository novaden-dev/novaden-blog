---
author: Kayra
pubDatetime: 2026-09-12T00:00:00Z
title: "Homelab v2.0 – The Useful One"
slug: homelab-v2-0-the-useful-one
featured: false
draft: false
tags: ["selfhosting"]
category: journal
format: writeup
description: After the governed cluster came the hard reset, and Gitea, K3s, and pfSense went away rm -rf style. What rose from the empty Proxmox is the version I actually use, plus the verdict on the whole hobby.
---

There were 2 more rounds of this series where I added multiple other things and features: Tailscale, making it work on Wi-Fi instead of Ethernet, and multiple other things.

However, after some time, I did a hard reset on the whole thing.

I had the perfect homelab architecture: proper governance, proper availability, isolation, security, automation, everything you name it, I had it. But the architecture was already consuming all of my resources, without even 1 useful app that wasn't just feeding the architecture itself.

So, one day, during a clarity period, I removed the whole thing, `rm -rf` style. I deleted Gitea, the K3s cluster, pfSense, etc.

I was left with an empty Proxmox. On it, I started adding actual useful things, one by one. First, I set up Tailscale to access internal things from my phone, from anywhere.

## The Apps

Then I added the apps I would use.

First, I hosted one Docker container for my lightweight services. If a service needs isolation, it gets its own Docker container. Some of the services:

- Memos: Google Keep, but open-source and on my homelab.
- Miniflux: Feed reader. Haven't set anything up yet because I had no time for it.
- Paperless-ngx: Document management system.
- Journiv: Journaling app. I can't keep up with the writing; the plan was one short paragraph every day, but that didn't happen.
- Uptime Kuma: Simple monitoring. I set it up so I get alerts in Telegram.
- Beszel: Monitoring for the resources.
- Umami: Tells me who visited my blog.
- Stirling PDF: All kinds of tools for PDF editing.
- WiseMapping: For building mind maps.
- Caddy: Reverse proxy.
- Homebox: Home inventory for the few items I own.
- Monica: A CRM for personal relationships. You can add when and what you did with who, and keep track.
- Immich: Google Photos alternative, quite good.
- Vaultwarden: The open-source Bitwarden, for password management.

Then I made my blog public through a Cloudflare tunnel.

## The AI Stack

Of course, the AI stack. I tried multiple local models, but they kept crashing. Even the smallest Qwen model would crash the machine most of the time. It would work for a while, and I even set up voice communication and all, but it kept crashing so much that I had to replace it with sending my data to Beijing. I also got OpenClaw, but a secure, scaled-down version of it. I still don't give it full access: it interacts with the homelab through the tools I set up for it, so it can spawn machines and edit configs, but not `rm -rf` my whole lab. And for privacy, I don't give it access to my files.

For cybersecurity, I have multiple tools, and I can host any lab I need. For example, I hosted GOAD to practice Active Directory for OSCP. I have a Kali machine I can run anything I need in, and I also have SysReptor for the reports.

I also have multiple scripts that are useful for me. I get night reminders for my medicine; usually they stay on read, and an alarm on my phone would've done the same job, but I might as well use the homelab while I have it. I also get a summary of the stocks I hold, every week.

For backups, I have `restic` configured with daily backups.

## Was It Worth It?

Now when I look back at the whole homelab thing, I would say it is worth it, even though I doubted that at times.

- I managed to learn a lot of things that any VPS wouldn't have allowed me to do.
- I can run anything I need, any time, with a simple command. Need a Windows server to test something? One command and it's there. For GOAD, for example, it was literally less than 5 minutes and the lab was up for me to attack.

Am I utilizing it to the max? Not really, most likely because I didn't have much time for it. But do I regret buying it and starting this hobby? I would say not really. I actually like it, and I am glad I did it. I am actually keeping a list of people who bought a mini PC and started homelabbing after we talked about it and I showed them the lab. So far there are 4 on the list, 3.5 maybe, as one of them is trying to return it and just go for a simple VPS. I guess that's the end of the homelab series. Maybe new posts will come up as I update things; we will see how it goes.

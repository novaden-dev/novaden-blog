---
author: Kayra
pubDatetime: 2024-12-31T00:00:00Z
title: "Homelab v1.2 — The Supply Chain: Golden Images & The Source of Truth"
slug: homelab-v1-2-the-supply-chain
featured: false
draft: false
tags: ["selfhosting"]
category: journal
series: homelab
seriesOrder: 1.2
description: Solving the bootstrap paradox — Cloud-Init templates, a self-hosted Gitea server outside the cluster, and why SQLite wasn't going to cut it when I'm hoarding 32GB of RAM.
---

## 1.2.1 Introduction: The Chicken and the Egg

We have the hardware (GMKtec K8 Plus). We have the network (pfSense with strict isolation). Now, we need to build the Kubernetes cluster.

But wait. If I build the cluster, where do I store the configuration files? In Git. Okay, where does Git live? Ideally, self-hosted on the server. But the server isn't built yet because I don't have the configuration files... which belong in Git.

They call it the **Bootstrap Paradox**.

To solve this, I needed to establish the "Source of Truth" _before_ building the infrastructure that relies on it. I also needed a way to spawn Virtual Machines without clicking "Next" on an installer 50 times. I like the keyboard more.

## 1.2.2 The "Golden Image" Strategy

In my quest for "Data Center" status, I refused to manually install Debian from an ISO for every single node. That's prone to human error, and frankly, it doesn't stand up to the autistic tech nerd status I am trying to achieve.

Instead, I used **Cloud-Init**. This was actually new to me. When the VM boots for the first time, it reads a small configuration file and sets up the hostname, IP address, user accounts, and SSH keys automatically.

I created a **Debian 12 Cloud Template** (ID 9000) on Proxmox. Now, whenever I need a new server, I don't "install" Linux. I just clone Template 9000, tell it "You are IP 10.0.0.11," and 20 seconds later, I have a fully secured, ready-to-use server.

I didn't even use the GUI to create the template. I scripted the entire process in the Proxmox shell. Why? Because if I ever burn this lab to the ground (likely), I can rebuild the base images in 30 seconds by pasting one block of code. Also, unlike the GUI, I can just make an AI write the script for me.

## 1.2.3 Gitea: The Command Center

For my Git server, I chose **Gitea**. It's lightweight, fast, and looks enough like GitHub that I don't feel homesick.

I deployed it on a dedicated VM (`192.168.1.60`) running outside the Lab network. This was a strategic choice: **Gitea is the "Librarian."** It needs to survive even if the "Library" (the Kubernetes Cluster) catches fire.

### The Logical Choice: SQLite vs. PostgreSQL

The default Gitea installation uses SQLite. It's simple, just a file on a disk. It uses almost zero RAM. It is perfectly adequate for a single user.

So, naturally, **I didn't use it.**

I spun up a **PostgreSQL** container instead.

- **Why?** Because I have 32GB of RAM, and I intend to use it.
- **The Real Reason:** SQLite struggles with concurrency. Since I plan to use Gitea as a **Container Registry** (storing Docker images) and potentially for CI/CD pipelines, I needed a database that wouldn't choke when multiple services hit it at once.

I deployed the whole stack using **Docker Compose**. The configuration is version-controlled (of course), and I restricted the memory usage to ensure it doesn't eat up the **Proxmox host's** resources, leaving maximum capacity for the K3s cluster.

## 1.2.4 Establishing Governance (Naming Things is Hard)

I like consistency, so I established a strict naming convention for my environment.

I set up two Organizations to keep things organized:

1. **`infrastructure` (Private):** This is the holy of holies. It contains `cluster-manifests`, the repository that defines the "Desired State" of my network. If you delete this repo, my lab ceases to exist.
2. **`applications` (Public):** This is where my actual code for applications and blogs lives.

The naming convention is simple: `infra-*`, `app-*`, and `tools-*`.

## 1.2.5 Conclusion

The foundation is complete.

- **Hardware:** ✅
- **Network:** ✅
- **Templates:** ✅
- **Git Server:** ✅

We have built the factory. In the next post, we finally turn on the assembly line and provision the Kubernetes Cluster itself.

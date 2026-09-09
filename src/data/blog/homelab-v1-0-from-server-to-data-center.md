---
author: Kayra
pubDatetime: 2024-12-31T00:00:00Z
title: "Homelab v1.0 — From Server to Data Center"
slug: homelab-v1-0-from-server-to-data-center
featured: false
draft: false
tags: ["selfhosting"]
category: journal
series: homelab
seriesOrder: 1.0
description: Throwing away the "simple Ubuntu server" plan and committing to a full K3s cluster with Proxmox, Longhorn, 3-2-1 backups, and four production-grade namespaces. Also known as "over-engineering for the vibes."
---

## 1.0.1 The Shift: From "Server" to "Data Center"

In the previous episode, I claimed I wanted a "simple setup." I lied. Well, I didn't lie intentionally. But after reviewing my initial plan just slapping multiple Ubuntu Servers on Proxmox behind a pfSense firewall works... but it's a bit boring.

It didn't unlock the level of "aura" I was aiming for. Sure, it's good for holding a nerdy conversation for a few minutes, but I wanted to flex harder than that. I needed an architecture complex enough to impress the AI girlfriend I plan to host on it.

That was the moment the project transitioned from "Setting up a Server" to "Building a Data Center."

## 1.0.2 The Blueprint (A.K.A. The "Real" Diagram)

Originally, the plan was just Proxmox hosting a few Docker containers and maybe one or two Debian virtual servers. That works, but I don't aim for "just works." My eyes are on the cloud giants; AWS, Azure, GCP. I wanted to build a miniature version of that chaos on my desk.

### The Foundation: Proxmox VE

This is the bedrock. It's the OS running on my GMKtec K8 Plus. It allows me to slice up that beautiful Ryzen 7 and 32GB of RAM into distinct virtual machines.

### K3s (The "Diet" Kubernetes)

Originally, I was going to run apps as Docker containers. However, managing lifecycle, networking, and storage for 20+ containers manually is painful. That's why I moved to Kubernetes (K8s), specifically the K3s distribution (a lightweight, CNCF-certified distro perfect for home labs).

Kubernetes isn't just a way to run containers; it's an orchestration engine that solves three specific problems:

- **Scheduling (Resource Efficiency):** You don't tell K8s _where_ to run an app. You tell it _what_ the app needs (e.g., "0.5 CPU and 1GB RAM"), and the scheduler finds the best node with available capacity.
- **Self-Healing (Desired State):** K8s operates on a "Desired State" model. If I tell it "I want 2 copies of my blog running," and one crashes, K8s detects the discrepancy (2 desired, 1 actual) and instantly spins up a replacement.
- **Scaling (Horizontal):** Handling a traffic spike isn't about making a server bigger; it's about making _more_ servers. K8s can spawn additional replicas of a container to handle load and destroy them when the traffic dies down.

### The Anatomy of the Flex: Nodes, Clusters, and High Availability

You might ask: _"Why not just run K3s on one big virtual machine?"_ Because that introduces a Single Point of Failure (SPOF). To achieve the "Data Center" status, I needed **High Availability (HA)**.

**Here is how the architecture is broken down:**

- **The Node:** In this context, a "Node" is a Virtual Machine running inside Proxmox. Think of it as a worker bee. I have provisioned **3 Nodes** (4GB RAM / 2 vCPU each).
- **The Cluster:** The "Cluster" is these three nodes working together as a single logical system. I don't talk to Node 1 or Node 2; I talk to the Cluster API, and it delegates work to the nodes.

**How we achieve SLA-level High Availability:** If I run my blog on a single server and that server crashes, my blog is down. In this cluster, I use **Anti-Affinity** rules to ensure that the two copies (replicas) of my blog never run on the same node.

1. **Node 1 dies** (or I reboot it for updates).
2. **Kubernetes detects the failure.**
3. **Traffic is instantly routed** to the replica running on Node 2.
4. **A new replica** is scheduled onto Node 3 to restore full redundancy. Result: Zero downtime.

### The Architecture Breakdown

To keep this sanitary, I divided the cluster resources (10.1 GB RAM / 4.8 vCPU allocated) into four flat namespaces:

**1. `mgmt` Namespace (The Control Room)**

- **ArgoCD:** The GitOps engine. It watches my Gitea repo. If I push code, ArgoCD updates the cluster.
- **Sealed Secrets:** Encrypts my passwords so I can safely commit them to Git.

**2. `platform` Namespace (The Utility Belt)**

- **Observability:** Prometheus (metrics), Grafana (dashboards), and Loki (logs). If the cluster is slow, this tells me why.
- **CI/CD:** Woodpecker CI. Runs pipelines and builds Docker images.
- **Ingress:** Traefik + Cert-Manager. Handles SSL certificates automatically via Cloudflare.

**3. `stage` Namespace (The Sandbox)**

- Apps here run with **1 replica**. This is for validation. If an update breaks the blog here, nobody sees it but me.

**4. `prod` Namespace (The Holy Land)**

- Apps here run with **2 replicas** for HA.
- **Matomo** runs here to track analytics.

### The "External" Guardians

I made a strategic decision to keep two specific services _outside_ the Kubernetes cluster, running directly on Proxmox:

1. **Gitea (External VM):** My Git server. It lives outside to solve the "Bootstrap Problem." I can't deploy the cluster _from_ Git if the Git server is _inside_ the cluster that is currently down.
2. **Uptime Kuma (LXC):** The watchdog. It monitors the cluster from the outside. If the API stops responding, it alerts me.

## 1.0.3 Defense & Resilience

A data center isn't a data center without redundancy.

**Storage: Longhorn** — I'm using **Longhorn** for distributed block storage. It replicates my persistent data (database volumes, etc.) across the nodes. If Node 1 dies, the data is accessible on Node 2. It's overkill for a single physical SSD, but it protects against VM corruption.

**The 3-2-1 Backup Strategy** — Data loss is the only thing that scares me more than social interaction.

- **3 Copies:** Live Data, Local Backup, Cloud Backup.
- **2 Media Types:** SSD (Live) and HDD (Backup).
- **1 Offsite:**
  - **Daily:** Velero snapshots the cluster to a local 2TB NFS share.
  - **Weekly:** The NFS share syncs to **Backblaze B2**.

## 1.0.4 Conclusion

I now have a cluster that can self-heal, auto-scale, and back itself up to the cloud. Is it necessary? **No.** Did I spend more time configuring the CI/CD pipeline than actually writing code? **Yes.**

Do I regret it? **Nope.**

Now, all that's left is to actually deploy the apps. But that... is a problem for the next post.

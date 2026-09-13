---
author: Kayra
pubDatetime: 2024-12-31T00:00:00Z
title: "Homelab v1.0 – From Server to Data Center (Homelab_v4.1_UltraOptimized(3).md)"
slug: homelab-v1-0-from-server-to-data-center
featured: false
draft: false
tags: ["selfhosting", "kubernetes"]
category: journal
format: writeup
description: Throwing away the "simple Ubuntu server" plan and committing to a full K3s cluster with Proxmox, Longhorn, 3-2-1 backups, and four production-grade namespaces. Also known as "over-engineering for the vibes."
---

At this point I was rethinking therapy. I started complicating things again, that's my thing. I looked at the architecture, then I was like: _that's not enough aura farming, I need more._

It was the moment I moved from wanting a homelab to building a data center.

## Diet Kubernetes

The original plan was simple: Proxmox, a few Docker containers, two, maybe 3 Debian virtual machines? Sort of. But then, plain Docker containers are not what I want to be known for, and I wanted to learn Kubernetes.

So I kept most things, but then for the Docker containers I went for K3s, which is just diet Kubernetes. Reading and learning about Kubernetes was nice: with a Docker container you have to manually manage it, as in specify how much CPU and RAM it needs, and if you need 2 copies you have to fulfill that manually. With Kubernetes, I don't need that. I just tell it: that app needs 0.5 CPU, 1 GB RAM, and I need 2 copies. What it will do is find a node (think virtual machine) that's appropriate for that and run the app there. It will get the 2 instances up, and if one crashes it will self-heal. If there is a traffic spike, Kubernetes can do more instances to cover that (really useful feature for my homelab that most likely I will be the only visitor of :)

## High Availability

So if you thought I would just run K3s on one big VM and that's it, you are wrong. At this point I don't need to mention it, but as you guessed, I complicated it again: I needed high availability. What would happen if that VM had an issue? First, let's explain the lingo. There are nodes; a node you can think of as a virtual machine. It is not exactly that, but just for the sake of simplicity. Then there is the cluster, which is the group of nodes you have. I talk to the cluster, say I want one app with these specs, and the nodes will organize it and it will happen. Again, simplification, cause that's not a technical guide.

So for high availability, the sweet spot is 3 nodes. Again, without going deep technical, the tech being used needs the majority of the members to agree before doing a write/update. To reach that, floor(N/2)+1 needs to agree. So if I have only 2, floor(2/2)+1 = 2, I need 2 members to agree before writing/editing, which means if 1 node goes down, I will be stuck with read-only: I can't do new deployments or writes. With 3, floor(3/2)+1 is 2, so if one fails there is no issue, the other 2 will manage.

## The Layout

Now I started adding namespaces, which you can consider a virtual space in the cluster where I can add rules/policies and all.

So I divided it like this:

1. `mgmt` Namespace (The Control Room)
   - ArgoCD: The GitOps engine. It watches my Gitea repo. If I push code, ArgoCD updates the cluster.
   - Sealed Secrets: Encrypts my passwords so I can safely commit them to Git.

2. `platform` Namespace (The Utility Belt)
   - Observability: Prometheus (metrics), Grafana (dashboards), and Loki (logs). If the cluster is slow, this tells me why.
   - CI/CD: Woodpecker CI. Runs pipelines and builds Docker images.
   - Ingress: Traefik + Cert-Manager. Handles SSL certificates automatically via Cloudflare.

3. `stage` Namespace (The Sandbox)
   - Apps here run with 1 replica. This is for validation. If an update breaks the blog here, nobody sees it but me.

4. `prod` Namespace (The Holy Land)
   - Apps here run with 2 replicas for HA.
   - Matomo runs here to track analytics.

Then I kept 2 things outside the Kubernetes cluster, directly on the Proxmox host:

- Gitea (External VM): My Git server. It lives outside to solve the "Bootstrap Problem." I can't deploy the cluster from Git if the Git server is inside the cluster that is currently down.
- Uptime Kuma (LXC): The watchdog. It monitors the cluster from the outside. If the API stops responding, I get an alert.

## Backups

After that, I needed some data backups. Longhorn replicates the data across the nodes. If one node dies, the data will still be accessible on the other node.

Then, a backup strategy. I learned about that thing, 3-2-1:

- 3 Copies: Live Data, Local Backup, Cloud Backup.
- 2 Media Types: SSD (Live) and HDD (Backup).
- 1 Offsite:
  - Daily: Velero snapshots the cluster to a local 2TB NFS share.
  - Weekly: The NFS share syncs to Backblaze B2.

The whole thing is a huge overkill for what I needed. I am kind of building a full data center to host a static blog, but I am doing it to learn things, and I was hoping I would enjoy it. Spoiler alert: I didn't.

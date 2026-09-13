---
author: Kayra
pubDatetime: 2025-01-14T00:00:00Z
title: "Homelab v1.4 – The Governance Wall: eBPF, Tunnels, and the Base64 Trap"
slug: homelab-v1-4-the-governance-wall
featured: false
draft: false
tags: ["selfhosting", "kubernetes"]
category: journal
format: writeup
description: Namespaces, resource quotas, Sealed Secrets, and finally exposing the cluster to the internet through a Cloudflare Tunnel, along with a 502 that was actually a win because it meant the packets got all the way through.
---

Now we are done with the hello world phase: the applications to use the thing now?

## Resource Quotas

I started with very low resource allocations, but I quickly hit a wall. Most app defaults are just too generous for a lean lab, and I had many fights with installation errors caused by resource quotas.

In Kubernetes, there are:

- **Requests:** The "Reserved Seat." The resources a pod is guaranteed to have before it even starts.
- **Limits:** The "Ceiling." How far a pod can go before the kernel steps in to throttle it (CPU) or kill it (Memory).

This was the final config I settled on:

![Resource quotas and limits configuration](/images/migrated/homelab-v1-4-resource-config.png)

Since I was increasing cluster resources, I had to bump the physical specs of my Proxmox VMs. This was the perfect time to test high availability. Because I already had kube-vip running, I migrated the nodes one at a time, achieving the dream: zero downtime.

With the foundation solid, I began my IaC (Infrastructure as Code) backup work. I gathered the configurations and saved them locally. It's not a full-blown Git repository yet, but it's the "cold storage" I need until the next phase.

## The Services

Now on the list is the load balancer. Originally, I had kube-vip-cloud-provider installed alongside kube-vip. But in a cluster, you can only have one driver. Since I was already running Cilium, keeping the kube-vip provider was like having two people fight over the steering wheel. After checking with my consultants (LLMs), I decided on Cilium as it is objectively superior here, especially with eBPF handling the networking logic directly in the kernel. I deleted the redundant cloud-provider pod and reconfigured kube-vip to disable `svc_enable`. Now, kube-vip only manages the Control Plane VIP, while Cilium ignores the noise and handles the service IPs.

Next, Sealed Secrets. Standard Kubernetes secrets are not actually encrypted; they are just Base64 encoded. For someone trying to maximize security, that's unacceptable. Sealed Secrets encrypts the data with a key only my cluster holds, so the Git repo gets ciphertext and nothing else. The installation was smooth, and for once, the logs stayed green.

Next, ArgoCD. It was where the real struggle began. I tried to install it multiple times, but the installation kept failing because of my initial, strict resource quotas. Pods couldn't even get created because their requests were over the namespace limits.

Beyond just the quotas, I had to manually tune the ArgoCD defaults. Some of them were just absurd, requesting massive amounts of resources that my lab didn't have to spare. I had to slash those defaults to match my version of reality, and increase the quota limits before it was up.

## The Domain

Now, getting my domain up.

Cloudflare Tunnel. This required Cert-Manager to handle the SSL certificates. Again, I had a brief resource-quota skirmish before setting the proper defaults.

Then came the "Cloudflare permissions" saga. I created a token and gave it DNS Edit. It failed initially. I realized I had committed a sin: I forgot my own domain was `novaden.dev`, not `novaden.com`. I fixed the domain and added the Read permission just to be safe (though I'm still not sure if Edit would have been enough on its own).

The moment of truth: I typed `argo.novaden.dev` into my browser. It worked! Well, it showed a 502 Bad Gateway, but it was still a win. It means the internet reached my cluster. I switched to HTTP because the tunnel agent and ArgoCD were having a protocol mismatch. Since the traffic is already secured by the tunnel's outbound encryption, there was no need to force internal SSL handshakes on the pod-to-pod hop. The ArgoCD login page finally popped up.

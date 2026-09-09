---
author: Kayra
pubDatetime: 2025-01-14T00:00:00Z
title: "Homelab v1.4 — The Governance Wall: eBPF, Tunnels, and the Base64 Trap"
slug: homelab-v1-4-the-governance-wall
featured: false
draft: false
tags: ["selfhosting"]
category: journal
series: homelab
seriesOrder: 1.4
description: Namespaces, resource quotas, Sealed Secrets, and finally exposing the cluster to the internet through a Cloudflare Tunnel — along with a 502 that was actually a win because it meant the packets got all the way through.
---

## 1.4.1 Introduction: The "Day 2" Wall

The cluster was alive. The "Hello World" phase was over, and I was ready to deploy my actual applications. However, before doing that, I needed to put proper governance in place to stick to my production-grade narrative.

I defined my core namespaces to keep the "Management Plane" separate from the "Data Plane":

- **`mgmt`**: The brains of the operation (ArgoCD and Sealed Secrets).
- **`platform`**: The heavy lifters (Cert-Manager, Monitoring, Tunnels).
- **`stage`**: My staging and testing playground.
- **`prod`**: The holy land where my actual apps live.

I started with very low resource allocations, but I quickly hit a wall. Most app defaults are just too generous for a lean lab. After several fights with installation errors caused by resource quotas, I finally landed on a configuration that balanced stability with my GMKtec's hardware limits.

In Kubernetes, **Requests** and **Limits** are your primary dials for resource allocation.

- **Requests**: The "Reserved Seat." The resources a pod is guaranteed to have before it even starts.
- **Limits**: The "Ceiling." How far a pod can go before the kernel steps in to throttle it (CPU) or kill it (Memory).

This was the final config I settled on:

![Resource quotas and limits configuration](/images/migrated/homelab-v1-4-resource-config.png)

Since I was increasing cluster resources, I had to bump the physical specs of my Proxmox VMs. This was the perfect time to test high availability. Because I already had `kube-vip` running, I migrated the nodes one at a time, achieving the dream: zero downtime.

## 1.4.2 The IaC Snapshot

With the foundation solid, I began my IaC (Infrastructure as Code) backup work. I gathered the configurations and saved them locally. It's not a full-blown Git repository yet, but it's the "cold storage" I need until the next phase.

## 1.4.3 The Load Balancer Pivot: Cilium Over Everything

Next on the list was the Load Balancer. Originally, I had `kube-vip-cloud-provider` installed alongside `kube-vip`. But in a cluster, you can only have one driver. Since I was already running **Cilium**, keeping the `kube-vip` provider was like having two people fight over the steering wheel.

Cilium is objectively superior here, especially with **eBPF** handling the networking logic directly in the kernel. I deleted the redundant cloud-provider pod and reconfigured `kube-vip` to disable `svc_enable`. Now, `kube-vip` only manages the Control Plane VIP, while Cilium ignores the noise and handles the service IPs.

## 1.4.4 Sealed Secrets: Fixing the Base64 Trap

It was finally time to install services. First up: **Sealed Secrets**.

Standard Kubernetes secrets are not actually encrypted; they are just **Base64 encoded**. It's basically writing your password in Morse code, anyone can decode it in a second. For someone trying to maximize security, that's unacceptable. Sealed Secrets solves this by encrypting the data using a secure algorithm that only my cluster can decrypt. The installation was smooth, and for once, the logs stayed green.

## 1.4.5 ArgoCD & The Resource Grudge Match

ArgoCD was where the real struggle began. I tried to install it multiple times, but the installation kept failing because of my initial, strict resource quotas. The pods were being blocked from even being created because their requirements exceeded the namespace limits.

Beyond just the quotas, I had to manually tune the ArgoCD defaults. Some of them were just absurd — requesting massive amounts of resources that my lab didn't have to spare. I had to slash those defaults to match my version of reality, and increase the quota limits before the ride finally became smooth.

## 1.4.6 The Tunnel: `novaden.dev` Goes Live

The final piece was the **Cloudflare Tunnel**. This required **Cert-Manager** to handle the SSL certificates. Again, I had a brief resource-quota skirmish before setting the proper defaults.

Then came the "Cloudflare permissions" saga. I created a token and gave it `DNS Edit`. It failed initially. I realized I had committed a sin: I forgot my own domain was **`novaden.dev`**, not `novaden.com`. I fixed the domain and added the `Read` permission just to be safe (though I'm still not sure if `Edit` would have been enough on its own).

The moment of truth: I typed `argo.novaden.dev` into my browser. It worked! Well, it showed a **502 Bad Gateway**, but it was still a win. It means the internet reached my cluster. I switched to HTTP because the tunnel agent and ArgoCD were having a protocol mismatch. Since the traffic is already secured by the tunnel's outbound encryption, there was no need to force internal SSL handshakes on the pod-to-pod hop. The ArgoCD login page finally popped up.

## 1.4.7 The "Ouch I Fucked Up" Scoreboard

**Current Score: 10 Ls**

### Mistake #10: The Quota/Default Standoff (1 Point)

- **The Issue:** Setting strict Resource Quotas and then trying to install "heavy" default Helm charts.
- **The Consequence:** Pods stayed in a `Forbidden` state; the installation failed before a single container even pulled an image.
- **The Lesson:** Quotas are only useful if you actually know the baseline of the apps you're installing. "Hardening" before "Understanding" is just a recipe for a locked door.

### Mistake #11: The TLD Identity Crisis (.dev vs .com) (0.5 Points)

- **The Issue:** Configuring Cert-Manager manifests for `novaden.com` when I actually own `novaden.dev`.
- **The Consequence:** "Zone Not Found" errors that led me down a 30-minute rabbit hole of checking API permissions.
- **The Lesson:** DNS doesn't care about your muscle memory. Check the suffix.

### Mistake #12: The Protocol Mismatch (1 Point)

- **The Issue:** Pointing a Cloudflare Tunnel (HTTPS) at an "Insecure" ArgoCD service (HTTP).
- **The Consequence:** "Connection Reset by Peer" and a 502 Bad Gateway because the Tunnel was trying to encrypt a connection that was already stripped of SSL.
- **The Fix:** Changing the Tunnel origin to HTTP on Port 80.
- **The Lesson:** End-to-end encryption is the goal, but you have to know where the "End" actually is.

### Mistake #13: The Zombie Provider (0.5 Points)

- **The Issue:** Leaving a "scaled-to-zero" `kube-vip-cloud-provider` in the cluster while trying to let Cilium take over LoadBalancer duties.
- **The Consequence:** Confusion in the "Source of Truth" — it's never a good idea to have two different drivers for the same steering wheel, even if one is "sleeping."
- **The Fix:** A delete of the deployment and a config change to `kube-vip-ds`.

## 1.4.8 Conclusion

We now have a working Load Balancer, strict namespace governance, Sealed Secrets, a Cloudflare Tunnel, and ArgoCD. The infrastructure is officially reachable from the outside world, securely. It feels amazing.

---
author: Kayra
pubDatetime: 2025-01-14T00:00:00Z
title: "Homelab v1.5 — Real Governance: OIDC, Sealed Secrets, and the App-of-Apps Meltdown"
slug: homelab-v1-5-real-governance
featured: false
draft: false
tags: ["selfhosting"]
category: journal
series: homelab
seriesOrder: 1.5
description: Single Sign-On with Gitea, Sealed Secrets for real, a Kyverno policy that broke the cluster I was trying to protect, and an App-of-Apps refactor that ended with me deleting the Cloudflare tunnel to force a sync (don't ask).
---

## 1.5.1 Introduction: Real Governance

Now that the cluster was reachable from the internet, it was time to stop playing around with manual configs and move to a real setup. My goal for this phase was simple: implement **Single Sign-On (SSO)** so I'm not managing a dozen local logins and to protect unauthorized services, and finally move my secrets into a GitOps-compliant workflow, IaC style.

The plan was to use **Gitea** as my identity provider. For apps that support it (like ArgoCD), I'd use native OIDC. For the simple stuff that doesn't have auth, I'd layer on **Traefik + oauth2-proxy**.

## 1.5.2 Using Sealed Secrets for Real

I had **Sealed Secrets** installed from the last session, but I hadn't actually done the work of converting my secrets. I finally sat down, used `kubeseal`, and migrated my `oauth2-proxy` credentials and Cloudflare tokens into encrypted manifests.

I didn't seal every single secret in the cluster, though. Things like Helm release metadata or Cert-Manager keys stay as regular secrets because they are managed by their own controllers. If I try to "own" those with Sealed Secrets, I'm just going to break the automation that's supposed to handle them.

## 1.5.3 The OIDC Troubleshooting Saga

Getting Gitea and ArgoCD to talk to each other was a headache. I hit two main issues that kept me stuck for a while.

First, the **Issuer URL**. Gitea was trying to identify itself as a local IP (`http://192.168.1.60:3000/`). When ArgoCD saw that, it basically said "I don't know who you are," because it was expecting `https://gitea.novaden.dev/`. I had to go into Gitea and fix the `ROOT_URL` so the OIDC handshake actually matched.

Then, there was the **ArgoCD Label Trap**. I had the secret created, and I could see the keys were there, but ArgoCD kept screaming that the `clientSecret` was missing. It turns out ArgoCD is picky. It won't even look at a secret unless it has the right labels (`app.kubernetes.io/part-of=argocd`). Once I added those to my SealedSecret template, the warning disappeared and the login worked.

## 1.5.4 Mirroring and the Gitea Bot

I'm keeping **GitHub** as my primary source of truth, that's where I want the "credit" for my work, but I set up **Gitea** to act as a local mirror.

I created the `novaden-dev` organization, gave it a logo, and made a bot user for ArgoCD. I had a brief moment of "why isn't this working?" before realizing I hadn't actually added the bot to the organization. Once I gave it `repository: read` access and a fresh token, ArgoCD was finally able to pull from the mirror.

## 1.5.5 The Kyverno Registry Cascades and Policy Lockdown

This was where things got truly messy. I installed **Kyverno** to handle policies, starting with a basic rule to disallow privileged containers. What followed was a series of "cascading failures":

1. **The 403 Forbidden:** For some reason, my pulls from `ghcr.io` (GitHub's registry) were getting blocked.
2. **The Bitnami 404:** I tried to point to Bitnami images instead, but since the Broadcom acquisition, a lot of their old tags have just vanished.
3. **The Brain/Hand Mismatch:** In a moment of desperation, I tried a global registry override in the Helm chart. This was the big one. I accidentally told the Kyverno **Controller** (the brain) to pull a `kubectl` image (the hands). The pod crashed instantly because it was being fed Kyverno commands that a basic `kubectl` image doesn't understand.

I had to split the config. I left the Controllers on their official registry and pointed the utility "Cleanup" jobs to the **AWS Public ECR mirror**. That mirror is reliable and actually has the images I needed.

Once Kyverno was finally up, I applied the `disallow-privileged` policy. **Everything broke.** Most of my management apps (Cilium, etc.) require privileged access to function. Because I applied the policy globally without thinking, my own platform pods started failing. I had to scramble to add proper exclusions to the policy so the cluster could actually run while still protecting the `stage` and `prod` namespaces.

## 1.5.6 The App-of-Apps Meltdown

The final boss was the "App-of-Apps" refactor. This was a multi-stage fight where I kept tripping over my own repo structure, new territory for me, so it was somewhat expected, to be honest.

### Stage 1: The Invisible Apps

I set up my Root App (Bootstrap), but nothing was showing up. I realized I hadn't enabled **recursive** discovery in ArgoCD. My apps were nested in subfolders, and Argo was just ignoring them.

### Stage 2: The Terrible Layout

I turned on recursive mode, and the apps appeared, but the repo layout was a mess. The hierarchy didn't make sense. I had to tear it down and move to the current structure:

- **`bootstrap/`**: The entry point.
- **`cluster/`**: Namespaces, Quotas, Policies.
- **`workloads/`**: The actual apps.

### Stage 3: The Desperation Move (Locking Myself Out)

Even with the new layout, I had massive **Out of Sync** issues with the apps. I was hard-refreshing and syncing repeatedly, but nothing was turning green. In a moment of total desperation, I deleted the `cloudflared` deployment, fully knowing that it would lock me out of the UI, but it was my last card. I instantly lost access to the ArgoCD UI and had to use `kubectl apply` on the manifest, but it still wasn't green!

It turned out the sync issues were caused by **stale annotations** in the deployment YAML files within the repo. ArgoCD was seeing metadata it didn't like and was refusing to settle. I had to go through and scrub all the garbage annotations out of the files.

### Stage 4: The Final Green

Everything synced except the "Cluster" app, which was still showing the `cluster-core` resources (Namespaces/Quotas). I can't even remember exactly what fixed it; it happened just a few hours ago and I've totally forgotten, brain rot at its finest. I think I just manually applied the update to force the state, but finally, it clicked and everything was green except for a few apps. For those, it was just a matter of clearing the empty `syncPolicy: {}` blocks, and for the first time all day, ArgoCD was completely green.

## 1.5.7 The "Ouch I Fucked Up" Scoreboard

**Current Score: 13.5 Ls**

### Mistake #14: The Global Registry Hammer (1 Point)

- **The Issue:** Forcing a Kyverno Controller to run a `kubectl` image.
- **The Consequence:** Instant `CrashLoopBackOff` due to flag mismatches.
- **The Lesson:** "Global" settings in Helm are a trap if the chart uses multiple different images.

### Mistake #15: The Secret Invisibility Cloak (1 Point)

- **The Issue:** Missing ArgoCD labels on the OIDC secret.
- **The Consequence:** Hours of debugging "Missing Key" errors for a secret that was clearly there.
- **The Lesson:** Add labels?

### Mistake #16: The Privileged Policy Lockdown (1.5 Points)

- **The Issue:** Applying `disallow-privileged` without exclusions for system apps.
- **The Consequence:** My own management plane stopped being able to deploy pods.
- **The Lesson:** Security is great, but "Hardening" before "Configuring" just locks you out of your own house.

## 1.5.8 Conclusion

The infrastructure is officially a "Platform" now. We have SSO, encrypted secrets, a mirror for local resilience, and a policy engine that is (finally) configured correctly. We are getting there.

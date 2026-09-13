---
author: Kayra
pubDatetime: 2025-01-14T00:00:00Z
title: "Homelab v1.5 – Real Governance: OIDC, Sealed Secrets, and the App-of-Apps Meltdown"
slug: homelab-v1-5-real-governance
featured: false
draft: false
tags: ["selfhosting", "kubernetes", "gitops"]
category: journal
format: writeup
description: Single Sign-On with Gitea, Sealed Secrets for real, a Kyverno policy that broke the cluster I was trying to protect, and an App-of-Apps refactor that ended with me deleting the Cloudflare tunnel to force a sync (don't ask).
---

Now since I have too many apps, SSO would be appreciated. I have this bad habit of either setting weak passwords or setting complicated passwords but then pasting them in some random place, so SSO would go a long way.

First, let's seal the secrets. I had Sealed Secrets installed from the last session, but I hadn't actually done the work of converting my secrets. I used `kubeseal`, and migrated my oauth2-proxy credentials and Cloudflare tokens into encrypted manifests.

I didn't seal every single secret in the cluster, though. Things like Helm release metadata or Cert-Manager keys stay as regular secrets because they are managed by their own controllers. If I try to own those with Sealed Secrets, I'm just going to break the automation that's supposed to handle them.

## The OIDC Headache

Getting Gitea and ArgoCD to talk to each other was a headache. I hit two main issues that kept me stuck for a while.

First, the Issuer URL. Gitea was trying to identify itself as a local IP (`http://192.168.1.60:3000/`). When ArgoCD saw that, it basically said "I don't know who you are," because it was expecting `https://gitea.novaden.dev/`. I had to go into Gitea and fix the `ROOT_URL` so the OIDC handshake actually matched.

Then, there was the ArgoCD Label Trap. I had the secret created, and I could see the keys were there, but ArgoCD kept screaming that the `clientSecret` was missing. It turns out ArgoCD is picky. It won't even look at a secret unless it has the right labels (`app.kubernetes.io/part-of=argocd`). Once I added those to my `SealedSecret` template, the warning disappeared and the login worked.

## The Mirror

I'm keeping GitHub as my primary source of truth; that's where I want the "credit" for my work. But I set up Gitea to act as a local mirror.

I created the `novaden-dev` organization, gave it a logo, and made a bot user for ArgoCD. Once I gave it `repository: read` access and a fresh token, ArgoCD was finally able to pull from the mirror.

## Kyverno

Now let's enforce some governance. I installed Kyverno to handle policies, starting with a basic rule to disallow privileged containers. What followed was a series of "cascading failures":

- **The 403 Forbidden:** For some reason, my pulls from `ghcr.io` (GitHub's registry) were getting blocked.
- **The Bitnami 404:** I tried to point to Bitnami images instead, but since the Broadcom acquisition, a lot of their old tags have just vanished.
- **The Brain/Hand Mismatch:** In a moment of desperation, I tried a global registry override in the Helm chart. This was the big one. I accidentally told the Kyverno Controller (the brain) to pull a `kubectl` image (the hands). The pod crashed instantly because it was being fed Kyverno commands that a basic `kubectl` image doesn't understand.

I had to split the config. I left the Controllers on their official registry and pointed the utility "Cleanup" jobs to the AWS Public ECR mirror. That mirror is reliable and actually has the images I needed.

Once Kyverno was finally up, I applied the `disallow-privileged` policy. **Everything broke.** Most of my management apps (Cilium, etc.) require privileged access to function. Because I applied the policy globally without thinking, my own platform pods started failing. I had to scramble to add proper exclusions to the policy so the cluster could actually run while still protecting the `stage` and `prod` namespaces.

## App-of-Apps

This was a multi-stage fight where I kept tripping over my own repo structure. New territory for me, so it was somewhat expected, to be honest.

**Stage 1: The Invisible Apps.** I set up my Root App (Bootstrap), but nothing was showing up. I realized I hadn't enabled recursive discovery in ArgoCD. My apps were nested in subfolders, and Argo was just ignoring them.

**Stage 2: The Terrible Layout.** I turned on recursive mode, and the apps appeared, but the repo layout was a mess. The hierarchy didn't make sense. I had to tear it down and move to the current structure:

- `bootstrap/`: The entry point.
- `cluster/`: Namespaces, Quotas, Policies.
- `workloads/`: The actual apps.

**Stage 3: The Desperation Move (Locking Myself Out).** Even with the new layout, I had massive Out of Sync issues with the apps. I was hard-refreshing and syncing repeatedly, but nothing was turning green. In a moment of total desperation, I deleted the `cloudflared` deployment, fully knowing that it would lock me out of the UI, but it was my last card. I instantly lost access to the ArgoCD UI and had to use `kubectl apply` on the manifest, but it still wasn't green!

It turned out the sync issues were caused by stale annotations in the deployment YAML files within the repo. ArgoCD was seeing metadata it didn't like and was refusing to settle. I had to go through and scrub all the garbage annotations out of the files.

**Stage 4: The Final Green.** Everything synced except the "Cluster" app, which was still showing the `cluster-core` resources (Namespaces/Quotas). I can't even remember exactly what fixed it; it happened just a few hours ago and I've totally forgotten, brain rot at its finest. I think I just manually applied the update to force the state, but finally, it clicked and everything was green except for a few apps. For those, it was just a matter of clearing the empty `syncPolicy: {}` blocks, and for the first time all day, ArgoCD was completely green.

So the platform was done: SSO, sealed secrets, working policies, and a fully green App-of-Apps. What happened after that is the real ending, and it gets its own post: [Homelab v2.0 – The Useful One](/posts/homelab-v2-0-the-useful-one).

---
author: Kayra
pubDatetime: 2024-12-31T00:00:00Z
title: "Homelab v1.2 – The Supply Chain: Golden Images & The Source of Truth"
slug: homelab-v1-2-the-supply-chain
featured: false
draft: false
tags: ["selfhosting"]
category: journal
description: Solving the bootstrap paradox with Cloud-Init templates, a self-hosted Gitea server outside the cluster, and why SQLite wasn't going to cut it when I'm hoarding 32GB of RAM.
---

Now that I have the host system done and the networking done, I will start with adding the actual machines and Docker containers.

Bootstrap Paradox: Occurs when any event, such as an action, information, an object, or a person, ultimately causes itself, as a consequence of either retrocausality or time travel.

If I build the cluster, where do I store the configuration files? In Git. Okay, where does Git live? Ideally, self-hosted on the server. But the server isn't built yet because I don't have the configuration files... which belong in Git.

So let's build the base first: the source of truth.

## The Golden Image

I created a golden image and configured it using Cloud-Init. When the VM boots for the first time, it reads a small configuration file and sets up the hostname, IP address, user accounts, and SSH keys automatically.

I didn't use the GUI much: AI-written scripts.

## Gitea

For my Git server, I chose Gitea. It's lightweight, fast, and looks enough like GitHub that I don't feel homesick. I deployed it on a dedicated VM (`192.168.1.60`) running outside the Lab network.

The default Gitea installation uses SQLite. It's simple, just a file on a disk. It uses almost zero RAM. It is perfectly fine for a single user. So, naturally, I didn't use it... I did PostgreSQL. To convince myself, I got this from an LLM:

> "SQLite struggles with concurrency. Since you plan to use Gitea as a Container Registry (storing Docker images) and potentially for CI/CD pipelines, you need a database that wouldn't choke when multiple services hit it at once."

I deployed the whole stack using Docker Compose, and the configuration is version-controlled.

## The Organizations

I then set up 2 organizations:

- `infrastructure` (Private): This contains `cluster-manifests`, the repository that defines the "Desired State" of my data center. If I delete this repo, my lab ceases to exist.
- `applications` (Public): This is where my actual code for applications and blogs lives.

The naming convention is simple: `infra-*`, `app-*`, and `tools-*`.

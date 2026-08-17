---
author: Kayra
pubDatetime: 2024-08-07T16:47:49Z
modDatetime: 2025-04-02T18:10:28Z
title: "Penetration Testing Fundamentals"
slug: penetration-testing-process
featured: false
draft: false
tags: ["security"]
category: notes
description: "What penetration testing is, the three engagement types (black, grey, white box), the domains you can test, and the process the work moves through."
---

## Introduction

Penetration testing is an authorized attempt to find all the vulnerabilities in a system. The word that carries the weight there is **authorized**. It is the line between a penetration test and a crime. You have written permission, a scope that says what you can touch, and an objective agreed with the owner before you start.

The "find all" part matters too. The job is not to break in once and stop. It is to map every way in, so the owner can close all of them rather than the one you happened to find first.

## Types of Engagement

Engagements are usually grouped by how much the client tells you before you start. The less you are given, the more the test looks like a real attack, but the more time you burn on discovery instead of depth.

| Type | What you're given | What it simulates |
|------|-------------------|-------------------|
| Black box | Little to nothing, often just a company name or an IP range | An outside attacker with no inside knowledge |
| Grey box | Partial access, e.g. low-privilege credentials or some documentation | An attacker who already has a foothold, or a regular user turning malicious |
| White box | Full access: source code, architecture diagrams, credentials | An insider, or a review aiming for the widest possible coverage |

The trade-off is coverage versus realism. Black box is the most realistic but time-boxed, so you can miss things a real attacker with months would eventually find. White box is the most thorough because nothing is hidden from you, but it looks the least like an outside attack. Grey box is the common middle ground.

## Domains

Penetration testing is not one skill set. The target surface decides the tools, and the knowledge you need. The same engagement can span several of these at once.

- **Network**: internal and external infrastructure, hosts, services, and Active Directory.
- **Web application**: the most common surface, covering logic flaws, injection, and broken authentication.
- **API**: the REST and GraphQL endpoints that sit behind modern apps and mobile clients.
- **Mobile**: Android and iOS apps, plus the back ends they talk to.
- **Cloud**: misconfigurations and identity issues in AWS, Azure, or GCP.
- **Wireless**: Wi-Fi networks and the devices on them.
- **Social engineering**: phishing and the human layer, where the target is a person, not a host.
- **Physical**: badge cloning, tailgating, and getting into the building.

## The Process

Most people picture a penetration test as a straight line: scan the target, find a hole, exploit it, done. In practice the work loops. Finishing one stage usually throws you back into an earlier one. You pop a box, and it hands you credentials that send you right back to enumeration on the next system.

The stages below are the structure that work moves through. Treat them as a map of where you might be, not a checklist you complete top to bottom. Information Gathering is the one everything else rests on. The more thorough your enumeration, the more options you have at every later stage.

| Stage | What happens |
|-------|--------------|
| Pre-Engagement | Agree on scope and objectives, and prepare the paperwork (contracts, rules of engagement, authorization). |
| Information Gathering | Enumerate every in-scope system. The most important stage, since every step after it builds on what you find here. |
| Vulnerability Assessment | Identify weaknesses based on the information gathered. |
| Exploitation | Exploit the identified weaknesses to gain initial access. |
| Post-Exploitation | Work from that initial access, mainly toward privilege escalation. |
| Lateral Movement | Use a compromised system to reach other in-scope systems. |
| Proof-of-Concept | Capture evidence, usually screenshots or video, and optionally a script that automates the exploit. |
| Post-Engagement | Document, present, and deliver the findings to the client. |

Because the process loops, these stages feed each other. Lateral Movement drops you onto a new system, which restarts Information Gathering for that host. Post-Exploitation on one machine can hand you credentials that turn into Exploitation somewhere else. The work is a cycle, not a straight line.

---
author: Kayra
pubDatetime: 2024-09-15T12:00:00Z
title: eWPTXv3
slug: ewptxv3
category: cert-review
tags: ["ewptx", "ine"]
description: "I took the eWPTXv3 the day after passing the eCPPT, still tired, and finished it in 9 hours. It wore the eXtreme label but felt like a victory lap."
draft: true
featured: false
---

I passed the eCPPT the day before this one. That should have been a reason to rest, but the eWPTx had that big, bold "eXtreme" label on it, and I wanted to know if it was deserved. I skimmed the syllabus (titles only) and it looked manageable, so I booked it and jumped in while I still had momentum.

This time I was slightly less of a zombie: six hours of sleep (a personal record) and a midday start. It took me 9 hours total, with breaks to eat, hop into a quick meeting, and remind my legs they still work. Way better than the 15-hour eCPPT.

<figure><img src="/images/ewptxv3-badge.png" alt="eWPTXv3 badge" width="227"><figcaption>eWPTXv3 badge</figcaption></figure>

## The Format

If you've read my eCPPT post, this is nearly the same setup, just with web targets: 18 hours, 45 questions mixing MCQs and hands-on challenges, instant pass/fail after submission, and a browser-accessed Kali machine. Progress saves between tab closes, lab restarts wipe everything.

Same drill on the restrictions: no internet, no installing tools. Though honestly, you don't even need anything that isn't already there.

And same scattered-question trick, Q1, Q30, Q45 all pointing at the same target. Read everything first.

## Preparation

Reviews of the eWPTXv3 are scarce online, so I went in with almost no guidance.

Did I open the INE material? No. My prep was everything from before: the CPTS path on HackTheBox, 50+ boxes from HackTheBox and Proving Grounds, and 20-30 PortSwigger labs. I skimmed the slides, glanced at the labs, and called it good.

A few topics weren't covered by the CPTS path, though:

- LDAP Injection
- Deserialization Attacks
- Introduction to NoSQL Injection
- API Attacks

The HTB modules on those (or their TryHackMe equivalents) cover them. They're Tier 3 and my subscription only went up to Tier 2, so I gave the INE labs and videos a quick look instead. You should go through the HTB modules properly if you can.

Tools I remember using: Burp Suite obviously, SQLMap, ffuf, nmap, curl, hashcat and john for the cracking bits, and an online CVSS calculator for the scoring questions. All of it ships on the exam's Kali machine, but get familiar with it beforehand, you don't want to be learning tool layouts mid-exam.

## The Ride

The exam was... surprisingly chill. I braced myself for next-level "eXtreme" web vuln madness and got a victory lap instead. Most of the challenges were stuff I'd already tackled in my HackTheBox and PortSwigger days, and some of the general-knowledge questions just screamed "Google it". If this is "eXtreme", I'm scared to see how basic the regular eWPT must be.

One thing worth knowing: the exam is designed to be finished in way less than 18 hours. When I hit the large website, after the basics (ports, directories, the usual), researching known CVEs pointed me in the right direction and saved me a lot of time.

## Struggles

Mostly the same headaches as the eCPPT: missing tools and no way to download the one script you forgot.

One question was genuinely broken, though. It asked about a service on a specific port, and that port just wasn't open. I triple-checked, scanned again, nothing. Bug? Some sneaky bypass I missed? No idea. I flagged it in the feedback for INE and moved on. It cost me two questions; otherwise it was smooth sailing.

## Advice

SQL injection is the star here, so go deep on it, past the basics. Enumeration barely shows up, which surprised me, but keep your nmap sharp for the initial recon anyway. Know your way around JWTs, both how they work and where they break. And stay warmed up on cracking hashes; the exam will ask.

## Final Thoughts

For learning, HTB Academy is great. As a student you get all Tier 2 modules for $8 a month, which also sets you up for the CBBH path. PortSwigger is free and just as good for web. Between the two, you don't really need to pay INE anything.

I took the eWPTx mainly for the CV letters. It's as simple as that.

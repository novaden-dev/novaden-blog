---
author: Kayra
pubDatetime: 2024-09-14T12:00:00Z
title: eCPPTv3
slug: ecpptv3
category: cert-review
tags: ["ecppt", "ine"]
description: "I skipped the INE material, prepared with the HTB CPTS path instead, and finished the 24-hour exam half-conscious. Notes on how it went and where it stands next to the OSCP and CPTS."
draft: true
featured: false
---

## The Format

24 hours, 45 questions split between MCQs and hands-on challenges, and you get the pass/fail verdict immediately after submitting. No waiting for once.

Everything runs in a Kali machine you access through the browser. It worked surprisingly well, though it disconnected briefly a few times. Your progress saves if you close and reopen the tab, but if you stop the lab, everything resets.

There's no internet access, so forget `apt-get install your_favorite_tool`. You copy-paste scripts by hand.

One thing to know before you start: the questions for the same machine are scattered all over (Q1, Q30, Q45...). I read all the questions first before touching anything, and I'd suggest you do the same. There's also one dynamic flag that changes with each lab restart, so once you submit it, that's it, no re-editing. Every other answer you can freely change until the end.

## Preparation

I skipped the INE material completely and followed the CPTS path on HackTheBox instead, plus 50+ boxes from Proving Grounds and HackTheBox. That was enough that I only skimmed the INE slides and labs before going in. The HTB Academy modules that mapped to the exam:

- Network Enumeration with Nmap
- Using the Metasploit Framework
- Password Attacks
- Login Brute Forcing
- Active Directory Enumeration & Attacks
- Linux Privilege Escalation
- Windows Privilege Escalation

For privilege escalation, Tib3rius's course carried me.

Tools-wise, I ended up using nmap, Hydra, WpScan, crackmapexec, Bloodhound, and a good chunk of impacket (GetNPUsers, GetADUsers, psexec, wmiexec). That covered everything the exam threw at me.

## The Ride

I started at midday, sleep-deprived. Don't do this. By hour 15 I was submitting answers half-conscious, my head kept dropping onto the keyboard, and a few questions went unanswered because my eyes wouldn't stay open.

The questions split evenly between Active Directory, Linux, and general topics. Some of the general ones felt like they escaped a CompTIA exam: no connection to the machines at all, just "Google it" trivia.

Small quality-of-life note: you get two terminals. Don't use lxterminal, QTerminal has better colors.

Difficulty-wise, the Linux questions felt like medium HackTheBox boxes. I couldn't finish all the AD questions, so I can't really judge that section, but the ones I did get through were simple and straightforward.

The question wording itself often drops hints. "Which account was exposed using technique X?" means the intended path is technique X. And brute-forcing was everywhere: I was cracking something at nearly every turn.

## Struggles

The attack machine lacks some tools I normally rely on, and you're not allowed to use your own machine. No internet either, so if a script isn't there, you're typing it in by hand.

The other trap: sometimes I popped a machine through a different vector than the intended one, and then couldn't answer the specific question they asked about it. Exploiting your way is not always the smart way.

## Advice

Study Active Directory properly, it's a big chunk of this exam. Get searchsploit under your fingers, you'll be reaching for it constantly. Privilege escalation matters too, and Tib3rius's course is the best resource I know for it. And when you get stuck, brute-force something. The exam rewards it more than it should.

## Final Thoughts

The INE videos and slides I skimmed were meh, but I didn't go deep, so take that with a grain of salt. I took the eCPPT mainly for the CV letters.

Honestly, the exam feels like a middle child. The autograded format skips the reporting skills you need in real work, OSCP has the recognition, CPTS is a tougher and richer learning experience. It's a solid test, but it's not the star of the show.

<figure><img src="/images/ecpptv3-badge.png" alt="eCPPTv3 badge" width="300"><figcaption>eCPPTv3 badge</figcaption></figure>

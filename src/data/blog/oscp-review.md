---
author: Kayra
pubDatetime: 2026-09-14T12:00:00+03:00
title: "OSCP – The Only Certificate I Knew as a Kid"
slug: oscp-review
category: cert-review
tags: ["oscp", "offsec"]
description: "How I prepared for the OSCP with 1.5 months of Proving Grounds boxes and no course content, how the exam day went, and whether it's worth OffSec's price."
draft: false
featured: false
---

OSCP was the only certificate I knew as a kid. I thought it was all there was to cybersecurity, naive at the time. I planned to get it in 2019, then 2020, then 2021... I kept a file on my desktop that I updated every year with the list of certificates I wanted, the OSCP as the final goal.

## What the Exam Looks Like

Six machines, fully practical, nothing multiple choice:

| Part | Machines | Flags | Points |
|---|---|---|---|
| Active Directory set | 3 | 3 for the set | 40 |
| Standalone machines | 3 | 2 each (`local.txt` and `proof.txt`) | 20 each |

You need 70 points to pass. You get 23 hours and 55 minutes for the exam itself, then another 24 hours to write and submit the report.

## Round One, 1.5 Years Ago

I first prepared for this about a year and a half ago, working through the Hack The Box CPTS path and a batch of Proving Grounds boxes. Then a payment issue got in the way, I never booked the exam, and the whole thing sat on the shelf.

## Round Two: Proving Grounds and Nothing Else

This time I skipped the course content completely. I got the voucher on a discount for 1,500 USD, added Proving Grounds Practice at 19.99 USD a month, and started grinding.

The plan was simple:

1. Put every machine from the TJ Null and Lainkusanagi lists into one list.
2. Solve them one by one, easiest first, to shake off the rust.
3. After each box, write a writeup and update my notes. I used AI for both to speed things up.

With work and other life things, I aimed for around 2 boxes on weekdays and 5 a day on weekends.

After 60 or so boxes I was so bored of the loop that I decided to just book the exam. Before booking, I ran through OSCP A, B, and C, Secura, and Poseidon, plus GOAD Light for some extra practice. From starting again to exam day, the whole prep took 1.5 months.

## Exam Day

I started at 9:00 AM and went at the machines in no particular order.

I took breaks whenever I felt I needed one:

- **After every flag**: about 5 minutes outside for a victory lap.
- **Midway**: a proper lunch break.
- **After hitting 70 points**: a full hour off.

Nine hours in, breaks included, I had 90 points:

- The full Active Directory set
- Two standalones with root
- One standalone without root

I spent one more hour on that last root flag, didn't get it, and used the rest of that time to collect the PoCs for the report. I ended the exam at 7:00 PM, 10 hours into the 24.

Apart from one technique, everything I needed was already in my notes, the same notes that became the [OSCP handbook](/collections/oscp) on this blog.

The walkthroughs won't end up on the blog though. I wrote one for every lab and box I solved, but OffSec doesn't allow publishing them.

## The Report

I took a break after ending the exam, then wrote the report the same night and submitted it Sep 5 at 3:01 AM. I used [SysReptor](https://github.com/Syslifters/sysreptor) with OffSec's template.

After refreshing my inbox daily for a while, the results came in Sep 11 at 11:04. By the way, the result shows up in the OffSec portal before the email is sent: go to the portal as if you're going to book a test, and if the exam is graded, you'll see there whether you passed.

## What Surprised Me

The exam was better than I expected. I went in thinking it would be a CVE search test: find the version, find the public exploit, run it. That was not the case.

I also learned a lot of new techniques, especially in Active Directory, which was my weak spot going in. None of it came from the course content. It came from the boxes and labs I solved, and my approach is written up in [Active Directory](/collections/oscp/active-directory).

For privilege escalation, Tib3rius's courses are really good too. My own checklists based on the course are in [Privilege Escalation (Linux)](/collections/oscp/privilege-escalation-linux) and [Privilege Escalation (Windows)](/collections/oscp/privilege-escalation-windows).

Looking back at it, I did overprepare a bit, but that beats having to do it all again.

## Is It Worth It?

For the content you get, I think OffSec is overpriced, especially next to certifications like the HTB ones. For recognition, though, OSCP is hard to beat, and that's the only reason I went for it. This will most likely be my last OffSec certificate, but who knows if that will change in the future.

Overall, it was a good experience.

<figure class="grid grid-cols-1 gap-4 sm:grid-cols-2">
  <img src="/images/oscp-certificate.png" alt="OSCP certificate" width="400" />
  <img src="/images/oscp-plus-certificate.png" alt="OSCP+ certificate" width="400" />
</figure>

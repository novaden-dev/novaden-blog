---
title: "The OWASP MAS Project"
slug: mas-project
category: notes
handbook: mobile
tags: ["mobile"]
draft: false
pubDatetime: 2026-09-19T00:00:00+03:00
description: "The OWASP Mobile Application Security (MAS) project: what MASVS, MASWE, MASTG, and the MAS Checklist each do, and the testing profiles that set the bar for an assessment."
---

## Introduction

The OWASP Mobile Application Security (MAS) project defines the industry standard for mobile application security: what a secure mobile app must do and how to test that it does. One name covers four deliverables: a requirements standard, a weakness catalog, a testing guide, and a checklist for tracking assessment coverage. The standard covers Android and iOS, is published at [mas.owasp.org](https://mas.owasp.org) with everything developed in the open on GitHub, and is referenced by platform providers such as Google Android and certification bodies such as CREST.

## The Four Deliverables

- **MASVS** (Mobile Application Security Verification Standard): the requirements. It establishes baseline security and privacy requirements for mobile apps, grouped into eight control groups such as MASVS-STORAGE and MASVS-CRYPTO. Developers use it as the requirements for a secure app, and testers use it to set the bar for an assessment.
- **MASWE** (Mobile Application Security Weakness Enumeration): the weakness catalog. It lists common security and privacy weaknesses specific to mobile apps. It works like the Common Weakness Enumeration (CWE), the community catalog of software weaknesses, but covers mobile apps only. Each entry describes a weakness, the MASVS control it breaks, and the MASTG tests that check for it.
- **MASTG** (Mobile Application Security Testing Guide): the testing manual. It covers the processes, techniques, and tools used in a mobile app security test on Android and iOS, plus the test cases that verify MASVS controls. The content is split into Tests, Techniques, Demos, Tools, and Apps.
- **MAS Checklist**: the tracking sheet. It puts every MASVS control on a single sheet and links each control to its MASTG test cases, so you record coverage in one place during an assessment. The sheet records the exact MASVS and MASTG versions it came from, so results stay traceable.

## The Testing Profiles

MASVS itself no longer carries verification levels. The old L1, L2, and R levels were reworked into the MAS Testing Profiles, which set the bar an app is tested against: L1 (baseline security), L2 (advanced security for sensitive apps), R (resilience against tampering and reverse engineering), and P (the privacy baseline).

### Where Profiles Are Used

- **Security assessments**: testers pick the profiles that match the app and assess it against them, looking for vulnerabilities, missing controls, and weak areas such as cryptography or secure communication.
- **Secure by design**: developers use the chosen profiles as requirements during design and implementation, so security requirements are handled from the start of development.
- **Compliance and risk management**: organizations map the profiles' controls and tests to the regulations and industry standards that apply to them, and use that mapping to show they meet those requirements.
- **App vetting**: organizations use the profiles as the basis for vetting apps before deploying them on company devices, tailored and extended with their own requirements.

### The Default Profiles

MAS provides four default profiles, and each assumes a different attacker:

| Profile | Name | Attacker model |
|---|---|---|
| MAS-L1 | Essential Security | Other apps installed on the device are adversaries. |
| MAS-L2 | Advanced Security | The operating system cannot be trusted, and the attacker may have physical access to the device. |
| MAS-R | Resilient Security | The device's own user is the attacker, including reverse engineers and cheaters. |
| MAS-P | Baseline Privacy | Not built around an attacker. It covers protecting users' personal data and handling it responsibly. |

MAS also publishes profiles for specific types of app or regulatory contexts. MAS-EUDIW covers the EU Digital Identity Wallet: it turns the EU regulatory requirements for the wallet into testable security requirements aligned with MAS.

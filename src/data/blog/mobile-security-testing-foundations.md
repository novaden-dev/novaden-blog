---
author: Kayra
pubDatetime: 2026-07-06T00:00:00Z
title: "Mobile Security Testing Foundations"
slug: "mobile-security-testing-foundations"
description: "The orientation for mobile app security testing: how the OWASP MAS project fits together, static versus dynamic analysis, the L1/L2/R/P profiles, the two-binary approach, and why scanner output is a lead rather than a verdict."
tags: ["mobile", "security"]
category: notes
draft: true
featured: false
---

## Introduction

Mobile application testing runs in two passes that see different things. Static analysis reads the app without running it: you decompile the package and work through the code, manifest, and resources, by hand or with tooling. Dynamic analysis watches the app while it runs, on the device and against its backend, and catches what only shows up at runtime, like a token on the wire or a check that fails open. Neither pass replaces the other. Static analysis finds the hardcoded key and the exported component; dynamic analysis proves whether the pinning actually holds.

## The OWASP MAS Project

The Mobile Application Security (MAS) project is not one document. It is four deliverables that reference each other, and most of the confusion around it comes from not knowing which one you are supposed to be reading.

- **MASVS** (Verification Standard): the requirements. Eight control groups, around twenty controls, each a single sentence of "the app must do X." This is short and high level. It is what you anchor an assessment to.
- **MASWE** (Weakness Enumeration): a catalog of concrete weaknesses, in the same spirit as CWE. It is the bridge between a vague MASVS requirement and a specific test.
- **MASTG** (Testing Guide): the long one. It holds the actual procedures, split into Tests, Techniques, Demos, Tools, and Apps. You navigate into it from a control, you do not read it front to back.
- **MAS Checklist**: a tracking sheet that maps every MASVS control to its MASTG tests, used to record coverage during an engagement.

The path to go deep on anything is the same every time. Start at the **MASVS control** (the requirement), follow it to its **MASWE weaknesses** (what can go wrong), then follow those to the **MASTG tests** (how to check). Reading MASTG on its own, front to back, does not work; you always enter it from a control.

### The eight MASVS control groups

- **MASVS-STORAGE**: sensitive data at rest, and leakage of it.
- **MASVS-CRYPTO**: strong algorithms used correctly, and key management.
- **MASVS-AUTH**: authentication and authorization, including local (biometric) auth.
- **MASVS-NETWORK**: transport security and endpoint identity (pinning).
- **MASVS-PLATFORM**: IPC, WebViews, and safe use of the user interface.
- **MASVS-CODE**: platform version, updates, dependencies, and input validation.
- **MASVS-RESILIENCE**: resistance to reverse engineering and tampering.
- **MASVS-PRIVACY**: minimizing and protecting personal data.

Some controls settle entirely from a decompiled build, some are pure runtime behavior, and some are split. Knowing which bucket a control sits in tells you whether the static pass can close it out, or whether you are only noting that a defense is present and leaving the proof for the dynamic phase.

## Static vs Dynamic Analysis

**Static analysis** ranges from a fast keyword search to reading a class line by line. A quick grep surfaces candidates: a broken cipher, a log call carrying a token, an exported activity. Reading the code in full is where business-logic flaws and design mistakes show up, the kind no scanner catches, because catching them means understanding what the code is meant to do. That reading is the work; the grep only points you at where to start.

**Dynamic analysis** examines the app while it runs. The goal is the same, find the weak spots, but you are looking at the running app and its live API traffic instead of decompiled source. It covers both the app on the device and the backend services it talks to, and it answers the questions static analysis cannot: whether a control actually holds when something tries to bypass it.

The two are complements. A control like certificate pinning shows its presence in the code (static) but only proves itself against a live intercept (dynamic). When a control can be partly settled statically, say what the static pass can and cannot conclude, and leave the rest for runtime.

## Working Through an App

The question that stalls people is whether you read the whole app line by line. You do not, and you cannot. A full mobile app is too large to read end to end on any real timeline, and most of it is UI plumbing that protects nothing. An assessment is time-boxed and coverage-driven: you work a list of controls, not a codebase. The reading you do is targeted, and three things make it targeted.

**Start with a sensitive data map.** Before any control, decide what is actually worth protecting in this app: auth tokens, the session, PII, payment data, encryption keys. Everything in STORAGE, CRYPTO, and NETWORK is then a single question repeated: where does that data go, and how is it protected on the way. This is what turns a search from a random keyword into "show me every place a token can land."

**Get breadth from grep, across every control.** Sweep the whole app for the known weakness patterns of each control: a broken cipher, a cleartext store, an exported component, a log call carrying a secret. This is fast and it is how you get coverage. It does not conclude anything; it produces a list of places to look.

**Get depth from reading, only where the sweep lands.** Read the hits and the classes that move sensitive data line by line: the storage layer, the crypto layer, the auth flow, the networking client. That is where design mistakes and misuse show up, the kind no grep catches. You are reading tens of classes, not the whole tree.

One caveat sets the ceiling on what a client-side read can find. A mobile app is the frontend of a web app: the client renders and collects, but the real gating and business logic almost always live on the server. Reading the client gives you the map (the endpoints it calls, the parameters it sends, any checks it makes locally), and it finds client-side flaws like a gate enforced only on the device. It cannot cover server-side logic, because that code is not in the binary. You test that through the API, in the dynamic phase.

So a one-day scope covering both an Android and an iOS build is not a line-by-line read of either. It is a baseline (L1) coverage pass: grep the controls, read the hits and the sensitive flows, and record coverage on the MAS Checklist. Prioritize by data sensitivity and by profile, go deeper on the L2 items that touch the crown jewels, and leave the rest as recorded coverage rather than silent gaps. Reading everything is not the goal; spending your fixed time where the sensitive data is, is.

## Where Dynamic Analysis Splits

Dynamic analysis is really two jobs against two different targets, and treating it as one ("just run the app") under-tests the half where the serious bugs usually are.

- **On the device:** you test the app's own controls as it runs. Instrument it with Frida or Objection to bypass root or jailbreak detection and SSL pinning, read what is actually in local storage and memory at runtime, confirm whether local (biometric) auth genuinely gates anything, and tamper with the running app. This front is about the client's controls and its resilience, not its logic.
- **Against the API:** once you are past pinning and can see the traffic, the app is mostly a request generator, and you test the server like any web API: broken object-level authorization (IDOR/BOLA), authentication flaws, injection, mass assignment, missing rate limits, and server-side business logic. The phone barely matters here; the weaknesses are server-side.

On most engagements the high-impact findings come from the API side, because that is where authorization and business decisions are made. The on-device work often exists to get you to the API cleanly (defeat pinning and root detection) and to confirm the client-side controls that only exist on the device, like data at rest and local auth binding.

## Android and iOS: What Changes

The MASVS controls are identical on both platforms, and so is the reasoning behind each check. What changes is the binary you open, how much of it you can read, and the exact API that counts as the protected path. Three differences matter before any control.

**The package.** An APK is a ZIP of Dalvik bytecode (`classes.dex`) plus resources. An IPA is a ZIP containing a compiled Mach-O application bundle (`.app`): native machine code, resources, and a property list. Both unzip, but what falls out is not the same kind of artifact.

**How much you can read.** This is the difference that shapes the whole iOS static pass. Android's DEX bytecode decompiles back to fairly readable Java, so jadx hands you something close to source. iOS ships compiled native code built from Swift or Objective-C, and that does not decompile to clean source. You disassemble it (Hopper, Ghidra, IDA), recover Objective-C class and method signatures with a tool like class-dump, and read embedded strings, but you are working with assembly and metadata, not reconstructed logic. Swift is harder still, because class-dump leans on Objective-C runtime metadata that Swift largely does not expose. The practical result: an iOS static pass yields less readable code than an Android one, so you lean harder on class metadata, strings, and the dynamic phase (Frida) to see behavior the static view hides.

**The security APIs.** Same purpose, different names, and most of a storage or crypto check comes down to knowing which API is the protected path and which is not. That mapping is platform-specific. The common pairs:

| Purpose | Android | iOS |
|---------|---------|-----|
| Hardware-backed key store | `AndroidKeyStore` | Keychain |
| Encrypted key-value store | `EncryptedSharedPreferences` | Keychain (with Data Protection) |
| Plain key-value store | `SharedPreferences`, DataStore | `NSUserDefaults`, plist |
| Structured local data | SQLite, Room | Core Data |
| File-level at-rest protection | `EncryptedFile` (Jetpack Security) | Data Protection classes (`NSFileProtection…`) |
| Backup exposure | `allowBackup` | iCloud and iTunes backup |
| App declaration | `AndroidManifest.xml` | `Info.plist` and entitlements |

Once you know a control on one platform, the other side is mostly this translation: the question is the same, the PASS and FAIL logic is the same, you look up the equivalent API. That is why the Android and iOS checklists mirror each other control for control.

## Testing Profiles

MASVS sorts its requirements into profiles so you test against the bar an app actually needs, not a single one-size list. How hard you test depends on what the app protects. A banking app carries obligations a mobile game does not: compliance requirements, PII handling, controls mandated by a regulator such as a central bank. The profiles fall into two groups: security profiles (L1, L2, R) for technical and adversarial threats, and a privacy profile (P) for personal-data handling.

- **MAS-L1**: the security baseline. The fundamental requirements and best practices that apply to every mobile app.
- **MAS-L2**: extends L1 for sensitive apps. It assumes the operating system's own protections cannot be trusted, for instance that the device may be rooted or jailbroken, and adds controls to match. Which of these apply is driven by the organization's own risk and compliance picture.
- **MAS-R**: resilience. It raises the cost of extracting intellectual property or bypassing client-side checks, like license enforcement or game anti-cheat. It layers on top of L1 or L2 rather than replacing them.
- **MAS-P**: the privacy baseline, focused on protecting the user's PII and other personal data.

## Working With Two Binaries

You will often be handed two builds of the same app, and it matters which one you use for what.

- **The production build** has every control in place. This is the one you report findings against. If pinning or root detection is missing here, it is a real weakness.
- **The test build** has specific controls disabled, usually SSL pinning and root detection, so you can intercept traffic and exercise the app without fighting its defenses.

Run static analysis on the production build. The test build's missing pinning is an intended change, not a vulnerability, and analyzing it produces a false "no pinning" finding that reports a deliberate modification as a real weakness. Keep the modified build for the dynamic pass, where it earns its place, and confirm every code-level finding against the build that ships to users.

## Scanner Output Is a Lead, Not a Verdict

Automated tools have no sense of context, so they over-report. Take CSRF: a real attack needs a logged-in user to open an attacker's link in a browser that then attaches the session cookie on its own. A mobile app breaks that chain. Even with a WebView and cookie-based sessions, an external link opens in the system browser, which keeps its own separate cookie store, so the forged request rides no session. A scanner flags the pattern anyway.

The lesson generalizes. Always trace a finding to an actual exploit path before you rate it, and treat tool output as something to confirm, never a conclusion. The exploit scenario is what turns a flagged pattern into a risk, and a flagged pattern with no path is noise.

> **Quick reference:** For the per-control checks (how to test each MASVS control statically from a decompiled APK and dynamically on a running device, with PASS and FAIL conditions), see [Android App Security Testing](/posts/mobile-app-security-testing).

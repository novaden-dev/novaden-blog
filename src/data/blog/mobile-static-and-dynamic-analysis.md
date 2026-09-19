---
title: "Static and Dynamic Analysis of Mobile Apps"
slug: mobile-static-and-dynamic-analysis
category: notes
handbook: mobile
tags: ["mobile"]
draft: false
pubDatetime: 2026-09-18T00:00:00+03:00
description: "Static and dynamic analysis of mobile apps: what each one covers, where manual code review finds what scanners miss, and why web findings like CSRF and reflected XSS rarely apply to a mobile app."
---

Static analysis (Static Application Security Testing, SAST) examines an app's components without running them, usually by reading the source code, either by hand or with a tool. Dynamic analysis (Dynamic Application Security Testing, DAST) examines the app while it runs, again manually or automatically.

## Static Analysis

Static analysis reviews the app's source code to check that its security controls are implemented correctly. It usually combines automated and manual work: an automated scan finds the obvious issues, and then you read the code with specific usage contexts in mind.

### Manual Code Review

Manual review ranges from a keyword search with `grep` to reading the code line by line. IDEs (Integrated Development Environments) have basic review features, and you can extend them with plugins.

A common starting point is to search for APIs and keywords that mark security-relevant code, such as database calls like `executeStatement` or `executeQuery`. Each match is a place to start reading.

Manual review finds what automated tools miss: flaws in the business logic, standards violations, and design flaws, including code that is technically secure but logically wrong.

The downside is that it is slow. The reviewer has to know both the language and the frameworks the app uses, and a full review of a large codebase with many dependencies takes a long time.

### Automated Analysis

Automated SAST tools speed up the review. They check the code against a set of rules or best practices and list every violation they find as a finding or warning. They differ in what they take as input: some run against the compiled app only, some need the original source code, and some run as plugins inside the IDE while the code is being written.

Some of these tools are tuned to mobile rules and semantics, but they still produce many false positives. Review every result by hand.

## Dynamic Analysis

Dynamic analysis looks for vulnerabilities while the app is running. It covers two layers: the mobile platform the app runs on, and the backend services and APIs it calls, where you analyze the app's requests and responses.

It is mostly used to check for common issues: data exposed in transit, authentication and authorization flaws, and server configuration errors.

## False Positives from Web Scanners

Automated tools lack the app's context, so some of what they report does not apply to it. Those results are false positives.

The common case in mobile testing is a finding that can be exploited in a web browser but says nothing about the mobile app. It gets into reports two ways: a scanner built for browser-based web apps flags patterns such as CSRF (Cross-Site Request Forgery) and XSS (Cross-Site Scripting), or a tester applies the same web app reasoning by hand. Both assume a browser session, which the app does not have.

Before you report a finding like this, work out a realistic exploit scenario and assess the risk from that. Scanner output goes into the report only after that check.

### CSRF

CSRF is the classic example. The attack needs a browser session: the victim is logged in to the target site, and the browser adds the session cookie or other token to the request on its own. An attacker's link, opened by that logged-in user, then fires the forged request.

A mobile app has no such session to abuse. Even where the app uses WebViews (browser components embedded in the app) and cookie-based sessions, a link the user taps opens in the default browser, and that browser keeps its own cookie store, separate from the app's.

### XSS

XSS is less clear-cut than CSRF, because stored and reflected XSS behave differently.

Stored XSS can be a real issue in WebViews. If the app exposes JavaScript interfaces (native methods that scripts running in the WebView can call), a stored payload can reach them and run native code.

Reflected XSS rarely matters, for the same reason as CSRF: the malicious link opens in the default browser, not in the app. Escaping output is still the right default either way.

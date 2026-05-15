---
author: Kayra
pubDatetime: 2026-05-02T00:00:00Z
title: Path/Directory Traversal
slug: path-directory-traversal
featured: false
draft: false
tags:
  - security
  - web
  - file-system
description: An overview of Path/Directory Traversal vulnerabilities, exploitation techniques, and remediation strategies.
---

## Introduction

Path traversal (also known as directory traversal) is a vulnerability that allows an attacker to read arbitrary files on a server. In some cases, it can also be leveraged to write to arbitrary files, potentially leading to remote code execution.

The attack works by manipulating file path inputs to escape the intended directory and access sensitive system files.

## How Paths Work

Before diving into the attack, it is important to understand the two types of file paths:

- **Absolute path**: The full path from the root directory. On Linux, this starts from `/` (e.g., `/var/www/app1`).
- **Relative path**: A path relative to the current working directory.

The sequence `../` (dot-dot-slash) is used to navigate up one directory level. For example:

```text
/var/www/app1/../       → /var/www/
/var/www/app1/../../    → /var/
```

Each `../` moves up one level from the current directory.

## Basic Exploitation

Consider an application running in `/var/www/` with an API endpoint like:

```text
loadprofilepic?profilepic=profile-pic1.png
```

The application likely constructs a file path by appending the user input to a base directory:

```text
/var/www/images/profile-pic1.png
```

If the application does not properly validate the input, an attacker can submit:

```text
../../../../etc/passwd
```

The resulting path becomes:

```text
/var/www/images/../../../../etc/passwd
```

After path resolution, this points to `/etc/passwd`, allowing the attacker to read the server's user database.

## Bypassing Defense Mechanisms

Applications often implement defenses against path traversal. However, these defenses are frequently incomplete and can be bypassed.

### Recursive Stripping Bypass

Some applications attempt to remove `../` from user input. If the stripping is not applied recursively, an attacker can use nested sequences:

```text
....//
```

When the application removes the inner `../`, the remaining characters form another `../`:

```text
....// → ../
```

### URL Encoding Bypass

A system might strip literal `../` sequences but fail to decode URL-encoded variants:

```text
%2e%2e%2f        → ../
%2e%2e/          → ../
..%2f            → ../
%252e%252e%252f  → ../ (double-encoded)
```

Always test multiple encoding levels, as some frameworks decode input multiple times.

### Prefix Validation Bypass

An application might validate that the path starts with an allowed directory, such as `public/`:

```text
public/images/profile.png
```

However, if the validation is not followed by proper path resolution, an attacker can append a traversal sequence after the allowed prefix:

```text
public/../../../../etc/passwd
```

The string starts with `public/`, passing the check, but resolves to `/etc/passwd` when read by the filesystem.

### Null Byte Injection

Some applications require a specific file extension, such as `.png`. On vulnerable systems (particularly older PHP versions), a null byte (`%00`) can be used to terminate the string early:

```text
/etc/passwd%00.png
```

The application sees the `.png` extension and accepts the input, but the underlying C-style string function stops at the null byte, resulting in `/etc/passwd` being read.

> **Note:** Null byte injection is largely mitigated in modern programming languages and frameworks, but it remains relevant when testing legacy systems.

## Remediation

The most effective way to prevent path traversal is to **avoid using user-supplied input in filesystem APIs altogether**. If this is not possible, implement the following layered defenses:

- **Validate input against a whitelist** of permitted filenames or patterns. If a whitelist is not feasible, restrict input to alphanumeric characters only.
- **Canonicalize the path** using platform-specific filesystem APIs (e.g., `realpath()` in Linux, `GetFullPathName()` in Windows).
- **Verify the resolved path** starts with the expected base directory. After canonicalization, ensure the file is still within the intended directory tree.
- **Avoid blacklists**. Stripping dangerous sequences is error-prone and frequently bypassed. Whitelisting and proper path resolution are far more reliable.

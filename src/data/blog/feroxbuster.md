---
title: "feroxbuster"
slug: feroxbuster
category: notes
handbook: oscp
tags: ["web", "enumeration"]
draft: false
pubDatetime: 2026-09-13T19:42:38+03:00
modDatetime: 2026-09-13T19:42:38+03:00
description: "Rust directory brute forcer whose distinguishing feature is recursion: hits on found directories are themselves enumerated by default."
---
Rust directory brute forcer whose distinguishing feature is recursion: hits on found directories are themselves enumerated by default. The plain choice when a tree of unknown depth is the target. Decisions, wordlists, and the ffuf alternative are in [Web Content Discovery](/collections/oscp/web-content-discovery).

## Install

Ships with Kali:

```bash
sudo apt install feroxbuster
```

## Command Shape

```bash
feroxbuster -u http://TARGET/ -w /usr/share/seclists/Discovery/Web-Content/raft-large-directories.txt -x php,txt
```

- `-u` takes the base URL; recursion digs below it, four levels deep by default (`-d` changes that).
- `-w` is the wordlist.
- `-x` appends extensions, the same job as ffuf's `-e` but spelled differently, and the two flags are the usual transcription mistake between the tools.
- Like ffuf, feroxbuster filters wildcard responses by default, so DNS-style catch-all hosts do not flood the output.
- `-t` raises the thread count when a target answers quickly; default 50 is usually fine.

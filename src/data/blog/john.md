---
title: "john"
slug: john
category: notes
handbook: oscp
tags: ["password-attacks"]
draft: false
pubDatetime: 2026-09-13T19:42:38+03:00
modDatetime: 2026-09-13T19:42:38+03:00
description: "Password cracker for offline cracking from Kali: CPU-based, auto-detects hash formats, and needs no GPU or OpenCL backend, which makes it the default for a single hash on the Kali VM."
---
Password cracker for offline cracking from Kali: CPU-based, auto-detects hash formats, and needs no GPU or OpenCL backend, which makes it the default for a single hash on the Kali VM. Which artifact turns into which hash is in [Password Cracking](/collections/oscp/password-cracking); online guessing is [Brute Forcing Logins](/collections/oscp/brute-forcing-logins).

## Install

```bash
sudo apt install john
```

The `*2john` helpers (`pdf2john`, `zip2john`, `office2john`, `ssh2john`, `keepass2john`) ship with it and extract a crackable hash from a protected file, as mapped in [Password Cracking](/collections/oscp/password-cracking).

## Crack a Wordlist

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt pdf.hash
john --wordlist=/usr/share/wordlists/rockyou.txt --rules=best64 pdf.hash
```

- `--wordlist` is the candidate list; rockyou is the usual one on Kali.
- `--rules=best64` applies mangling rules to every candidate (capitalization, digits, suffixes) and pays for itself once a plain rockyou pass finishes empty.
- A raw hash from a dump or `/etc/shadow` skips the `*2john` step; john reads it straight from the file and auto-detects the type.
- `--format=bcrypt` forces the type when detection is ambiguous.

Recovered passwords appear as they crack. Come back later for the full picture:

```bash
john --show pdf.hash
```

Keep the filename the `*2john` output was built from, so `--show` maps the crack back to the artifact.

## System Passwords

With both system files in hand, `unshadow` merges them so each hash carries its username, and the output names the account instead of a bare line:

```bash
unshadow passwd.txt shadow.txt > creds.txt
john --wordlist=/usr/share/wordlists/rockyou.txt creds.txt
```

Ubuntu 22.04 and later store shadow hashes as `$y$` (yescrypt), which john takes through the system's libcrypt:

```bash
john --format=crypt --fork=4 --wordlist=/usr/share/wordlists/rockyou.txt root.hash
john --show --format=crypt root.hash
```

`--format=crypt` is CPU-bound and single-threaded without `--fork`, which should be set to the core count. `john --test --format=crypt` prints the rate before committing to a run; at a few hundred hashes per second a full rockyou pass is hours rather than minutes. GPU-side cracking of formats that support it is [hashcat](/collections/oscp/hashcat).

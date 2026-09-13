---
title: "kerbrute"
slug: kerbrute
category: notes
handbook: oscp
tags: ["kerberos"]
draft: false
pubDatetime: 2026-08-01T10:35:17+03:00
modDatetime: 2026-09-08T22:27:09+03:00
description: "Kerbrute abuses Kerberos pre-authentication to test usernames and passwords against a DC quickly."
---
Kerbrute abuses Kerberos pre-authentication to test usernames and passwords against a DC quickly. It needs only the KDC (port 88), which is always open on a Domain Controller, and works through AS-REQ messages rather than SMB or LDAP logons. A single Go binary, no install beyond downloading it.

## Install

Not installed on Kali by default, hence `command not found`. Grab the precompiled release binary, which has no dependencies:

```bash
wget https://github.com/ropnop/kerbrute/releases/latest/download/kerbrute_linux_amd64 -O kerbrute
chmod +x kerbrute
sudo mv kerbrute /usr/local/bin/kerbrute      # now on PATH as `kerbrute`
kerbrute -h
```

With Go already installed, `go install github.com/ropnop/kerbrute@latest` builds it into `~/go/bin` instead.

Kerbrute is cross-platform: the same releases page has `kerbrute_windows_amd64.exe` and a macOS build, so it can run from a Windows foothold too, though it is normally run from Kali against the DC.

## What it does

For each name it sends an AS-REQ and reads the reply:

- unknown user -> `KDC_ERR_C_PRINCIPAL_UNKNOWN`
- valid user  -> pre-auth-required error, or an AS-REP if pre-auth is disabled

That difference is what the three modes are built on.

## Modes

```bash
# confirm which usernames exist, from a wordlist, no passwords sent
kerbrute userenum -d corp.com --dc <DC_IP> /usr/share/seclists/Usernames/Names/names.txt

# one password against many users (spray); respect the lockout policy
kerbrute passwordspray -d corp.com --dc <DC_IP> users.txt 'Season2024!'

# many passwords against one user
kerbrute bruteuser -d corp.com --dc <DC_IP> passwords.txt jeff
```

## Wordlists

Username enumeration is only as good as the list. AD accounts are usually person names, so start with a names list and widen if it comes up empty:

- `/usr/share/seclists/Usernames/Names/names.txt` (person names, primary)
- `/usr/share/seclists/Usernames/xato-net-10-million-usernames.txt` (large generic, fallback)

Both come from `seclists` (`sudo apt install seclists`). If the accounts follow a `firstname.lastname` or `flast` convention, the list has to match that format, a plain names list will not hit them. A spray or `bruteuser` takes a password list instead, such as `/usr/share/wordlists/rockyou.txt`.

## Lockout

User enumeration is safe: a request for a nonexistent or valid user is not a failed logon, so it never touches the bad-password count. Password spraying and brute forcing send real guesses and do count toward lockout, so keep spraying to one or two attempts per user per policy window.

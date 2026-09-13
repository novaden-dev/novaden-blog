---
title: "SMB Enumeration"
slug: smb-enumeration
category: notes
handbook: oscp
tags: ["smb", "enumeration"]
draft: false
pubDatetime: 2026-07-21T21:42:14+03:00
modDatetime: 2026-09-08T22:27:09+03:00
description: "SMB on 139/445 exposes file shares and host information, often without credentials."
---
SMB on 139/445 exposes file shares and host information, often without credentials. The checks are: list shares over a null session, read anything world-accessible, and version the service for a known exploit. On a box where the web service is dry, this is the next place to look.

## List Shares

Try a null session first (empty user, empty password):

```bash
smbclient -L //TARGET/ -N            # list shares
nxc smb TARGET -u '' -p '' --shares  # netexec, also flags read/write access
```

`nxc` (netexec, the crackmapexec successor) annotates each share with READ/WRITE, which is the fastest way to spot a writable or readable one.

Confirm a negative with a second tool. On Bratarina smbmap reported

```text
[*] Established 1 SMB connections(s) and 0 authenticated session(s)
[!] Access denied on 192.168.186.71, no fun for you...
```

on a host where `smbclient -L //TARGET/ -N` listed the shares and a readable `backups` share was then downloaded anonymously. One tool saying access denied is not evidence that anonymous access is closed.

`do_connect: Connection to TARGET failed (Error NT_STATUS_IO_TIMEOUT)` alongside `Reconnecting with SMB1 for workgroup listing` is the SMB1 workgroup query timing out on a modern Samba. It appears after the share listing has already succeeded and can be ignored.

## Full Enumeration

```bash
enum4linux-ng TARGET                 # users, groups, shares, OS, domain
nmap --script "smb-os-discovery,smb-enum-shares,smb-enum-users,smb-vuln*" -p139,445 TARGET
```

`smb-os-discovery` gives the OS and, on Windows, the build, which decides whether host exploits apply. `smb-vuln*` runs the known SMB vulnerability scripts.

## Connect and Download

Open the share interactively:

```bash
smbclient //TARGET/share -N          # -N null session; -U user for authenticated
```

Inside the client, navigation is ftp-style: `ls`, `cd dir`, `get file`. Downloads land in the local directory the client was started from, so `lcd /tmp/share` first to keep loot in one place. Quote names with spaces: `get "my notes.txt"`. `allinfo file` shows size, timestamps, and alternate data streams, which is the classic spot for data hidden inside an innocent-looking file.

For a whole tree, disable the per-file confirmation and recurse before a bulk pull:

```text
smb: \> prompt off
smb: \> recurse on
smb: \> mget *
```

Without the interactive prompt, `-c` runs client commands and exits, and `smbget` pulls a share recursively on its own:

```bash
smbclient //TARGET/share -N -c 'ls'
smbclient //TARGET/share -N -c 'cd backups; get passwords.txt'
smbget -R smb://TARGET/share/        # -R recursive, whole share in one go
```

smbmap and nxc also pull files directly, no client session:

```bash
smbmap -H TARGET -R share                        # recursive listing of one share
smbmap -H TARGET --download 'share\file.txt'     # single file by share path
nxc smb TARGET -u '' -p '' --get-file 'share\file.txt' /tmp/file.txt
nxc smb TARGET -u '' -p '' -M spider_plus -o DOWNLOAD_FLAG=True   # dump every readable share
```

spider_plus writes the file listing to ~/.nxc/modules/spider_plus/ and `DOWNLOAD_FLAG=True` copies every file into that tree, so on a large share it replaces the interactive crawl with one command. See [NetExec](/collections/oscp/netexec).

## Version-Bound Exploits

Match the exploit to the platform:

- **Windows**: **EternalBlue (MS17-010)** on unpatched Windows 7 / 2008. Confirm with the `smb-vuln-ms17-010` nmap script first. A vulnerable flag does not guarantee a working shell: some public PoCs (3hydraking `send_and_execute.py`) stop at `Not found accessible named pipe` when a null session cannot open a pipe, which needs valid credentials or a PoC that locates a usable pipe. That happened on Internal.
- **Windows (Vista / Server 2008)**: **MS09-050 (CVE-2009-3103)**, an SMBv2 negotiate bug, is the fallback when EternalBlue is blocked. EDB 40280 exploits it and runs as SYSTEM, but the standalone script needs repair and its shell is unstable. See Internal and [Fixing Public Exploits](/collections/oscp/fixing-public-exploits).
- **Samba (Linux)**: **usermap_script (CVE-2007-2447)** on Samba 3.0.20 to 3.0.25, and **SambaCry (CVE-2017-7494)** on 3.5.0 to 4.6.x when a writable share exists. Get the version from `smb-os-discovery` or `enum4linux-ng`.

A modern Samba (as on Snookums, CentOS 7) is not vulnerable to these, so SMB there was enumeration only, not the path.

## What to Look For

- Readable shares holding configs, credentials, keys, or source.
- A writable share, which enables SambaCry or a payload drop.
- Usernames for password spraying or brute force, cross-referenced with [Credential Hunting](/collections/oscp/credential-hunting).
- A share that turns out to alias a directory a web app already writes into. On Apex a read-only `docs` share held the same files as a Responsive FileManager upload folder; the app's own HTTP read-back 404'd for one particular file while `smbclient get` pulled it straight off the same directory. Worth checking any anonymous share against a web app's known upload paths before assuming the two are unrelated.

## Where This Sits

SMB is a line in the attack-surface table from [Information Gathering](/collections/oscp/information-gathering). A version match goes to [Service Exploits](/collections/oscp/service-exploits); credentials and files found go to [Credential Hunting](/collections/oscp/credential-hunting).

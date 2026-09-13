---
title: "accesschk"
slug: accesschk
category: notes
handbook: oscp
tags: ["privilege-escalation", "windows"]
draft: false
pubDatetime: 2026-07-22T08:58:39+03:00
modDatetime: 2026-09-13T19:42:38+03:00
description: "accesschk (Sysinternals) reports the effective access a user or group has to services, files, directories, and registry keys."
---
accesschk (Sysinternals) reports the effective access a user or group has to services, files, directories, and registry keys. It is the confirmation step for every service and autorun vector: winPEAS flags a possible misconfiguration, accesschk proves the current user can actually write to or control the object. Used throughout [Windows Service Exploits](/collections/oscp/windows-service-exploits) and [Windows Autoruns and Scheduled Tasks](/collections/oscp/windows-autoruns-and-scheduled-tasks).

## Install

Part of the Sysinternals suite:

```bash
curl -L https://download.sysinternals.com/files/AccessChk.zip -o AccessChk.zip
```

`accesschk.exe` and `accesschk64.exe` are the 32- and 64-bit builds. Transfer to the target the same way as [winPEAS](/collections/oscp/winpeas) (HTTP with `certutil`, or an SMB share).

## The EULA Flag

Current versions accept `-accepteula` on the command line and run headless. Very old builds pop a GUI EULA prompt, and the OSCP-era build used `/accepteula`; both forms are accepted, so keep `-accepteula` on every invocation to avoid the popup:

```cmd
accesschk.exe -accepteula ...
```

## Common Checks

Flags used across the privesc vectors:

- `-u` suppress errors
- `-w` show only writable objects
- `-v` verbose (list specific rights)
- `-q` omit the banner
- `-c` name a Windows service (`*` for all)
- `-d` process directories, not their contents
- `-k` registry key
- `-s` recurse

```cmd
:: service: does <user> have change/start/stop rights
accesschk.exe -accepteula -uwcqv <user> <service>
accesschk.exe -accepteula -uvqc <user> <service>

:: writable directory (unquoted path, startup folder)
accesschk.exe -accepteula -uwdq "C:\Program Files\Some Dir\"
accesschk.exe -accepteula -d "C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp"

:: writable file (insecure service executable, AutoRun target)
accesschk.exe -accepteula -quvw "C:\Program Files\Some Service\service.exe"

:: registry key (weak service permissions)
accesschk.exe -accepteula -uvwqk HKLM\System\CurrentControlSet\Services\<service>
```

A finding here is what turns a winPEAS highlight into an actionable vector. If the current user is not shown with a write or control right, the vector is a dead end.

For file and folder ACLs only, the built-in [icacls](/collections/oscp/icacls) is enough and needs no upload. accesschk earns its keep on services and registry keys, which icacls cannot see.

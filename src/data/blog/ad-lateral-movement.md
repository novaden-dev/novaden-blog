---
title: "AD Lateral Movement"
slug: ad-lateral-movement
category: notes
handbook: oscp
tags: ["active-directory", "lateral-movement"]
draft: false
pubDatetime: 2026-08-01T10:35:17+03:00
modDatetime: 2026-09-13T20:51:50+03:00
description: "Lateral movement reuses a credential (password or NT hash) to run code on another host, no cracking needed."
---
Lateral movement reuses a credential (password or NT hash) to run code on another host, no cracking needed. A hash pulled from one place (SAM, LSASS, [DCSync](/collections/oscp/dcsync)) authenticates as that account anywhere the account is valid, but a shell needs more than authentication: the remote-execution tools below require the account to be a local admin on the target. Reaching a host where a more privileged user is logged in, then stealing that session, is how a foothold climbs toward Domain Admin ([Active Directory](/collections/oscp/active-directory)).

## Find where a credential is admin

Sweep the credential across the hosts to see where it can execute; `Pwn3d!` marks local admin. Command forms (pass-the-hash and password): [NetExec](/collections/oscp/netexec#spraying-and-credential-reuse).

## Get a shell

Probe both SMB and WinRM: a host can hand a shell over WinRM (account in **Remote Management Users**) with no local admin, so SMB `Pwn3d!` is not the only lead. Marker meanings are in [NetExec](/collections/oscp/netexec#shape); the WinRM-vs-admin nuance in [Windows Remote Access](/collections/oscp/windows-remote-access#winrm).

```bash
nxc smb TARGET -u user -p 'pass'          # Pwn3d! = local admin
nxc winrm TARGET -u user -p 'pass'        # [+] = evil-winrm will open
```

A WinRM shell without SMB `Pwn3d!` is a low-priv foothold: file hunt and local enum work, but `lsassy` / `--sam` / `--lsa` still need admin. Password forms below first; swap in the hash form when only a hash is known.

```bash
# evil-winrm: interactive PowerShell over WinRM (needs 5985 open), prefer when it works
evil-winrm -i TARGET -u user -p 'pass'
evil-winrm -i TARGET -u user -H <NThash>

# wmiexec: WMI, no service dropped, quieter, lands as the user
impacket-wmiexec 'DOMAIN/user:pass@TARGET'
impacket-wmiexec -hashes :<NThash> 'DOMAIN/user@TARGET'

# psexec: drops a service over SMB, lands as SYSTEM (loud)
impacket-psexec 'DOMAIN/user:pass@TARGET'
impacket-psexec -hashes :<NThash> 'DOMAIN/user@TARGET'

# single command, no interactive shell
nxc smb TARGET -u user -p 'pass' -x 'whoami'
nxc smb TARGET -u user -H <NThash> -x 'whoami'
```

`impacket-smbexec` is another semi-interactive SMB option when the others fail.

## After local admin

Local admin unlocks credential theft; the next domain move almost always comes from secrets on that box, not from more low-priv enum. On every newly owned host, before looking for a clever ACL path:

1. **Dump what the host already knows.** `-M lsassy` (live LSASS), `--lsa` (LSA secrets, cached logons), `--sam` (local hashes): [NetExec](/collections/oscp/netexec#dump-credentials-remotely); `--sessions --loggedon-users` to see who else is on. Reading the lsassy lines: [NetExec](/collections/oscp/netexec#reading-lsassy-output). File and registry hunt on the shell: [Windows Credential Hunting](/collections/oscp/windows-credential-hunting).
2. **Spray every new secret** across the estate ([NetExec](/collections/oscp/netexec#spraying-and-credential-reuse)); each fresh `Pwn3d!` is another host to dump.
3. **Re-enumerate AD as the new identity** (BloodHound, Kerberoast, group membership, ACLs), following the re-enumeration habit in [Active Directory](/collections/oscp/active-directory).
4. Only then chase graph edges (ACL abuse, delegation) if the dump/spray loop stalls.

Stop when Domain Admin or a [DCSync](/collections/oscp/dcsync)-capable principal is reached.

## Execute from a Windows foothold

The tools above run from Kali. Already on a domain-joined host, the same lateral move uses built-in Windows tooling, which is quieter and avoids transferring impacket. Each still needs local admin on the target.

```cmd
:: winrs: remote command over WinRM (5985), runs as the calling user
winrs -r:web01 -u:corp\jeffadmin -p:password "whoami"

:: wmic: create a process over WMI (135 + dynamic RPC), no service dropped; WMI returns no stdout, so write to a file
wmic /node:web01 /user:corp\jeffadmin /password:password process call create "cmd /c whoami > C:\out.txt"
```

```powershell
# PowerShell equivalents from the foothold
Invoke-WmiMethod -ComputerName web01 -Class Win32_Process -Name Create -ArgumentList "cmd /c whoami > C:\out.txt"
Invoke-Command -ComputerName web01 -ScriptBlock { whoami }   # PSRemoting over WinRM, subject to the double hop below
```

`PsExec.exe` (Sysinternals, transferred to the host) is the classic service-based option and lands as SYSTEM:

```cmd
PsExec.exe \\web01 -u corp\jeffadmin -p password cmd
```

DCOM (`MMC20.Application` and similar objects, driven over RPC) is a stealthier execution primitive, rarely needed on the exam but a fallback when WMI and WinRM are filtered.

## Pass-the-hash and its limits

The NT hash is enough on its own, no plaintext, no cracking. Ticket-based variants (overpass-the-hash, pass-the-ticket) handle the Kerberos-only targets that plain pass-the-hash cannot and are covered below; hash-over-NTLM is the simplest path and the one to try first.

Execution needs local admin, not just a valid hash. psexec writes to the `ADMIN$` share and registers a service, wmiexec and smbexec drive the SCM and WMI, and evil-winrm needs membership in Remote Management Users: all administrative operations. A hash for a non-admin account still authenticates (it can read a share it has rights to, bind LDAP, or be sprayed), but it returns no shell through these tools, so the sweep looks for `Pwn3d!`, not just `[+]`.

A hash belongs to one specific account. Sweeping `-u Administrator` makes each host authenticate as *its own* domain's Administrator, so a hash pulled from one domain only matches on that domain's hosts; hosts in another domain return `STATUS_LOGON_FAILURE`. Moving into another domain needs that domain's credential (for example [DCSync](/collections/oscp/dcsync) its DC), or explicitly authenticating as the original account if it holds cross-domain rights.

## Overpass-the-hash and pass-the-ticket

When a target only accepts Kerberos (reached by hostname, or NTLM disabled), plain pass-the-hash fails and the hash has to become a ticket first. The route decides how fiddly it is, and on a foothold it is neither exotic nor fragile:

- **On a Windows foothold** (no setup): [Rubeus](/collections/oscp/rubeus) or [Mimikatz](/collections/oscp/mimikatz) mint and inject the ticket in memory. This is the reliable path, needing no `krb5.conf` and no route from Kali to the DC.

  ```
  Rubeus.exe asktgt /user:jeffadmin /rc4:<NThash> /ptt   # overpass-the-hash: NT hash -> TGT, injected
  Rubeus.exe ptt /ticket:ticket.kirbi                    # pass-the-ticket: reuse a stolen ticket
  ```

  Mimikatz does the same with `sekurlsa::pth` and `kerberos::ptt` ([Mimikatz](/collections/oscp/mimikatz)); a ticket to reuse comes from `sekurlsa::tickets /export`.

- **From Kali** (impacket `-k`): `getTGT`/`getST` write a `.ccache` used via `KRB5CCNAME` and `-k -no-pass`. This needs a working `/etc/krb5.conf` mapping the realm to its KDC and the target addressed by the FQDN in the ticket; mismatches surface as `KRB_AP_ERR_MODIFIED` or `STATUS_MORE_PROCESSING_REQUIRED`. It is the same plumbing that made the [Kerberos Delegation](/collections/oscp/kerberos-delegation) ticket path finicky, so the on-host route is preferred whenever a foothold exists.

Overpass-the-hash is the standard answer once a hash is in hand and the target turns out to only accept Kerberos, for instance when it is addressed by hostname or NTLM is disabled.

## The Kerberos double-hop problem

Landing on a host over WinRM (`evil-winrm`) or PSRemoting gives a working shell, but the credential does not travel to a second hop. From inside that shell, reaching a further host or a network share (`\\dc\c$`, another WinRM, a SQL server) fails with access denied, even though the same account works against that resource directly. The session holds only a service ticket for the host already logged into, not the user's password, so it cannot request fresh tickets for other services on the user's behalf; NTLM has the same limit, the first hop has no reusable secret to authenticate onward.

This is a frequent exam trap: a command that works from Kali fails when run from within a WinRM shell, and it reads like a permissions bug rather than a protocol limit.

Avoiding it:

- Do not pivot from inside the WinRM shell. Run each tool from Kali (or the foothold) with the credential supplied fresh (`-hashes`, password), so every hop authenticates on its own. psexec, wmiexec, and `nxc -x` re-send the credential on each call and never hit the double hop.
- If a shell on the far host is the goal, target it directly with its own credential rather than chaining through the first shell.
- Ticket-forwarding workarounds (CredSSP, an explicit `PSCredential` inside the script, a fresh `runas /netonly`) exist but are fiddly; supplying the credential per tool is the reliable exam habit.

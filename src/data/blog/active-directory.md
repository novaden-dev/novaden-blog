---
title: "Active Directory"
slug: active-directory
category: notes
handbook: oscp
format: methodology
tags: ["active-directory"]
draft: false
pubDatetime: 2026-08-01T10:35:17+03:00
modDatetime: 2026-09-13T17:59:14+03:00
description: "Active Directory (AD) is both a directory of an organisation's users, groups, and computers, and the management layer that controls them."
---
Active Directory (AD) is both a directory of an organisation's users, groups, and computers, and the management layer that controls them. Everything is an object with attributes and a set of permissions. One or more Domain Controllers (DC) hold the whole database and answer authentication; a DC also runs the domain's authoritative DNS, so the DC is usually the DNS server too. A domain such as `corp.com` can grow into a tree, and multiple trees form a forest.

Two groups matter most as targets:

- **Domain Admins**: full control of one domain.
- **Enterprise Admins**: full control of every domain in the forest, administrator on every DC.

Compromising a member of either is game over for that scope, so most AD work is a search for a path from a low-privileged foothold to one of these.

The terms the notes below assume (SPN, ACL, nested groups, Kerberos, tickets, pass-the-hash, DCSync) are defined in [Active Directory Concepts](/collections/oscp/active-directory-concepts), the primer for someone new to AD.

## The OSCP scenario

The labs and exam use an assumed breach: the starting point is valid credentials for one low-privileged domain user (for example `stephanie`), usually with WinRM access to a domain-joined workstation but no local admin. The objective is to enumerate the whole domain and reach Domain Admin.

The defining habit is to re-enumerate from every new identity. Each user and each host sits in a different position in the permission graph, so a second low-privileged account is not a duplicate of the first: it may be a local admin somewhere, hold a dangerous ACL, or share a machine with a privileged user whose credentials are cached there. Rinse and repeat after every credential gained.

## Workflow

Each phase feeds the next. Loop back to enumeration whenever a new account or host is obtained.

1. **Enumerate** ([Active Directory Enumeration](/collections/oscp/active-directory-enumeration)). Map users, groups (including nested ones), computers and their OS, sessions, SPNs, object ACLs, and shares. Build a picture of who can reach and control what. [BloodHound](/collections/oscp/bloodhound) gathers the same data itself and turns it into attack-path graphs.
2. **Get more credentials.** Several attacks on the authentication protocols yield hashes or plaintext to crack. AS-REP roasting and Kerberoasting come first: they need no special privilege, risk no account lockout, and run from any authenticated foothold, so they are a free attempt at the next credential before any graph analysis.
   - [AS-REP Roasting](/collections/oscp/as-rep-roasting): crackable hash for any account with Kerberos pre-auth disabled, no credentials needed to request it.
   - [Kerberoasting](/collections/oscp/kerberoasting): crackable hash for any account with an SPN, requestable by any authenticated user.
   - Password spraying against the domain, more cautious since it risks lockout (low and slow) with [Password Spraying](/collections/oscp/password-spraying).
   - Credentials cached on compromised hosts, dumped from LSASS with [Mimikatz](/collections/oscp/mimikatz) / `nxc -M lsassy`, plus the file and registry stashes in [Windows Credential Hunting](/collections/oscp/windows-credential-hunting).
   - LLMNR/NBT-NS poisoning and NTLM relay from a position on the internal segment, capturing or forwarding authentication ([LLMNR Poisoning and NTLM Relay](/collections/oscp/llmnr-poisoning-and-ntlm-relay)). Not applicable on the exam: it needs a shared broadcast segment the routed exam network does not provide, and spoofing is restricted by the exam rules, so it is lab and real-engagement material rather than an exam step.
3. **Move laterally** ([AD Lateral Movement](/collections/oscp/ad-lateral-movement)). Reuse a hash or ticket to get code execution on another host: pass-the-hash, overpass-the-hash, pass-the-ticket, and remote execution over WMI, WinRM, PsExec, or DCOM. Once local admin lands, dump that host (LSASS / LSA / SAM / files) before chasing ACL paths; the next domain credential usually comes from secrets on the box. Full post-admin loop in [AD Lateral Movement After local admin](/collections/oscp/ad-lateral-movement#after-local-admin).
4. **Escalate to Domain Admin.** Take over a privileged user, group, or computer through a dangerous ACL that BloodHound flags ([ACL Abuse](/collections/oscp/acl-abuse)); abuse a delegation misconfiguration to impersonate a Domain Admin to a service, especially on a DC ([Kerberos Delegation](/collections/oscp/kerberos-delegation)); forge tickets when the right hash is in hand ([Silver and Golden Tickets](/collections/oscp/silver-and-golden-tickets)); or impersonate a DC to pull any account's hash with [DCSync](/collections/oscp/dcsync) once a suitably privileged account is compromised.
5. **Persist** ([AD Persistence](/collections/oscp/ad-persistence)). Golden tickets from the `krbtgt` hash, and offline extraction of the whole domain database via shadow copies of `ntds.dit`.

## How this connects to the rest of the vault

- Local privilege escalation is still a separate problem on each host. A foothold that lands as a low-privileged local user needs [Privilege Escalation (Windows)](/collections/oscp/privilege-escalation-windows) to reach the point where LSASS and the SAM can be read; only then do the AD credential-theft steps apply.
- Reaching hosts on an internal subnet the Kali box has no route to is a pivoting problem, see [Tunneling and Pivoting](/collections/oscp/tunneling-and-pivoting). Many AD tools (`nxc`, `impacket`, `bloodhound-ce-python`) run from Kali against the DC once a route exists.
- Every hash pulled from AD goes to [Password Cracking](/collections/oscp/password-cracking) (NT hash is hashcat mode 1000); every plaintext gets retried everywhere, since reuse is the whole premise.

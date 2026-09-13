---
title: "Active Directory Concepts"
slug: active-directory-concepts
category: notes
handbook: oscp
tags: ["active-directory"]
draft: false
pubDatetime: 2026-08-01T10:35:17+03:00
modDatetime: 2026-09-13T20:51:50+03:00
description: "The terms the Active Directory workflow and its attack notes assume."
---
The terms the [Active Directory](/collections/oscp/active-directory) workflow and its attack notes assume. Read once for grounding; each section links to where the concept is actually exploited.

A domain (for example `corp.com`) is a directory of objects: users, groups, and computers, each with attributes and a set of permissions. The Domain Controller (DC) holds the whole database and answers logins.

## Local admin vs domain admin

These are different scopes of power, and confusing them wastes time.

- **Local administrator**: admin on **one** machine. The account and its rights live in that machine's local SAM database. Power stops at that box: it can read everything on that host (including credentials cached in memory), but says nothing about any other machine.
- **Domain administrator**: member of the **Domain Admins** group. Admin across the **whole domain**, including every DC. This is the objective.

A normal domain user can also be a local admin on some specific machines (that is exactly what `Find-LocalAdminAccess` looks for). Getting local admin on a host is usually a stepping stone, not the goal: it lets an attacker dump the credentials cached on that host, which may belong to a more privileged user, and those credentials open the next door. See [AD Lateral Movement](/collections/oscp/ad-lateral-movement).

Above Domain Admins sits **Enterprise Admins**: admin over every domain in the forest.

## Groups and nested groups

A group is a bag of members treated as one unit. A permission granted to a group applies to every member, so admins assign access to groups instead of to individuals.

A **nested group** is a group that is itself a member of another group. Membership flows inward to outward: members of the inner group inherit the outer group's access.

```text
jen  ->  Management Dept  ->  Development Dept  ->  Sales Dept
```

Here `jen` is only directly in Management, but through the chain she also has whatever Sales can access. This matters because `net.exe` lists only the direct **user** members of a group and hides the nested groups, so a user can hold access that is not obvious. PowerView and [BloodHound](/collections/oscp/bloodhound) follow the chain; see the nested-group unravelling in [Active Directory Enumeration](/collections/oscp/active-directory-enumeration).

## Shares

A share is a folder (or resource) on a host exposed over SMB (port 445) so other machines on the network can reach it. Some are default: `C$`, `ADMIN$`, and `IPC$` are hidden admin shares on every host; `SYSVOL` and `NETLOGON` live on the DC and every domain user can read them.

Shares matter for two reasons. First, files left on them leak credentials (configs, scripts, old Group Policy backups with a GPP `cpassword`). Second, several lateral-movement techniques rely on a share existing: PsExec and pass-the-hash write to `ADMIN$`. Enumeration and reading of shares is in [Active Directory Enumeration](/collections/oscp/active-directory-enumeration).

## SPN (Service Principal Name)

A service such as IIS, MSSQL, or Exchange runs under some account (a **service account**). An SPN is a label that maps "this service, on this host, on this port" to the account that runs it, so Kerberos knows whose key to use when issuing a ticket for that service.

The account behind an SPN is usually an ordinary domain user account, so it can log in like any user (RDP, WinRM, running as its service), limited only by its assigned rights. Whether RDP specifically works depends on its group membership; some admins deny interactive logon to service accounts and many do not.

Nothing about an SPN grants privilege by itself. Service accounts end up powerful in **practice**, not by design: the service needs to reach databases, file shares, and system locations, so admins over-grant it, commonly local admin on the servers it runs on and sometimes Domain Admins outright. Paired with weak, human-chosen, non-expiring passwords, that over-granting is why [Kerberoasting](/collections/oscp/kerberoasting) pays off. It targets SPNs on **user** accounts; SPNs on machine accounts have random 120-character passwords and are not worth cracking.

## ACLs and ACEs

Every object carries an **ACL** (Access Control List): a list of who can do what to it. Each entry is an **ACE** (Access Control Entry): one principal (identified by a SID) plus one right, such as `GenericAll` or `WriteDACL`.

A **SID** (Security Identifier) is how Windows identifies a principal internally, for example `S-1-5-21-1987370270-658905905-1781884369-1104`. Its structure explains where several attacks get their inputs:

- `S-1-5-21` is a fixed prefix meaning a domain-issued SID.
- The three long numbers are the **domain identifier**, generated randomly when the domain is created and shared by every object in that domain. This is the "domain SID" a golden ticket needs.
- The last number is the **RID** (Relative Identifier), handed out in sequence as objects are created. Some RIDs are fixed and worth knowing: `500` is the built-in Administrator, `502` is krbtgt, `512` is Domain Admins.

Names are cosmetic; access checks use the SID, so renaming an account does not transfer its access, and `Convert-SidToName` is needed to read one back.

The SID value is **not** secret or cryptographically signed, so "make one up" is a fair question. Making one up does not help for normal logins because the account authenticates to the DC, and the DC issues the ticket stamped with the real SIDs that account actually holds. What can be forged is the encrypted ticket that carries the SIDs, but only with the key that encrypts it. Stealing the krbtgt key and inserting RID `512` into a forged TGT is precisely the golden ticket attack, and it is why that attack needs the genuine domain identifier: the DC only trusts SIDs under a domain it recognises.

ACLs matter because a misconfigured ACE lets a low-privileged account take over a privileged object (reset its password, add itself to a group, rewrite its ACL). The abusable rights are tabled in [Active Directory Enumeration](/collections/oscp/active-directory-enumeration), and [BloodHound](/collections/oscp/bloodhound) draws these as edges between objects.

## Kerberos

Kerberos is the default authentication protocol in AD. Instead of sending the password to every service, a user proves identity once and then presents **tickets**. The **KDC** (Key Distribution Center) runs on the DC and issues them. Two ticket types:

- **TGT** (Ticket Granting Ticket): proof of identity, issued at logon. Encrypted with the **krbtgt** account's key, so only a DC can read or make a valid one.
- **TGS** (service ticket): permission to use **one specific service**, requested by presenting the TGT. Encrypted with **that service account's** key.

These keys are **symmetric**, not a public/private pair. Each account (a user, a service account, krbtgt) has one secret key derived from its password, and the DC holds every account's key because it stores the password hashes. "Encrypted with the service account's key" means encrypted with that single shared secret: the DC can build the ticket, the service can read it, and a stolen service account hash is enough to forge tickets for it.

The flow runs in three exchanges. Logon happens once; the service exchange repeats for every resource the user touches. The encrypted timestamp in step 1 is the pre-authentication proof, explained below.

```text
1. LOGON (once, at sign-in)
     Client -> KDC      AS-REQ: timestamp encrypted with user's hash
     KDC -> Client      AS-REP: TGT + session key
                        (TGT is encrypted with the krbtgt key)

2. GET A SERVICE TICKET (once per service: share, DB, web app)
     Client -> KDC      TGS-REQ: TGT + SPN + authenticator
     KDC -> Client      TGS-REP: TGS for that service
                        (encrypted with the service account's key)

3. USE THE SERVICE
     Client -> Service  AP-REQ: TGS + authenticator
                        (service decrypts it, reads identity + SIDs)
```

The names decode simply: **AS** is the Authentication Server, **TGS** the Ticket Granting Service, **AP** the Application (the service itself), and **REQ**/**REP** are request and reply. So AS-REP is the logon reply carrying the TGT, TGS-REQ/TGS-REP are the service-ticket request and reply, and AP-REQ is the client presenting its service ticket to the service.

The **session key** returned in the AS-REP is a temporary shared secret between the client and the KDC, and it is **never sent in the clear**. The client cannot read the TGT (it is under krbtgt's key), so on each later TGS-REQ it proves it genuinely holds that TGT by sending an **authenticator**: a fresh timestamp encrypted with the session key. The KDC decrypts the TGT, reads the copy of the session key stored inside it, and uses that to validate the authenticator. The same pattern repeats at the service in step 3, where the AP-REQ carries an authenticator encrypted with the service session key handed out in the TGS-REP. Identity carries forward without the key or the password ever appearing in the clear.

**Pre-authentication** is the encrypted timestamp in step 1: proof the requester knows the password, sent before the DC replies. Its state is what makes AS-REP roasting possible or not.

- **Enabled (default):** the DC decrypts the timestamp with the user's stored key and only sends the AS-REP if it matches. A stranger who does not know the password never gets a reply, so there is nothing to attack offline.
- **Disabled:** the DC skips that check and hands the AS-REP to anyone who asks for that user. This does **not** grant a login. Part of the AS-REP is still encrypted with the user's password-derived key, so the attacker receives an encrypted blob, not access. Cracking that blob offline recovers the password. That is [AS-REP Roasting](/collections/oscp/as-rep-roasting): no credentials needed to request it, but the password still has to be cracked before it is usable.

Admins disable it for compatibility: some legacy apps, appliances, and non-Windows Kerberos clients cannot do pre-authentication, so the account option "Do not require Kerberos preauthentication" gets switched on to make them work. That is why the flaw turns up on real accounts.

Two facts from this flow drive every Kerberos attack. Each ticket is encrypted with a specific account's key (TGT with krbtgt's, TGS with the service account's), and the service trusts whatever identity and SIDs are inside a ticket it can decrypt. So whoever holds a key can forge the matching ticket, and whoever steals an issued ticket can replay it. Each attack hits one piece:

| Attack          | What it does                                                                   | Note                          |
| --------------- | ------------------------------------------------------------------------------ | ----------------------------- |
| AS-REP roasting | Pre-auth disabled, so anyone can request the logon reply and crack it offline  | [AS-REP Roasting](/collections/oscp/as-rep-roasting)           |
| Kerberoasting   | Request a TGS for any SPN, crack it offline for the service account's password | [Kerberoasting](/collections/oscp/kerberoasting)             |
| Silver ticket   | Forge a TGS using a service account's hash (access to that one service)        | [Silver and Golden Tickets](/collections/oscp/silver-and-golden-tickets) |
| Golden ticket   | Forge a TGT using the krbtgt hash (access to the whole domain)                 | [Silver and Golden Tickets](/collections/oscp/silver-and-golden-tickets) |
| Pass the ticket | Steal an existing ticket from memory and reuse it                              | [AD Lateral Movement](/collections/oscp/ad-lateral-movement)       |

## NTLM

NTLM is the older protocol AD falls back to when Kerberos cannot be used: a client connecting to a resource by IP address instead of hostname, a name not registered in AD DNS, or an application that does not speak Kerberos. Both protocols coexist in most domains.

It is a challenge-response exchange. The detail that matters is what does the proving:

```text
Client -> Server   username
Server -> Client   a random challenge (the nonce)
Client -> Server   the challenge encrypted with the NTLM hash
Server/DC          recomputes it from the stored hash and compares
```

The client proves identity by encrypting the challenge with the **NTLM hash**, never with the plaintext password. The hash is derived from the password but is used as if it *were* the password. So whoever holds the hash can authenticate without knowing or cracking the plaintext. That is **pass-the-hash**: feed a captured NTLM hash straight into an NTLM login and it succeeds.

### Why pass-the-hash sometimes fails

It is not universal. The usual reasons it works on one target but not another:

- **The target authenticates with Kerberos, not NTLM.** Pass-the-hash is an NTLM technique and does nothing against a Kerberos-only path. The fix is **overpass-the-hash**, which turns the same NTLM hash into a Kerberos TGT (see [AD Lateral Movement](/collections/oscp/ad-lateral-movement)). Connecting by IP tends to force NTLM; connecting by hostname tends to use Kerberos.
- **The account is a non-default local admin.** Since a 2014 security update, only the built-in Administrator (RID 500) and domain accounts can pass-the-hash for a remote admin login. Other local accounts in the Administrators group get a filtered token over the network, so their hash authenticates locally but not remotely.
- **The account is not admin on that host.** The hash may authenticate, but code execution (PsExec, wmiexec) also needs local admin rights and the `ADMIN$` share on the target. Authentication and code execution are separate hurdles.
- **The "hash" is not an NTLM hash.** Pass-the-hash uses the NT hash. An AS-REP or TGS-REP blob from roasting is not a pass-the-hash credential; it must be cracked (see the table below).

## Where credentials are stored: SAM, LSASS, ntds.dit

The hashes and tickets that the reuse and forging attacks consume come from one of three stores. Which store holds what, and what access each needs, explains why local admin usually has to come before credential theft.

- **SAM** (Security Account Manager): the **local** accounts' NTLM hashes on a single machine, kept in a registry hive encrypted with a key in the SYSTEM hive. It holds only that host's local accounts, never domain users. Reading it needs local admin or SYSTEM. Dumping the SAM and SYSTEM hives is covered in [Windows Credential Hunting](/collections/oscp/windows-credential-hunting).
- **LSASS** (Local Security Authority Subsystem Service): the process that performs authentication, and the richest target. In memory it caches the credentials of everyone logged on to that host: NTLM hashes, Kerberos tickets (TGTs and TGSs), and on older systems even plaintext. This is why lateral movement works: a privileged user's session on a host leaves that user's credentials in that host's LSASS, so an attacker with local admin there can steal them and act as that user elsewhere. Mimikatz reads it (`sekurlsa::logonpasswords` for hashes, `sekurlsa::tickets` for tickets) and needs admin or SYSTEM; LSA Protection can block it.
- **ntds.dit**: the domain database on the DC, holding the NTLM hashes and Kerberos keys of **every** domain account, krbtgt included. Reached over the network with [DCSync](/collections/oscp/dcsync) (needs replication rights) or from a shadow copy of the DC's disk (needs admin on the DC). This is the whole domain at once.

The pattern: SAM and LSASS need admin on the host in question, so a foothold often has to clear [Privilege Escalation (Windows)](/collections/oscp/privilege-escalation-windows) before any of this pays off; ntds.dit needs either DC admin or a privileged account that can DCSync.

## Hashes: reuse vs cracking

Windows never stores the plaintext password, only its **NTLM hash** (plus Kerberos keys). The hash is one-way, so it cannot be reversed back into the password. Dumping the domain database (`ntds.dit`, via [DCSync](/collections/oscp/dcsync) or a shadow copy) therefore yields hashes, not plaintext. NTLM is unsalted and fast to compute, though, so a weak password can still be recovered by guessing: hash each candidate and compare.

Given a hash, does it have to be cracked? Often no. Cracking recovers the plaintext; reuse skips cracking by using the artifact directly. Which is possible depends on what the artifact is.

- **NTLM hash** (derived from the password, dumped from LSASS or the SAM, or via [DCSync](/collections/oscp/dcsync)). Two options:
  - **Reuse it directly.** **Pass-the-hash** presents the NTLM hash to a service that speaks NTLM and authenticates without ever knowing the password (the hash *is* the proof NTLM checks). **Overpass-the-hash** converts the hash into a real Kerberos TGT. Both skip cracking. See [AD Lateral Movement](/collections/oscp/ad-lateral-movement).
  - **Crack it** with `hashcat -m 1000` to recover the plaintext, which is worth doing because a plaintext password can be sprayed, tried over RDP, and reused across services that do not accept a hash. See [Password Cracking](/collections/oscp/password-cracking).
- **Kerberos roast blobs** (the AS-REP and TGS-REP from roasting) can **only** be cracked offline; they are not a credential that can be replayed. Cracking does not extract anything from the blob, it guesses passwords until one reproduces it. AS-REP roasting recovers the **target user's** password (the AS-REP is under the user's key); Kerberoasting recovers the **service account's** password (the TGS is under the service account's key). Either way the output is a plaintext password, not a hash.
- **A Kerberos ticket** (a TGT or TGS itself, not a hash) is reused directly by injecting it into a session: **pass-the-ticket**. No cracking, no password.
- **A raw NTLM hash of krbtgt or a service account**, already in hand from a dump or [DCSync](/collections/oscp/dcsync), is used **directly** to forge tickets (golden and silver), so cracking it to plaintext is rarely needed. It often would not crack anyway: krbtgt, machine, and managed service accounts have random passwords. This is a different situation from Kerberoasting, where the artifact is a TGS-REP blob rather than the hash, so cracking is the only route to the password.

| Artifact                      | Reuse directly                    | Crack for plaintext                 |
| ----------------------------- | --------------------------------- | ----------------------------------- |
| NTLM hash                     | pass-the-hash / overpass-the-hash | optional, gives a reusable password |
| Kerberos ticket (TGT/TGS)     | pass-the-ticket                   | not applicable                      |
| AS-REP / TGS-REP roast blob   | no                                | required, yields a password         |
| krbtgt / service account hash | forge golden / silver ticket      | rarely needed                       |

## DCSync

Real domains run more than one DC, and DCs keep each other in sync by **replication** (the DRSUAPI protocol): one DC asks another for an account's data, which includes its password hash.

The weakness is that the DC answering the request does not verify the requester is really a DC. It only checks that the requesting account holds the replication rights (Replicating Directory Changes and its siblings), which **Domain Admins**, **Enterprise Admins**, and **Administrators** have by default.

So an account with those rights can ask a DC for **any** user's hash, including krbtgt and the domain Administrator, without running code on the DC or touching its disk. This is the clean way to harvest every hash once a sufficiently privileged account is compromised, and the krbtgt hash it yields is what makes a golden ticket possible. See [DCSync](/collections/oscp/dcsync).

## Where each concept is used

- Enumerate all of the above: [Active Directory Enumeration](/collections/oscp/active-directory-enumeration).
- The end-to-end plan: [Active Directory](/collections/oscp/active-directory).
- Credentials cached on hosts, and the tools that dump them: [Windows Credential Hunting](/collections/oscp/windows-credential-hunting).

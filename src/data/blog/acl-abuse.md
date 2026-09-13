---
title: "ACL Abuse"
slug: acl-abuse
category: notes
handbook: oscp
tags: ["active-directory"]
draft: false
pubDatetime: 2026-08-01T10:35:17+03:00
modDatetime: 2026-09-08T22:35:52+03:00
description: "Every AD object carries a DACL that lists who can do what to it."
---
Every AD object carries a DACL that lists who can do what to it. A misconfigured entry, a low-privileged account granted write-like rights over a user, group, or computer, is a direct escalation: those rights let the account take the target over. BloodHound draws each one as an edge and its Abuse tab prints the exact command; this note collects the common ones. The rights are exercised from a Windows foothold with PowerView, or from Kali with `bloodyAD`, impacket, or `net rpc`.

## The common edges

**ForceChangePassword over a user** resets the target's password without knowing the old one. The cleanest and most common.

```bash
net rpc password 'target' 'Newpass1!' -U 'corp.com/attacker%pass' -S dc.corp.com
bloodyAD --host dc.corp.com -d corp.com -u attacker -p pass set password target 'Newpass1!'
```
```powershell
# from a Windows foothold (PowerView)
Set-DomainUserPassword -Identity target -AccountPassword (ConvertTo-SecureString 'Newpass1!' -AsPlainText -Force)
```

**GenericAll / GenericWrite over a user** allows the reset above, or a stealthier path: write a fake SPN onto the account and Kerberoast it offline (targeted Kerberoasting), recovering the real password without changing it.

```bash
bloodyAD --host dc.corp.com -d corp.com -u attacker -p pass set object target servicePrincipalName -v 'fake/svc'
impacket-GetUserSPNs corp.com/attacker:pass -request-user target -dc-ip <DC_IP>    # then crack the hash
```

**GenericAll / AddMember over a group** adds a controlled account to the group, inheriting its rights. Adding into a privileged group is game over.

```bash
net rpc group addmem 'Target Group' attacker -U 'corp.com/attacker%pass' -S dc.corp.com
bloodyAD --host dc.corp.com -d corp.com -u attacker -p pass add groupMember 'Target Group' attacker
```
```powershell
Add-DomainGroupMember -Identity 'Target Group' -Members attacker
```

**GenericWrite / GenericAll over a computer** enables resource-based constrained delegation: set `msDS-AllowedToActOnBehalfOfOtherIdentity` to a controlled account and impersonate any user to that computer. See [Kerberos Delegation](/collections/oscp/kerberos-delegation).

**ReadLAPSPassword over a computer** reads that machine's local Administrator password straight out of the directory in cleartext. No write, no reset, nothing to clean up. See [LAPS](/collections/oscp/laps).

**Write access over an existing GPO** can become code execution through an immediate scheduled task. A computer task runs as SYSTEM on every computer in the GPO's scope, so check the link and scope before writing. On a member host, add a controlled domain account to local Administrators for lateral movement; on a DC, the same task can change domain group membership. [pyGPOAbuse](/collections/oscp/pygpoabuse) automates the SYSVOL and LDAP changes; it needs write access to both.

**WriteDacl / Owns over an object** lets the account rewrite that object's DACL and grant itself further rights over it (Owns/WriteOwner takes ownership first, which carries WriteDacl). This yields the replication rights for [DCSync](/collections/oscp/dcsync) only when the object is the **domain** itself; over an ordinary user, group, or computer it grants full control of that one object, nothing domain-wide.

## After the abuse

Each of these yields a new password, group membership, or right, so it feeds straight back into enumeration ([Active Directory](/collections/oscp/active-directory)) and lateral movement. Re-run BloodHound's "from owned" queries after every win.

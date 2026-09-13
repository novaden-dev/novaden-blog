---
title: "LAPS"
slug: laps
category: notes
handbook: oscp
tags: ["active-directory", "windows"]
draft: false
pubDatetime: 2026-08-03T22:49:06+03:00
modDatetime: 2026-09-09T21:52:45+03:00
description: "LAPS (Local Administrator Password Solution) exists because every machine deployed from one image shares one local Administrator password, so a single dumped hash pass-the-hashes across the whole estate."
---
LAPS (Local Administrator Password Solution) exists because every machine deployed from one image shares one local Administrator password, so a single dumped hash pass-the-hashes across the whole estate. LAPS gives each domain-joined machine a unique random local admin password and rotates it on a schedule.

The password is stored on the **computer object in AD**, in cleartext. That is not a flaw, it is the design: the directory is the store, and access is controlled by an ACL. The attack is entirely about who was granted read.

## The Attributes

Legacy LAPS, which is what most lab and exam material uses:

| Attribute | Holds |
| --- | --- |
| `ms-Mcs-AdmPwd` | The password, cleartext |
| `ms-Mcs-AdmPwdExpirationTime` | When it next rotates |

Windows LAPS, the 2023 rewrite built into the OS, uses `msLAPS-Password` (cleartext JSON carrying both the account name and the password), `msLAPS-EncryptedPassword` (DPAPI-encrypted, needs a decryption step), and `msLAPS-PasswordExpirationTime`. Query both naming schemes when unsure which is deployed.

`ms-Mcs-AdmPwd` is flagged confidential in the schema, so reading it needs an explicit grant rather than the general read that covers ordinary attributes. Deploying LAPS means delegating that read to whoever runs the helpdesk, and the misconfiguration is delegating it to an ordinary user.

## Finding Who Can Read It

BloodHound draws it as a **ReadLAPSPassword** edge from the principal to the computer, which is the reliable way to find it across a large domain. See [ACL Abuse](/collections/oscp/acl-abuse) for the surrounding edge types.

Without BloodHound, ask for the attribute. LDAP omits attributes the bound account cannot read rather than returning an error, so the query itself is the permission check: a value means the right is held, an empty result means it is not.

## Reading It

`nxc` has a module and formats the result:

```bash
nxc ldap <DC_IP> -u user -p 'password' -M laps
```

```text
LAPS  <DC_IP>  389  HUTCHDC  [*] Getting LAPS Passwords
LAPS  <DC_IP>  389  HUTCHDC  Computer:HUTCHDC$  User:  Password:<cleartext>
```

An empty `User` field is normal on legacy LAPS. There is no attribute holding the managed account's name, so the module has nothing to print, and the account is whatever the `AdminAccountName` policy set, defaulting to the built-in Administrator. Windows LAPS does store the name, hence the field.

Raw, when the module is unavailable or the output looks wrong:

```bash
ldapsearch -x -H ldap://<DC_IP> -D 'user@corp.com' -w 'password' \
  -b "DC=corp,DC=com" "(objectClass=computer)" ms-Mcs-AdmPwd
```

From a Windows foothold with PowerView:

```powershell
Get-DomainObject -Identity TARGETPC -Properties ms-mcs-admpwd
```

## Using It

The recovered password is the **local** Administrator of that one machine, not a domain account. That distinction decides how to authenticate:

```bash
evil-winrm -i <TARGET> -u Administrator -p '<password>'
impacket-psexec './Administrator:<password>@<TARGET>'
```

On a member server, authenticate locally (`.\Administrator`, or the bare username) rather than as `DOMAIN\Administrator`, which is a different account entirely and will fail. On a domain controller the distinction disappears, because a DC has no local account database and its Administrator is the domain Administrator. Reading LAPS off a DC is therefore domain admin outright, which is what happened on Hutch.

Local admin on a member server is not domain admin, but it is a foothold with SYSTEM available, so it feeds straight into credential dumping and [AD Lateral Movement](/collections/oscp/ad-lateral-movement).

## Rotation

The password expires and rotates on the schedule the policy sets, so one read is not durable. Re-read after a machine revert or a long gap rather than reusing a value from earlier in the engagement, and check `ms-Mcs-AdmPwdExpirationTime` when a known-good password stops working.

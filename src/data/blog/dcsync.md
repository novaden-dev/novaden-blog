---
title: "DCSync"
slug: dcsync
category: notes
handbook: oscp
tags: ["active-directory", "credentials"]
draft: false
pubDatetime: 2026-08-01T10:35:17+03:00
modDatetime: 2026-09-08T22:27:09+03:00
description: "DCSync abuses the directory replication protocol (MS-DRSR / DRSUAPI)."
---
DCSync abuses the directory replication protocol (MS-DRSR / DRSUAPI). Domain Controllers replicate account data to each other by design; DCSync impersonates a DC and asks a real DC to replicate secrets, pulling password hashes without reading `ntds.dit` from disk or running code on the DC. The concept is in [Active Directory Concepts](/collections/oscp/active-directory-concepts). Once a privileged account is in hand, it is the standard way to take the whole domain.

It requires an account with replication rights: Domain Admins, Enterprise Admins, Administrators, or any account granted `DS-Replication-Get-Changes` and `-Get-Changes-All` (an ACL misconfiguration BloodHound flags as a `DCSync` edge). With that, it runs from Kali over NTLM, no shell on the DC. Without replication rights, a shell on the DC with backup privileges can pull the database from disk instead: [NTDS.dit Extraction](/collections/oscp/ntds-dit-extraction).

## Dump

```bash
impacket-secretsdump -just-dc -outputfile domain_ntds 'DOMAIN/dauser:password@DC_IP'
impacket-secretsdump -just-dc -hashes :NTHASH 'DOMAIN/dauser@DC_IP'    # pass-the-hash instead of a password
nxc smb DC_IP -u dauser -p password --ntds                            # same from NetExec
```

- `-just-dc` pulls NTLM hashes and Kerberos keys; `-just-dc-ntlm` limits it to NTLM.
- `-outputfile <prefix>` saves `<prefix>.ntds` instead of only printing to the screen.
- Authenticate by IP over NTLM, so no Kerberos, no `/etc/krb5.conf`, no DNS.

## What comes out

Each line is `user:rid:lmhash:nthash:::`. The two that matter most:

- **`krbtgt`**: its hash forges golden tickets for domain-wide persistence ([Silver and Golden Tickets](/collections/oscp/silver-and-golden-tickets)).
- **`Administrator` and other privileged accounts**: pass-the-hash them into a shell or onto other hosts ([AD Lateral Movement](/collections/oscp/ad-lateral-movement)), no cracking needed.

Every hash can also go to [Password Cracking](/collections/oscp/password-cracking) (NT is hashcat mode 1000), but reuse by pass-the-hash usually beats cracking.

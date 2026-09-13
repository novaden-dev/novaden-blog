---
title: "Silver and Golden Tickets"
slug: silver-and-golden-tickets
category: notes
handbook: oscp
tags: ["kerberos"]
draft: false
pubDatetime: 2026-08-01T10:35:17+03:00
modDatetime: 2026-09-08T22:35:52+03:00
description: "Forged Kerberos tickets, built offline from a stolen key and injected without the DC ever issuing them."
---
Forged Kerberos tickets, built offline from a stolen key and injected without the DC ever issuing them. Both are post-compromise techniques: forging either already needs a hash that only comes from full compromise ([DCSync](/collections/oscp/dcsync) or a DC dump). A plain golden or silver ticket is persistence rather than a way in, but the inter-realm variant below is a genuine movement path, child domain to forest root. Injecting them runs into the same `/etc/krb5.conf` Kerberos plumbing noted in [Kerberos Delegation](/collections/oscp/kerberos-delegation).

Both need the **domain SID**: the `S-1-5-21-x-y-z` prefix shared by every object in the domain, without the trailing RID. Read it off any account's SID by dropping the last block (the domain Administrator is `...-500`):

```bash
impacket-lookupsid corp.com/user:pass@<DC_IP> | grep 'Domain SID'   # prints: Domain SID is: S-1-5-21-...
```

```powershell
Get-DomainSID          # PowerView, from a Windows foothold
whoami /user           # your own SID; strip its trailing RID for the domain SID
```

## Golden ticket

Forged from the `krbtgt` account hash, the key that signs every TGT in the domain. With it, a TGT can be minted for any user, real or not, with arbitrary group membership, valid until `krbtgt`'s password changes twice. Full domain persistence.

```bash
impacket-ticketer -nthash <krbtgt-NThash> -domain-sid <domain-SID> -domain corp.com Administrator
```

- `-domain-sid` is the SID prefix before the RID in a `--rid-brute` dump or the ntds output.
- Produces `Administrator.ccache`; it is used with `KRB5CCNAME` and `-k -no-pass`, as in [Kerberos Delegation](/collections/oscp/kerberos-delegation).

From a Windows host [Mimikatz](/collections/oscp/mimikatz) forges and injects it in one step, skipping the `.ccache` plumbing:

```
kerberos::golden /user:Administrator /domain:corp.com /sid:<domain-SID> /krbtgt:<krbtgt-NThash> /ptt
```

- `/krbtgt:` the krbtgt NT hash from the DC dump, `/sid:` the domain SID above, `/user:` any name to stamp on the ticket (the Domain Admin rights come from the default group RIDs mimikatz bakes in, so the name itself need not exist).
- `/ptt` injects it into the current session straight away; a `dir \\dc01.corp.com\c$` then works as that identity. Drop `/ptt` to write a `.kirbi` instead.

## Inter-realm: child domain to forest root

In a forest, owning a child domain owns the forest. The root DC accepts TGTs signed by the child's krbtgt (forest trust) and honors the SIDs inside the ticket, so a child-domain golden ticket forged with an extra SID becomes enterprise-wide admin. The extra SID is the root domain's SID plus RID 519 (Enterprise Admins, a group that exists only in the forest root):

```bash
impacket-ticketer -aesKey <child-krbtgt-aes256> \
  -domain sub.corp.com -domain-sid <child-domain-SID> \
  -extra-sid <root-domain-SID>-519 Administrator
```

- `-aesKey` over `-nthash`: AES tickets are the cleaner default; the aes256 key comes from the same dump (`[*] Kerberos keys` in [DCSync](/collections/oscp/dcsync) or [NTDS.dit Extraction](/collections/oscp/ntds-dit-extraction) output).
- No space before `-519`.
- Both SIDs are known once one shell exists on each side: the child SID is the prefix of `whoami /user` there, the root SID from `nltest /domain_trusts /v` (lists the whole forest with `Dom Sid`).
- Use it with `KRB5CCNAME` and `-k -no-pass` against the root DC by FQDN: `impacket-psexec -k -no-pass sub.corp.com/Administrator@DC01.corp.com`. Kerberos is FQDN-or-nothing, so the host must resolve ([Kerberos Delegation](/collections/oscp/kerberos-delegation) plumbing).
- Using the ticket needs a live KDC, and impacket finds it by resolving the realm name itself (`SUB.CORP.COM:88`, then `CORP.COM:88` for the referral). Without lab DNS, alias the realm names in `/etc/hosts` to the DC IPs or psexec dies with `Connection error (REALM:88) Name or service not known`.
- Mimikatz equivalent adds `/sids:<root-domain-SID>-519` to `kerberos::golden`.

Worked example with both SIDs, the trust output, and the psexec finish: Poseidon.

## Silver ticket

Forged from a single service or machine account hash, it signs a service ticket (TGS) for that one service only. Narrower than a golden ticket and quieter, because no DC is contacted at all: only the target service validates it. Useful for targeted access to one service (CIFS, MSSQL, HOST) on one host.

```bash
impacket-ticketer -nthash <service-NThash> -domain-sid <domain-SID> -domain corp.com -spn CIFS/host.corp.com Administrator
```

On a Windows host [Mimikatz](/collections/oscp/mimikatz) forges the same with `kerberos::golden` (it builds both ticket types); the service hash and `/target` are what make it a silver ticket rather than a golden one:

```
kerberos::golden /user:Administrator /domain:corp.com /sid:<domain-SID> /target:host.corp.com /service:cifs /rc4:<service-NThash> /ptt
```

- `/rc4:` the service account's NT hash (a machine account's name ends in `$`), `/target:` the host running the service, `/service:` the SPN class (`cifs` for SMB, `host`, `mssql`, `http`). Only that one service on that one host accepts the ticket.

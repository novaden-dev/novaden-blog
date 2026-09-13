---
title: "DNS Enumeration"
slug: dns-enumeration
category: notes
handbook: oscp
tags: ["dns", "enumeration"]
draft: false
pubDatetime: 2026-07-24T12:03:13+03:00
modDatetime: 2026-09-13T19:51:45+03:00
description: "DNS resolves names to addresses and stores other records describing a domain."
---
DNS resolves names to addresses and stores other records describing a domain. It normally uses UDP 53 for queries and TCP 53 for large responses and zone transfers. In Active Directory, DNS also locates domain controllers and domain services.

## Identify the Domain

```bash
dig @TARGET example.local A
dig @TARGET example.local NS
dig @TARGET example.local MX
```

`@TARGET` sends the query to the target DNS server. Query types select address, name-server, and mail-server records.

## Zone Transfer

```bash
dig @TARGET example.local AXFR
```

A successful transfer discloses the zone's hostnames and addresses. Try each authoritative name server. A failed transfer is normal and only means the zone is not exposed this way.

## Reverse Lookup

```bash
dig @TARGET -x 192.168.X.X
```

PTR records can identify domain controllers, file servers, and development systems.

## Active Directory Records

```bash
dig @TARGET _ldap._tcp.dc._msdcs.example.local SRV
dig @TARGET _kerberos._tcp.example.local SRV
```

SRV records identify domain controllers and where LDAP and Kerberos listen. Deeper use belongs in the [Active Directory](/collections/oscp/active-directory) methodology.

## What to Record

- Domain name and authoritative name servers
- Hostnames and addresses from records or a zone transfer
- Mail servers and domain controllers
- Names needed in `/etc/hosts` for virtual hosting or service access

DNS names feed [Web Content Discovery](/collections/oscp/web-content-discovery), [SMB Enumeration](/collections/oscp/smb-enumeration), and the [Active Directory](/collections/oscp/active-directory) workflow.

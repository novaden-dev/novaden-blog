---
title: "RPC Enumeration"
slug: rpc-enumeration
category: notes
handbook: oscp
tags: ["rpc", "enumeration"]
draft: false
pubDatetime: 2026-07-24T12:03:13+03:00
modDatetime: 2026-09-13T19:51:45+03:00
description: "RPC lets a client call functions on another machine."
---
RPC lets a client call functions on another machine. Unix `rpcbind` on 111 and the Windows MSRPC Endpoint Mapper on 135 both map services to other ports, but they expose different systems.

## Unix rpcbind

`rpcbind` tells clients which port an RPC program uses. NFS commonly appears behind it, so port 111 is a pointer to enumerate registered programs rather than a foothold by itself.

```bash
rpcinfo -p TARGET
sudo nmap -sV -p111 --script=rpcinfo TARGET
```

Look for `nfs`, `mountd`, and unexpected RPC programs on dynamic high ports. If NFS is registered:

```bash
showmount -e TARGET
```

The export and privilege-escalation checks continue in [NFS no_root_squash](/collections/oscp/nfs-no-root-squash).

## Windows MSRPC

Port 135 is the MSRPC Endpoint Mapper. Windows services register RPC interfaces with it and may send clients to dynamic high ports, commonly 49152 and above. Seeing 135 plus several high ports is normal on Windows and does not make each high port a separate custom application.

MSRPC is closely tied to SMB named pipes on 445. Practical enumeration usually starts with SMB because tools can use RPC interfaces to query users, groups, shares, policies, and host information.

```bash
enum4linux-ng TARGET
rpcclient -U '' -N TARGET
```

Useful commands inside `rpcclient`:

```text
srvinfo
enumdomusers
enumdomgroups
querydispinfo
```

Anonymous RPC access is frequently blocked. Retry once with credentials when they surface:

```bash
rpcclient -U 'DOMAIN/user%password' TARGET
```

## What to Record

- Unix RPC programs and their assigned ports
- NFS exports discovered through `mountd`
- Windows hostname, domain or workgroup, users, and groups
- Whether anonymous access failed, so the service is parked until credentials surface

Windows RPC findings feed [SMB Enumeration](/collections/oscp/smb-enumeration) and the [Active Directory](/collections/oscp/active-directory) workflow.

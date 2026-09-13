---
title: "Network Services Handbook"
slug: network-services-handbook
category: notes
handbook: oscp
tags: ["enumeration", "networking"]
draft: false
pubDatetime: 2026-07-24T12:03:13+03:00
modDatetime: 2026-09-13T18:05:23+03:00
description: "Port numbers suggest what may be running, but the banner and protocol response decide what the service actually is."
---
Port numbers suggest what may be running, but the banner and protocol response decide what the service actually is. Use this page as a map, then follow the service note for commands and decisions.

## Core Services

The ratings describe how services usually contribute to OSCP-style attack chains:

- **High**: commonly worth immediate attention for that role.
- **Medium**: regularly useful, but usually needs a supporting weakness.
- **Low**: mainly provides information or access after another step.
- **Conditional**: powerful when credentials, permissions, or a specific misconfiguration are present.

Privilege-escalation relevance includes exposing credentials or a misconfiguration that leads to higher privileges. It does not mean the remote port itself is a local privilege-escalation vulnerability.

| Port(s) | Protocol | What it does | Initial foothold | Privilege escalation | First question |
|---:|---|---|---|---|---|
|          21 | FTP                   | Transfers files over separate control and data connections                   | Medium | Low | Is anonymous access allowed, and is anything readable or writable? See [FTP Enumeration](/collections/oscp/ftp-enumeration)            |
|          22 | SSH                   | Provides encrypted remote shell access and file transfer                     | Conditional | Low | Are credentials or a private key already available, and does it even accept passwords? See [Brute Forcing Logins](/collections/oscp/brute-forcing-logins) |
|          25 | SMTP                  | Transfers email between mail systems                                         | Medium | Low | Does the banner expose an old daemon, or can users be enumerated? See [SMTP Enumeration](/collections/oscp/smtp-enumeration)            |
|  53 TCP/UDP | DNS                   | Resolves names and stores domain records                                     | Low | Low | Can the server disclose records or transfer its zone? See [DNS Enumeration](/collections/oscp/dns-enumeration)                         |
|      80/443 | HTTP/HTTPS            | Serves web applications and APIs                                             | High | Medium | What application, content, and virtual hosts are exposed? See [Web Content Discovery](/collections/oscp/web-content-discovery)               |
|  88 TCP/UDP | Kerberos              | Issues authentication tickets in an Active Directory domain                  | Medium | High | Is this a domain controller, and which domain and users exist?                                        |
| 111 TCP/UDP | rpcbind               | Maps Unix RPC programs such as NFS to their listening ports                  | Low | Conditional | Which RPC programs are registered? See [RPC Enumeration](/collections/oscp/rpc-enumeration)                                            |
|         135 | MSRPC Endpoint Mapper | Maps Windows RPC interfaces to dynamic high ports                            | Low | Medium | Which Windows services and management interfaces are exposed? See [RPC Enumeration](/collections/oscp/rpc-enumeration)                 |
|     139/445 | NetBIOS/SMB           | Provides Windows file, printer, named-pipe, and remote administration access | High | High | Can shares or host information be read anonymously or with known credentials? See [SMB Enumeration](/collections/oscp/smb-enumeration) |
|     161 UDP | SNMP                  | Exposes device and host management information                               | Medium | Medium | Does a default or weak community string allow a walk? See [SNMP Enumeration](/collections/oscp/snmp-enumeration)                        |
|     389/636 | LDAP/LDAPS            | Queries directory objects such as users, groups, and computers               | Low | High | Is anonymous bind allowed, or are domain credentials available?                                       |
|        1433 | MSSQL                 | Hosts Microsoft SQL Server databases                                         | Conditional | High | Are credentials available, and can the account execute OS commands? See [Database Enumeration](/collections/oscp/database-enumeration)      |
|        2049 | NFS                   | Shares Unix filesystems over the network                                     | Medium | High | Which exports are visible and mountable? See [NFS no_root_squash](/collections/oscp/nfs-no-root-squash)                                   |
|        3306 | MySQL                 | Hosts MySQL or MariaDB databases                                             | Conditional | Medium | Have application credentials surfaced? See [Database Enumeration](/collections/oscp/database-enumeration)                                   |
|        3389 | RDP                   | Provides an interactive Windows desktop session                              | Conditional | Low | Are valid Windows credentials available? See [Windows Remote Access](/collections/oscp/windows-remote-access)                                |
|        5432 | PostgreSQL            | Hosts PostgreSQL databases                                                   | Conditional | Medium | Have application credentials surfaced? See [Database Enumeration](/collections/oscp/database-enumeration)                                   |
|        6379 | Redis                 | Stores key-value data, commonly as an application's session or cache store   | High | High | Does it answer `INFO` without a password, and which user does the daemon run as? See [Database Enumeration](/collections/oscp/database-enumeration#redis) |
|   5985/5986 | WinRM                 | Provides remote Windows management over HTTP or HTTPS                        | Conditional | Low | Do known credentials permit a PowerShell session? See [Windows Remote Access](/collections/oscp/windows-remote-access)                       |

## How the Services Relate

Windows services often describe a single attack surface rather than independent ports:

- DNS locates the domain and its controllers.
- Kerberos authenticates domain identities.
- LDAP exposes directory objects and relationships.
- SMB provides shares, named pipes, and remote administration paths.
- MSRPC exposes management interfaces used by enumeration and remote actions.
- WinRM and RDP turn valid credentials into remote access when the account is permitted to log on.

On Unix-like targets, `rpcbind` on 111 commonly points to NFS on 2049 or another dynamically assigned port. Query the mapper before treating each high port as an unrelated service.

## Decision Rules

- Identify the service before choosing commands. A familiar port can host unfamiliar software.
- Try unauthenticated enumeration once, then park the service if it requires credentials.
- Revisit SMB, LDAP, WinRM, RDP, SSH, and databases whenever credentials surface. Include HTTP on Windows targets, since IIS features such as WebDAV authenticate against Windows accounts rather than an application login. See [WebDAV](/collections/oscp/webdav).
- Check what a service will accept before spending a credential on it. SSH with `PasswordAuthentication no` cannot take a password from any user, so a reuse test there returns `Permission denied (publickey)` regardless of how good the credential is. `nmap -p22 --script ssh-auth-methods TARGET` settles it in advance and redirects the reuse test to the services that can actually answer it (Sorcerer).
- Treat UDP as a separate attack surface. DNS, SNMP, Kerberos, and rpcbind may answer over UDP even when the TCP scan is quiet.
- Record what the service revealed and the next action in the attack-surface table from [Information Gathering](/collections/oscp/information-gathering).

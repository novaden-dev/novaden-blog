---
title: "Information Gathering"
slug: information-gathering
category: notes
handbook: oscp
format: methodology
tags: ["enumeration"]
draft: false
pubDatetime: 2026-07-18T17:48:53+03:00
modDatetime: 2026-09-09T22:04:52+03:00
description: "Start automation and manual enumeration together."
---
Start automation and manual enumeration together. Automation saves time and provides a second set of eyes, but its important findings should still be understood and reproduced manually.

## Setup

```bash
export TARGET=192.168.X.X

mkdir -p ~/oscp/machines/BOX/{scans,web,exploits,loot}
cd ~/oscp/machines/BOX
```

## Automated Enumeration

### AutoRecon

AutoRecon fits CTF and OSCP-style targets. It can run in the background while the initial manual scans are performed.

```bash
sudo autorecon "$TARGET"
```

Multi-target labs take space-separated targets on the same command line:

```bash
sudo autorecon "$TARGET1" "$TARGET2" "$TARGET3"
```

AutoRecon scans the targets in parallel and writes each host to its own folder under `results/`. A CIDR range works as a single argument, and a longer list can go in a file passed with `-t targets.txt`, one target per line.

Review points:

- What did AutoRecon and the manual process both find?
- What did AutoRecon find that I missed?
- What did I find that AutoRecon missed?
- Which commands failed or produced noise?
- Can I reproduce the useful results manually?

## Manual Enumeration

### Connectivity

```bash
ping -c 3 "$TARGET"
```

A failed ping does not prove that the target is offline. ICMP may be filtered.

### Full TCP port scan

```bash
sudo nmap -Pn -n -p- --min-rate 1000 -T4 --reason \
  -oA scans/tcp-all "$TARGET"
```

- `-Pn`: Treat the target as online without relying on ping.
- `-n`: Skip DNS resolution.
- `-p-`: Scan all 65,535 TCP ports.
- `--min-rate 1000`: Aim for at least 1,000 probes per second.
- `-T4`: Use faster timing suitable for a lab.
- `--reason`: Show why Nmap assigned each port state.
- `-oA`: Save normal, XML, and grepable output.

If the scan appears unreliable, remove `--min-rate 1000` and run it again more slowly.

### Service enumeration

Run version detection and default scripts against the ports found in the full scan:

```bash
sudo nmap -Pn -n -sC -sV -p22,80,8080 \
  -oA scans/tcp-services "$TARGET"
```

- `-sC`: Run the default Nmap scripts.
- `-sV`: Identify the service and its version.

Do not assume the service based only on its port number.

### Initial UDP scan

```bash
sudo nmap -Pn -n -sU --top-ports 100 --reason \
  -oA scans/udp-top100 "$TARGET"
```

Investigate any interesting UDP ports separately:

```bash
sudo nmap -Pn -n -sU -sC -sV -p161 \
  -oA scans/udp-services "$TARGET"
```

This phase is the easiest to skip and the most expensive to skip. A TCP-only pass never shows SNMP, and a box can then look like nothing but FTP, SSH and HTTP while the intended foothold sits on UDP 161. The top-100 list covers snmp, DNS, Kerberos, and rpcbind, which is most of what UDP ever answers on a lab target.

## Track the Attack Surface

The machine note should contain an attack-surface table:

| Port | Service | Version | Observations | Next action |
|---:|---|---|---|---|
| 22 | SSH |  |  |  |
| 80 | HTTP |  |  |  |

Every exposed service should lead to a deliberate next action.

### Common services and first action

| Port(s) | Service | First action |
|---|---|---|
| 21 | FTP | Banner for a version exploit, anonymous login, upload into a web root. See [FTP Enumeration](/collections/oscp/ftp-enumeration) |
| 22 | SSH | Park unless creds exist. Version only for the rare CVE |
| 25 | SMTP | Banner for the daemon/version, `VRFY`/`EXPN` user enumeration. See [SMTP Enumeration](/collections/oscp/smtp-enumeration) |
| 53 | DNS | Attempt a zone transfer (`dig axfr`) |
| 80/443 | HTTP | whatweb, directory brute force, read source. See [Web Content Discovery](/collections/oscp/web-content-discovery) |
| 111 | rpcbind | `rpcinfo -p TARGET` to list RPC services (NFS and others) |
| 139/445 | SMB | Null-session share listing and version. See [SMB Enumeration](/collections/oscp/smb-enumeration) |
| 199 | smux | SNMP multiplexing. snmpd is running, so scan UDP 161. See [SNMP Enumeration](/collections/oscp/snmp-enumeration) |
| 161/udp | SNMP | `snmpwalk -c public -v2c TARGET`. See [SNMP Enumeration](/collections/oscp/snmp-enumeration) |
| 3306 / 5432 / 1433 | MySQL / PostgreSQL / MSSQL | Try the default account once, then park until creds surface. See [Database Enumeration](/collections/oscp/database-enumeration) |
| 9090 | Cockpit | Web admin console that authenticates system accounts through PAM. Reuse any leaked password here, then its `Terminal` is a shell and its Accounts page writes `authorized_keys`. See [SSH Key Access](/collections/oscp/ssh-key-access) |

### Parked ports

Some ports are not a foothold on their own. SSH and database ports usually do nothing until a web app or a config file leaks credentials, after which they become the login or the credential store. Mark these "park, revisit once creds surface" in the attack-surface table instead of forcing them early. Snookums hit both: 22 and 3306 were dead until `db.php` leaked credentials, and then they carried the rest of the chain.

Park it after one attempt, not before. A database ships with a known account, and the cost of trying it is a single command. On Nibbles `postgres`/`postgres` was accepted, and the version behind that login was the whole box, with the web port serving an unedited HTML template. The same port was on 5437 rather than 5432, which changes nothing about the service: read the scan's service column, not the number.

An open port is not a path. Enumerate every service, but expect most boxes to have one intended door and several ports that only matter after it opens.

### Unknown or high ports

A port not in the table (for example 60000 on ClamAV) is unknown until it identifies itself, so banner-grab it before theorising:

```bash
nc -nv TARGET 60000
```

On lab boxes an unexpected high port is often a planted bind shell or backdoor, so type a command once connected. If the banner is silent, run `nmap -sV` against the single port for a version guess.

A high port that identifies as HTTP gets its own row and its own enumeration. It is a separate server with a separate docroot, not a second view of port 80, so its version, its application, and its content are all independent. Sea served an unrelated real-estate template on 80 and SeaCMS on 55743, and every finding about the box came from the second one.

A whole block of randomly numbered high ports is a different pattern. Distributed frameworks, clusters, and container runtimes open a set of ports from a range at startup, so the numbers look arbitrary and change on every restart. On CVE-2023-6019 the scan returned fourteen of them next to a web port, and all fourteen belonged to the Ray cluster whose dashboard was on 9000. Identify the web port first: one application usually explains the entire spread, and probing each port separately produces nothing.

### Usernames via auth-owners

nmap's default script set includes `auth-owners`, which queries identd (113) for the OS account that owns each open TCP connection and prints it under the relevant port as `_auth-owners: <user>`. It only fires when the target's own identd answers, which is uncommon, but when it does it hands over a real username before anything has been exploited. On Peppo the scan could not identify the service on port 10000 at all, yet still tagged it `_auth-owners: eleanor`, and that name was the SSH account the rest of the box was built around. Worth a look at the raw scan output on any unidentified port rather than only the summary line.

### HTTP on a low, non-web port

The reverse of a high port serving HTTP: a service on 21, 22, 23, 25, 110 or another well known port that answers HTTP instead of what the number implies. The scan names it correctly, and then the browser refuses to open it:

```text
This address is restricted
This address uses a network port which is normally used for purposes other than Web browsing.
```

That is Firefox and Chrome enforcing a hardcoded banned-port list, not a firewall and not a closed port. Nothing is wrong with the target, the browser simply will not send the request. Use a client that has no such list:

```bash
curl -i http://TARGET:23/
```

To keep using the browser, `about:config` > `network.security.ports.banned.override` > the port number. ZenPhoto served HTTP on 23 and the block reads exactly like an unreachable service.

### First-run setup wizards

An appliance shipped without an administrator account often exposes a first-run or setup wizard to whoever reaches it first. Claiming the admin account through that wizard satisfies the authentication requirement of any authenticated exploit for free. On Hub FuguHub 8.4 presented a Config Wizard at `/Config-Wizard/wizard/SetAdmin.lsp` that set the admin credentials to admin/admin, which then unlocked the authenticated RCE (CVE-2024-27697). Identify the product and version from its login or About page, look up the CVE, and check whether the setup is still open before assuming credentials are needed.

What the wizard asks for decides whether it is a lead. One that only wants an administrator username and password can be answered on the spot. One that wants credentials to a service it does not control cannot, and the half-installed application behind it has no attack surface at all: no config file to read, no accounts, no plugins. Extplorer served an uninstalled WordPress whose `setup-config.php` wanted database credentials, and the real path was the other application in the same webroot.

## Machine-note Shape

A machine note opens with the attack-surface table ([Track the Attack Surface](#track-the-attack-surface)), then tells the path in order: enumeration, vulnerability, exploitation, privilege escalation. Failed attempts stay inline where they taught something rather than in a separate mistakes section. The note closes with `## Takeaways`: the reusable lessons, each pointing at the technique note that carries the general method.

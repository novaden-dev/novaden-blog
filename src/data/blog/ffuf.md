---
title: "ffuf"
slug: ffuf
category: notes
handbook: oscp
tags: ["web", "enumeration"]
draft: false
pubDatetime: 2026-09-13T19:42:38+03:00
modDatetime: 2026-09-13T19:42:38+03:00
description: "Web fuzzer built around a replaceable `FUZZ` keyword and response filtering."
---
Web fuzzer built around a replaceable `FUZZ` keyword and response filtering. The same tool covers directory discovery, virtual host discovery, parameter fuzzing, and logins that need the response matched rather than the form parsed. The decisions (which list, which matcher, why a run returns noise) are in [Web Content Discovery](/collections/oscp/web-content-discovery); the vhost case is in [Virtual Hosts](/collections/oscp/virtual-hosts), the login use in [Brute Forcing Logins](/collections/oscp/brute-forcing-logins).

## Install

Ships with Kali:

```bash
sudo apt install ffuf
```

## Command Shapes

```bash
# directories, with extensions
ffuf -u http://TARGET/FUZZ -w /usr/share/seclists/Discovery/Web-Content/raft-large-directories.txt -e .php,.txt

# filter a soft 404 out by response size
ffuf -u http://TARGET/FUZZ -w LIST -fs 4242

# let ffuf measure the catch-all itself
ffuf -u http://TARGET/FUZZ -w LIST -ac

# request parameters
ffuf -u "http://TARGET/page?FUZZ=1" -w params.txt -fs 4242

# virtual hosts, through the Host header
ffuf -u http://TARGET/ -H "Host: FUZZ.loly.lc" -w subdomains.txt -fs 4242

# JSON login brute force
ffuf -u http://TARGET/api/login -X POST -w rockyou.txt \
  -H 'Content-Type: application/json' -d '{"user":"admin","pass":"FUZZ"}' -fr 'invalid'
```

- `FUZZ` is the placeholder wordlist entries replace, anywhere in URL, header, or body.
- `-w` is the wordlist; `-e .php,.txt` appends extensions as extra requests.
- Every matcher `-m*` keeps matches on one dimension (status `-mc`, size `-ms`), and every filter `-f*` hides them (`-fc`, `-fs`); `-fr` matches response content. They compose, so `-mc 200,301` and `-fs 4242` can share a run.
- `-ac` auto-calibrates: requests a few random paths, learns the catch-all, and filters anything that matches it.
- `-ic` skips comment lines in lists such as the DirBuster sets, whose `#` headers otherwise get requested as paths and produce a block of identical junk hits at the top.

The wordlist decides most of the outcome. The list choices and the comment-line trap are covered in [Web Content Discovery](/collections/oscp/web-content-discovery).

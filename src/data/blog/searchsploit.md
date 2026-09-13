---
title: "SearchSploit"
slug: searchsploit
category: notes
handbook: oscp
tags: ["exploit-development"]
draft: false
pubDatetime: 2026-07-18T17:48:53+03:00
modDatetime: 2026-09-08T22:27:09+03:00
description: "SearchSploit searches the local Exploit-DB copy included with Kali."
---
SearchSploit searches the local Exploit-DB copy included with Kali. It can also copy a PoC into the current working directory.

## Install

SearchSploit is normally installed on Kali. If it is missing:

```bash
sudo apt update
sudo apt install -y exploitdb
```

## Search

Search by product and version:

```bash
searchsploit saltstack 3000.1
```

Search by CVE:

```bash
searchsploit --cve 2020-11651
```

## Inspect a PoC

Open an entry in the terminal before copying or running it:

```bash
searchsploit -x 48421
```

Show its location in the local Exploit-DB repository:

```bash
searchsploit -p 48421
```

## Copy a PoC

Change to the current machine's exploit directory:

```bash
cd ~/oscp/machines/BOX/exploits
```

Copy EDB-ID 48421 into that directory:

```bash
searchsploit -m 48421
```

Confirm the file type and read the usage information:

```bash
file 48421.py
python3 48421.py -h
```

Do not run a PoC before reading it. Check:

- Which target and port it uses.
- Whether it writes or deletes files.
- Whether it executes commands automatically.
- Which dependencies it imports.
- Whether it expects Python 2 or Python 3.
- Whether its vulnerable version range matches the discovered service.

## Download Fallback

If the local database does not contain the entry:

```bash
curl -o 48421.py https://www.exploit-db.com/download/48421
```

The local SearchSploit copy is preferred because it is quick, works offline, and avoids copying code manually from the website.

## Update

```bash
searchsploit -u
```

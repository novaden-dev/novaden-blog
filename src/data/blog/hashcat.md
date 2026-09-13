---
title: "hashcat"
slug: hashcat
category: notes
handbook: oscp
tags: ["password-attacks"]
draft: false
pubDatetime: 2026-09-13T19:42:38+03:00
modDatetime: 2026-09-13T19:42:38+03:00
description: "Password cracker built for GPUs: each hash format needs an explicit mode number, and the right `-m` comes from the format table in [Password Cracking](/collections/oscp/password-cracking)."
---
Password cracker built for GPUs: each hash format needs an explicit mode number, and the right `-m` comes from the format table in [Password Cracking](/collections/oscp/password-cracking). Faster than [john](/collections/oscp/john) where a compute backend exists, but on the Kali VM it needs OpenCL installed first, and even then bcrypt-class hashes stay CPU-slow, so john usually wins for a single hash on the VM.

## Install

```bash
sudo apt install hashcat
```

## Identify the Mode

```bash
hashcat --identify hash.txt     # prints the matching -m modes
hashcat --help | grep -i <format>
```

john auto-detects; hashcat needs the mode, and `--identify` on a hash file is the quickest way to the number.

## Crack a Wordlist

```bash
hashcat -m 10500 pdf.hash /usr/share/wordlists/rockyou.txt
hashcat --show -m 10500 pdf.hash
```

- `-m` sets the hash mode; the artifact-to-mode mapping lives in [Password Cracking](/collections/oscp/password-cracking).
- `-a 0` (dictionary against the wordlist) is the default attack mode.
- `--show` prints the potfile of cracks recovered so far instead of running again.

## OpenCL Backend on the VM

On a Kali VM with no GPU, hashcat exits at once with `No OpenCL, HIP or CUDA compatible platform found`, because it has no compute backend. To run on CPU anyway, install an OpenCL CPU runtime and confirm a device with `hashcat -I`.

```bash
apt-cache search opencl | grep -i icd
sudo apt install -y pocl-opencl-icd
```

`pocl-opencl-icd` is the cleanest CPU backend but is sometimes dropped from Kali rolling. `mesa-opencl-icd` installs, but modern Mesa uses rusticl, which lists no device until `RUSTICL_ENABLE=llvmpipe` is exported, so `hashcat -I` reports `No devices found` until then. It is still CPU-speed bcrypt after all that, so [john](/collections/oscp/john), which needs none of it, is usually the better use of time.

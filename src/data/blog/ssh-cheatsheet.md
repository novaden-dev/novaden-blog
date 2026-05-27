---
author: Kayra
pubDatetime: 2026-05-27T00:00:00Z
title: SSH Cheat Sheet
slug: ssh-cheatsheet
featured: false
draft: false
tags:
  - linux
  - networking
  - security
  - cheatsheet
  - notes
description: A quick-reference of the SSH commands I actually use, from key generation and copying through port forwarding, file transfer, jump hosts, and sshd hardening.
---

A living quick-reference for the SSH commands I actually use. For the model behind any of this, see [SSH Foundations](/posts/ssh-foundations).

## Connecting

```bash
# Basic connection
ssh user@host

# Non-default port
ssh -p 2222 user@host

# Use a specific identity (private key)
ssh -i ~/.ssh/work_key user@host

# Run a single command and exit
ssh user@host "uptime"

# Force a TTY (e.g. for interactive prompts inside the remote command)
ssh -t user@host "sudo less /var/log/syslog"

# Verbose output for debugging (-vv and -vvv for more)
ssh -v user@host
```

## Generating Keys

```bash
# Generate a modern Ed25519 key (recommended default)
ssh-keygen -t ed25519 -C "kayra@laptop"

# Generate an RSA key (use when forced to by an older server)
ssh-keygen -t rsa -b 4096 -C "kayra@laptop"

# Specify a custom output path
ssh-keygen -t ed25519 -f ~/.ssh/work_key -C "kayra@work"

# Change or add a passphrase on an existing key
ssh-keygen -p -f ~/.ssh/id_ed25519

# Show the fingerprint of a key
ssh-keygen -lf ~/.ssh/id_ed25519.pub
```

## Copying Your Key to a Server

```bash
# Easy way: ssh-copy-id appends your public key to the server's authorized_keys
ssh-copy-id user@host
ssh-copy-id -i ~/.ssh/work_key.pub user@host
ssh-copy-id -p 2222 user@host

# Manual way (when ssh-copy-id isn't available)
cat ~/.ssh/id_ed25519.pub | ssh user@host "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

## SSH Agent

```bash
# Start the agent in the current shell (most distros start one automatically on login)
eval "$(ssh-agent -s)"

# Add a key to the agent (prompts for passphrase once)
ssh-add ~/.ssh/id_ed25519

# Add with a lifetime (auto-expires from the agent after 1h)
ssh-add -t 3600 ~/.ssh/id_ed25519

# List keys currently held by the agent
ssh-add -l

# Remove a specific key
ssh-add -d ~/.ssh/id_ed25519

# Remove all keys
ssh-add -D

# Forward your agent for this session (use sparingly, see foundations)
ssh -A user@host
```

## ~/.ssh/config

```text
# Per-host defaults so you can type `ssh prod-web` instead of the full command
Host prod-web
    HostName 10.0.0.5
    User deploy
    Port 2222
    IdentityFile ~/.ssh/work_key

# Jump through a bastion in one hop
Host internal-db
    HostName 10.0.5.42
    User dba
    ProxyJump bastion.example.com

# Wildcard defaults for an internal network
Host *.internal
    User admin
    IdentityFile ~/.ssh/internal_key

# Keep idle connections alive across NAT timeouts
Host *
    ServerAliveInterval 60
    ServerAliveCountMax 3
```

```bash
# Validate the effective config for a given host (shows what ssh would actually use)
ssh -G prod-web
```

## File Transfer

```bash
# scp: simple copy over SSH
scp file.txt user@host:/remote/path/
scp user@host:/remote/file.txt ./
scp -r dir/ user@host:/remote/path/      # recursive
scp -P 2222 file.txt user@host:~          # non-default port (capital P, unlike ssh)

# rsync over SSH: faster, resumable, only sends changed bytes
rsync -avz dir/ user@host:/remote/path/
rsync -avz -e "ssh -p 2222" dir/ user@host:/remote/path/
rsync -avz --delete dir/ user@host:/remote/path/   # mirror exactly (delete extras on the other side)

# sftp: interactive file transfer session
sftp user@host
# common sftp commands: ls, cd, get file, put file, mget *.txt, bye
```

> **Danger:** `rsync --delete` will remove files on the destination that don't exist on the source. Always dry-run first with `-n` (`rsync -avzn --delete ...`).

## Port Forwarding

```bash
# Local forwarding: localhost:8080 -> internal-host:80 via jump
ssh -L 8080:internal-host:80 user@jump

# Listen on all local interfaces (not just 127.0.0.1)
ssh -L 0.0.0.0:8080:internal-host:80 user@jump

# Remote forwarding: jump's localhost:9000 -> my-laptop:3000
ssh -R 9000:localhost:3000 user@jump

# Dynamic forwarding: SOCKS proxy on localhost:1080
ssh -D 1080 user@jump

# Tunnel only, no shell (-N), in the background (-f)
ssh -fN -L 8080:internal-host:80 user@jump
```

## Jump Hosts (Bastions)

```bash
# Hop through a bastion to reach an internal host
ssh -J bastion.example.com user@10.0.5.42

# Multiple hops
ssh -J bastion1,bastion2 user@10.0.5.42

# Permanent version in ~/.ssh/config
# Host internal-db
#     HostName 10.0.5.42
#     ProxyJump bastion.example.com
```

## known_hosts Management

```bash
# Remove the stored host key for a host (after a legitimate rebuild / IP reuse)
ssh-keygen -R host
ssh-keygen -R 10.0.0.5

# Show the fingerprint a server is currently presenting
ssh-keyscan host
ssh-keyscan -t ed25519 host

# Add a host's keys to known_hosts non-interactively
ssh-keyscan host >> ~/.ssh/known_hosts
```

> **Note:** `ssh-keyscan` does not verify the key. If you pipe its output straight into `known_hosts` you are trusting whoever answers on that IP. For real security, get the expected fingerprint out-of-band and compare.

## Permissions

```bash
# Fix .ssh permissions (do this whenever public-key auth mysteriously fails)
chmod 700 ~/.ssh
chmod 600 ~/.ssh/id_* ~/.ssh/authorized_keys ~/.ssh/config 2>/dev/null
chmod 644 ~/.ssh/*.pub ~/.ssh/known_hosts 2>/dev/null
```

## Debugging Failed Connections

```bash
# Increase client verbosity (more v = more output)
ssh -v user@host
ssh -vvv user@host

# Show which config block ssh thinks applies to a host
ssh -G host

# Test sshd config syntax on the server before reloading
sudo sshd -t

# Tail the server's auth log live (Debian/Ubuntu)
sudo tail -f /var/log/auth.log

# Tail sshd logs via journalctl (Fedora/RHEL/systemd)
sudo journalctl -u sshd -f
```

Common failure causes to check first: wrong key tried (look for `Offering public key`), permissions too open on `~/.ssh` or `authorized_keys`, `PasswordAuthentication no` with no key loaded, server on a non-default port, or a stale `known_hosts` entry.

## Server: Hardening sshd

Edit `/etc/ssh/sshd_config`, then validate and reload:

```bash
sudo sshd -t                                  # syntax check
sudo systemctl reload sshd                    # apply
```

Settings worth knowing:

```text
# /etc/ssh/sshd_config

Port 2222                                     # move off 22 to cut brute-force noise
PermitRootLogin no                            # no direct root login
PasswordAuthentication no                     # public keys only
PubkeyAuthentication yes
PermitEmptyPasswords no
MaxAuthTries 3
LoginGraceTime 30
AllowUsers deploy admin                       # whitelist specific users
AllowGroups ssh-users                         # or whitelist a group
ClientAliveInterval 300                       # drop idle sessions after 5 min of silence
ClientAliveCountMax 2
```

> **Danger:** before disabling password auth, confirm your public key actually works in a *separate* SSH session. Otherwise a config typo plus a reload locks you out of the box.

## Misc

```bash
# Run a local script on a remote host
ssh user@host "bash -s" < local_script.sh

# Copy your clipboard into a remote file
xclip -o -selection clipboard | ssh user@host "cat > /tmp/from-laptop.txt"

# Mount a remote directory over SSH (needs sshfs)
sshfs user@host:/remote/path /local/mountpoint
fusermount -u /local/mountpoint               # unmount

# Generate an authorized_keys entry that restricts what the key can do
# (prepended to the public key line on the server)
command="rsync --server -vlogDtpre.iLsfx . /backups/",no-pty,no-port-forwarding ssh-ed25519 AAAA... user@host
```

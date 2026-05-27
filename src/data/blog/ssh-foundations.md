---
author: Kayra
pubDatetime: 2026-05-27T00:00:00Z
title: SSH Foundations
slug: ssh-foundations
featured: false
draft: false
tags:
  - linux
  - networking
  - security
  - notes
description: The mental model behind SSH. How the handshake works, host keys, public-key authentication, the agent, port forwarding, and why permissions matter.
---

## Introduction

SSH (Secure Shell) is the standard way to log into a remote machine over an untrusted network and run commands as if you were sitting in front of it. It replaced older protocols like `telnet` and `rsh`, which sent everything (including passwords) in cleartext. SSH gives you an encrypted channel, server authentication, and several ways to prove who you are. It's the protocol behind remote shells, `git push`, `scp`, `rsync`, and almost every other "I need to do something on that box over there" workflow.

## Client / Server Model

Every SSH session has two halves:

- **Server**: a daemon (`sshd`) listening on a port, by default `22/tcp`. It owns a host keypair that identifies the machine itself.
- **Client**: the `ssh` program you run. It optionally owns a user keypair that identifies *you*, and it remembers which servers it has talked to before.

You connect with `ssh user@host`. The user is who you want to be on the remote box; the host is the server you're connecting to. They're independent of your local username.

### The Host Keypair

When `openssh-server` is installed, the package generates a keypair *for the machine itself* and saves it under `/etc/ssh/` (typically `ssh_host_ed25519_key` and `ssh_host_ed25519_key.pub`, plus older RSA/ECDSA variants). This keypair is the server's permanent identity. It sticks around across reboots, sshd restarts, and package upgrades. It only changes if the machine is reinstalled, the key files are deleted, or someone explicitly regenerates them.

That permanence is the whole point. The first time you connect, the client pins the server's public host key in `~/.ssh/known_hosts`. Every connection after that compares the offered key against the pinned one. If they always match, you can trust you're talking to the same machine you onboarded the first time. If a host key suddenly changes, either the box was legitimately rebuilt, or someone is sitting between you and the real server.

## How the Handshake Works

The setup phase happens before you see a shell prompt and roughly goes:

1. **TCP connection** to the server's SSH port.
2. **Protocol and algorithm negotiation**. Both sides advertise which SSH version, ciphers, MACs, key-exchange methods, and host-key types they support, and pick the strongest match.
3. **Key exchange**. The two sides run a Diffie-Hellman style exchange to agree on a shared symmetric session key without ever sending it across the wire. Everything after this point is encrypted with that key.
4. **Server authentication**. The server proves it owns the private half of its host key by signing part of the exchange. The client checks the signature against the public host key.
5. **User authentication**. Now the client has to prove who *you* are. This is the step where password or public-key authentication happens.
6. **Channel open**. Once you're authenticated, the server opens an interactive shell, runs a command, sets up a tunnel, or whatever else the client asked for.

The important split: steps 1 through 4 prove the *server* is who it claims to be and set up an encrypted pipe. Step 5 proves the *user* is who they claim to be.

## Host Keys and Trust on First Use

The server's host key answers the question "am I actually talking to the machine I think I am, or did someone intercept the connection?" The client checks the server's public host key against `~/.ssh/known_hosts`.

- **First connection**: the key isn't in `known_hosts` yet. SSH prints the fingerprint and asks you to confirm. If you say yes, the public key is pinned in `known_hosts`. This pattern is called **Trust On First Use (TOFU)**.
- **Subsequent connections**: SSH compares the offered key against the stored one. If they match, you connect silently. If they don't, SSH refuses to connect and prints a loud warning about a possible man-in-the-middle.

> **Gotcha:** the warning also fires if the server's host key was legitimately rotated (reinstall, new VM with the same IP, etc.). The fix is to remove the stale entry with `ssh-keygen -R host`, not to blindly say "yes" to a new key. Out-of-band verification of the new fingerprint is the only thing that actually keeps you safe here.

## Authentication Methods

Once the encrypted pipe is up, the server asks you to authenticate. The two methods you'll see in practice:

### Password Authentication

You type a password, the client sends it over the (already encrypted) channel, and the server checks it against the local user database. Simple, but every login is one phishable secret away from compromise, and password-based logins are the favourite target of brute-force botnets scanning the internet for port 22.

### Public Key Authentication

You generate a keypair on the client. The **public key** is copied to the server and appended to `~/.ssh/authorized_keys` under the target user's home. The **private key** stays on the client (ideally protected by a passphrase). When you log in:

1. The client says "I want to authenticate as `user` with this public key."
2. The server checks whether that public key is listed in the target user's `authorized_keys`.
3. If so, the server sends a challenge. The client signs it with the private key. The server verifies the signature with the public key.
4. No secret ever leaves the client, and the signature is only valid for this one session.

This is the recommended default. Hardened servers turn off password authentication entirely (`PasswordAuthentication no` in `sshd_config`) so that public keys are the only way in. Three reasons it's worth doing:

- **Brute force.** Any SSH port reachable from the internet gets hammered by botnets trying common username/password pairs. With password auth disabled, there's nothing for them to guess.
- **Nothing to phish or keylog.** A password is something you type, and anything you type can be stolen. A private key is a file that lives on disk and never moves.
- **No shared secret on the server.** With password auth, the server stores a hash of your password. If the server is compromised, attackers can try to crack it offline. With public keys, the server only ever sees your *public* key, which is useless to an attacker.

## Public Key Cryptography in SSH

A keypair is two mathematically linked files:

- `~/.ssh/id_ed25519` (private). Never leaves your machine. Should be `chmod 600` and ideally encrypted with a passphrase.
- `~/.ssh/id_ed25519.pub` (public). Safe to share. Goes into `authorized_keys` on every server you want access to.

Anything signed with the private key can be verified with the public key, and anything encrypted with the public key can only be read with the private key. SSH uses the signing half: the server doesn't need your private key, it just needs to verify signatures the client produces with it.

### Key Types

Modern SSH supports several algorithms. In practice:

- **Ed25519**: small, fast, modern, recommended default. Use unless something forces you onto an older algorithm.
- **RSA**: still widely supported. Use at least 3072 bits, ideally 4096. Older 1024-bit RSA keys are considered weak.
- **ECDSA**: present but rarely the right pick over Ed25519.
- **DSA**: deprecated. Don't generate new ones.

### The Key Files

| File | Purpose |
| --- | --- |
| `~/.ssh/id_ed25519` | Your private key. Keep secret. |
| `~/.ssh/id_ed25519.pub` | Your public key. Safe to share and copy to servers. |
| `~/.ssh/authorized_keys` | Public keys that are allowed to log in as *this user* on *this server*. |
| `~/.ssh/known_hosts` | Public host keys of servers this client has previously connected to. |
| `~/.ssh/config` | Per-host client settings (aliases, default user, key, port, jump hosts). |

## The SSH Agent

If your private key has a passphrase (it should), typing it on every connection gets old fast. The **SSH agent** is a background process that holds your decrypted private keys in memory and signs challenges on behalf of the SSH client. You unlock the key once per login session, and every subsequent `ssh`, `scp`, `git push`, or `rsync -e ssh` uses the agent silently.

The agent also enables **agent forwarding**: when you SSH from machine A to machine B with `-A`, machine B can use your local agent (via a forwarded socket) to authenticate onward to machine C, without your private key ever leaving machine A.

> **Note:** agent forwarding gives root on the intermediate host the ability to impersonate you while the session is open. Only forward your agent to hosts you trust. For untrusted hops, prefer `ProxyJump` (which just routes the connection through, without exposing your agent).

## Port Forwarding

SSH isn't only a shell. Because the protocol multiplexes channels over a single encrypted connection, you can also tunnel arbitrary TCP traffic through it. Three flavours, and the difference is which side initiates the listening socket and which side initiates the outbound connection.

### Local Forwarding (`-L`)

`ssh -L 8080:internal-host:80 user@jump` means: on *my local machine*, listen on `localhost:8080`. Anything that connects to it is forwarded through the SSH connection to `jump`, which then opens a TCP connection to `internal-host:80` and proxies the bytes back and forth.

Use case: reach a service that's behind a firewall, but the firewall lets you SSH into a host that can reach it.

### Remote Forwarding (`-R`)

`ssh -R 9000:localhost:3000 user@public` means: on the *remote machine* (`public`), listen on `localhost:9000`. Anything that connects there is forwarded back through the SSH tunnel to *your local machine*, which then connects to `localhost:3000`.

Use case: expose a service running on your laptop to a remote host, or punch out from behind a NAT to a server you control.

### Dynamic Forwarding (`-D`)

`ssh -D 1080 user@jump` opens a SOCKS proxy on your local `localhost:1080`. Any application that supports SOCKS (browsers, `curl --socks5`, many tools) can use it, and the traffic comes out of `jump` to the wider internet.

Use case: a lightweight VPN-style escape hatch when you want all your traffic to egress from a particular host.

## The SSH Config File

`~/.ssh/config` lets you stop typing long command lines. Instead of `ssh -p 2222 -i ~/.ssh/work_key -J bastion.example.com deploy@10.0.0.5`, you write a block once and then `ssh prod-web`:

```text
Host prod-web
    HostName 10.0.0.5
    User deploy
    Port 2222
    IdentityFile ~/.ssh/work_key
    ProxyJump bastion.example.com
```

The config file also supports wildcards (`Host *.internal`) and is read by `ssh`, `scp`, `sftp`, `rsync -e ssh`, and most other tools that wrap the SSH client, so any alias you define works everywhere.

## Permissions Matter

SSH is paranoid about file permissions, and it will silently refuse to use files that are too open. The rule of thumb is "only the owning user can read or write." Common requirements:

| Path | Mode | Why |
| --- | --- | --- |
| `~/.ssh` | `700` | Only you can list or modify the directory. |
| `~/.ssh/id_*` (private keys) | `600` | Only you can read your secret keys. |
| `~/.ssh/*.pub` | `644` | Public, but only you can modify. |
| `~/.ssh/authorized_keys` | `600` | Only you can change who can log in as you. |
| `~/.ssh/config` | `600` | Only you can change connection defaults. |

If you ever see "Permissions are too open" or silent public-key failures, check these first. The same rules apply on the server: a world-writable `~/.ssh` or `authorized_keys` will be ignored even though the keys inside it look fine.

> **Quick reference:** the actual commands for generating keys, copying them to servers, tunneling, transferring files, and hardening `sshd` live in the [SSH Cheat Sheet](/posts/ssh-cheatsheet).

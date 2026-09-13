---
title: "Restricted Shells"
slug: restricted-shells
category: notes
handbook: oscp
tags: ["shells"]
draft: false
pubDatetime: 2026-08-13T19:41:23+03:00
modDatetime: 2026-09-13T20:51:50+03:00
description: "`rbash` (restricted bash, either the account's login shell or plain bash invoked with `argv[0]` starting with `r`) blocks a fixed set of things for the life of the session: `cd`, changing `PATH`, `SHELL`, `ENV`, or `BASH_ENV`, running any command whose name contains a `/` (so no absolute paths and no `./binary`), `exec`, and output redirection (`>`, `>>`, `<>`, `>&`, `&>`)."
---
`rbash` (restricted bash, either the account's login shell or plain bash invoked with `argv[0]` starting with `r`) blocks a fixed set of things for the life of the session: `cd`, changing `PATH`, `SHELL`, `ENV`, or `BASH_ENV`, running any command whose name contains a `/` (so no absolute paths and no `./binary`), `exec`, and output redirection (`>`, `>>`, `<>`, `>&`, `&>`). Input redirection (`<`) is not on that list, which matters for reading files once other options run out.

The tell is the prompt itself (`-rbash` instead of a plain `$`), or an external command failing with `command not found` even though it obviously exists on a normal Linux box. That second symptom is `$PATH` locked to a small whitelisted directory rather than an actual restriction on the command:

```bash
echo $PATH        # often just $HOME/bin
ls $HOME/bin       # the whitelist
```

## Reading a File Without an External Command

If nothing whitelisted can `cat`, use shell builtins instead. Builtins bypass `$PATH` entirely, so the whitelist and the slash rule are both irrelevant, and input redirection still works:

```bash
while IFS= read -r line; do echo "$line"; done < local.txt
```

## Escaping via a Whitelisted Binary

Any program on the whitelist that can itself run a shell escapes the restriction entirely, because the escape is a fresh `exec`/`system()` call made by a trusted binary, not something the restricted shell's own parser has to accept. Check GTFOBins' "Shell" function for whatever is on the whitelist. `ed` is a common one to find on a stripped-down box, since it looks harmless (a line editor) next to `chmod`/`chown`/`ls`/`mv`/`ping`/`sleep`/`touch`:

```text
ed
!/bin/sh
```

`vi`/`vim` (`:!/bin/sh`), `awk` (`system("/bin/sh")`), `find` (`-exec /bin/sh \;`), and `less`/`more`/`man` (`!/bin/sh` from the pager prompt) all work the same way when present.

### The escaped shell is not still restricted

A fresh `/bin/sh` spawned this way can still report ordinary commands as `not found`, which reads like the restriction survived. It didn't: the new shell inherited the same crippled `$PATH` from the parent environment, and `export` is not blocked outside rbash, so fixing it directly works:

```bash
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH
```

### Forcing a command over SSH does not always bypass it

A restriction enforced through `.bashrc` follows the account: bash sources `.bashrc` when it detects it was started by sshd, even for a non-interactive command like `ssh user@host bash`, so the restriction still applies. Only login-shell rc files (`.bash_profile`) are skipped that way. And if the account's actual login shell is `rbash`, sshd execs that shell first regardless of interactivity, so `ssh user@host bash` still runs through rbash and fails with `bash: command not found` if `bash` itself was never on the whitelist. Peppo was the second case, and the `ed` escape was needed instead.

### PATH resets on every new interactive shell

If the box enforces the restriction by having `.bashrc` pin `PATH=$HOME/bin` on every interactive shell rather than only through the account's login shell field, a fixed `$PATH` does not survive spawning another interactive bash. `python -c 'import pty; pty.spawn("/bin/bash")'` (see [Reverse Shells](/collections/oscp/reverse-shells#stabilizing-the-shell)) re-sources `.bashrc` and wipes the export out again. Re-run the same `export PATH=...` line after the upgrade, or skip the rc files entirely:

```bash
bash --norc --noprofile
```

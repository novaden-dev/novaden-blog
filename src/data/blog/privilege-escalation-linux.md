---
title: "Privilege Escalation (Linux)"
slug: privilege-escalation-linux
category: notes
handbook: oscp
format: methodology
tags: ["privilege-escalation", "linux"]
draft: false
pubDatetime: 2026-07-18T17:48:53+03:00
modDatetime: 2026-09-13T17:59:14+03:00
description: "Goal: turn a low-privilege shell into root."
---
Goal: turn a low-privilege shell into root. This note is the decision workflow: how to enumerate, what order to try things, and where each technique's full method lives under `Techniques/`.

## First Steps After a Foothold

Before enumerating, make the shell usable and record the context.

1. Stabilize the shell so history, tab completion, and job control work. See [Reverse Shells](/collections/oscp/reverse-shells).
2. Establish who and where:

```bash
id
whoami
hostname
uname -a
cat /etc/os-release
```

The OS matters immediately. It decides whether `/bin/sh` is bash or dash, which kernel exploits apply, and which default paths to check. Read the whole `id` line, not just the username: a supplementary group such as `disk`, `docker`, or `lxd` is a vector on its own, listed in [Linux Groups](/collections/oscp/linux-groups).

Every vector below is an access-control violation, so know the model it abuses. Users, groups, the `rwx` sets, SUID/SGID, and real/effective/saved UID are in [Linux Permissions](/collections/oscp/linux-permissions).

## Enumerate

Start with the manual basics; they are one command each and most often lead somewhere:

```bash
sudo -l                                  # allowed sudo commands
find / -perm -4000 -type f 2>/dev/null   # SUID binaries
getcap -r / 2>/dev/null                  # file capabilities
cat /etc/crontab; ls -la /etc/cron.*     # scheduled jobs
ls -la /home/* ; ls -la /var/www         # writable files and web roots
cat ~/.*history                          # passwords typed inline
alias ; cat ~/.bashrc                    # prepared credentialed shortcuts
cat /var/mail/$(whoami) 2>/dev/null      # credentials left in local mail
ss -tulnp                                # local-only services scans miss
```

The last three are cheap and easy to skip. `alias` and the shell rc files can hold a prepared credentialed command (the whole escalation on Boolean); `/var/mail/<user>` can hold a password an admin emailed (root's own on Plum, where a local Exim on `ss` was the hint); and `ss -tulnp` surfaces services bound to localhost, which are either an escalation target or something to forward with [Tunneling and Pivoting](/collections/oscp/tunneling-and-pivoting). All three are in [Credential Hunting](/collections/oscp/credential-hunting).

The SUID and capability sweeps return mostly stock entries, so read them against the baselines in [SUID Binaries](/collections/oscp/suid-binaries) and [Linux Capabilities](/collections/oscp/linux-capabilities) rather than chasing every line. Drop `/snap/` duplicates, treat anything outside the package directories as the finding, and version `pkexec`, `sudo`, and `snap-confine` even though they are baseline.

Then let a tool widen the net, reading all of the output. Order:

1. [linux-smart-enumeration](/collections/oscp/linux-smart-enumeration) first, at `-l1` or `-l2`: quiet, ranked, and readable over a raw shell.
2. [LinPEAS](/collections/oscp/linpeas) second, for the thorough sweep when the quiet pass came up empty. It flags findings by likelihood but spams heavily, so it is the deep cross-check rather than the opening move.
3. [LinEnum](/collections/oscp/linenum) in the same role, and for keyword credential hunting.

Run one, read it, and only reach for a second when it comes up empty. Save the output so it can be reviewed without rerunning:

```bash
./lse.sh -l1 | tee lse.txt
```

## Strategy

Enumeration produces more leads than can be chased, so work them deliberately.

- Try the short paths first. Sudo, cron, and SUID usually take the fewest steps, so check them before service or kernel exploits.
- Build a checklist per vector. Before committing to a method, write down what it needs (a writable file, a specific version, a `NOPASSWD` entry). If a precondition is missing, drop it. This is how to avoid rabbit holes.
- Read home directories and history. Look in the user's home, `/var/backups`, and `/var/log`, and read any history file for passwords or useful commands.
- Profile root processes. Version each one and search for exploits.
- Check internal ports. Services bound to localhost may be forwardable to Kali. See [Tunneling and Pivoting](/collections/oscp/tunneling-and-pivoting).
- Kernel last. If nothing else lands, reread the full enumeration dumps and highlight anything unfamiliar (an odd process or filename, a non-standard filesystem, a stray username), then consider a kernel exploit.

Every promising finding needs a concrete next action. A SUID binary that is not exploitable is a dead end, not a task.

## Vectors

Ordered roughly by what to try first (fewest steps, most reliable) to last (noisiest). Each links to its full method.

1. **Sudo rights** ([Sudo](/collections/oscp/sudo)). `sudo -l` is the first command. Any allowed program is a lead, through a GTFOBins shell escape, file read/write abuse, a preserved `LD_PRELOAD`, or an old `sudo` CVE.
2. **Group membership** ([Linux Groups](/collections/oscp/linux-groups)). Free, since `id` has already run. `disk` reads the raw block device with `debugfs`, which hands over `/etc/shadow` and root's keys, and was the whole escalation on Extplorer; `docker` and `lxd` mount the host filesystem as root.
3. **Scheduled jobs** ([Cron Jobs](/collections/oscp/cron-jobs)). A root job that runs a writable script, a bare command name resolved through a writable `PATH`, or a wildcard expanded in a writable directory. Empty readable crontabs do not rule this out: a job in root's own crontab is unreadable, so when a script clearly exists to be run by root, watch the process list with [pspy](/collections/oscp/pspy) instead of trusting `cat /etc/crontab`. Sar used a writable script pulled by a root cron job. Match the payload to the interpreter, since a `#!/bin/sh` job runs under dash where `>&` fails; see [Reverse Shells](/collections/oscp/reverse-shells). A job that processes files from a writable directory counts even when nothing in its command chain is writable: version the tool it runs, which is how Exfiltrated fell to [ExifTool DjVu Injection](/collections/oscp/exiftool-djvu-injection).
4. **SUID / SGID binaries** ([SUID Binaries](/collections/oscp/suid-binaries)). A GTFOBins one-liner, a known CVE in the binary, shared object injection, `PATH` abuse of a relative call, or bash function / `PS4` tricks. InfoSecPrep used SUID `bash -p`.
5. **File capabilities** ([Linux Capabilities](/collections/oscp/linux-capabilities)). A binary with `cap_setuid`, `cap_dac_read_search`, or similar is a root primitive without a SUID bit. `getcap -r /` finds them; Levram used `cap_setuid` on python3.
6. **Weak file permissions** ([Weak File Permissions](/collections/oscp/weak-file-permissions)). Loose perms on `/etc/shadow` (crack) or `/etc/passwd` (inject a UID-0 user), plus backups and stray keys in `/var/backups` and elsewhere.
7. **Credentials at rest** ([Credential Hunting](/collections/oscp/credential-hunting)). Passwords in history files, config files, and scripts, reused for root. Pebbles took the MySQL root password from the ZoneMinder config. A leaked DB-root plus `mysqld` as OS root escalates through [MySQL Privilege Escalation](/collections/oscp/mysql-privilege-escalation).
8. **Service exploits** ([Service Exploits](/collections/oscp/service-exploits)). A vulnerable service running as root. Version each root process and search Searchsploit/GitHub.
9. **NFS no_root_squash** ([NFS no_root_squash](/collections/oscp/nfs-no-root-squash)). A writable export with `no_root_squash` lets a SUID root binary be planted from Kali and run on the target.
10. **Kernel exploits** ([Kernel Exploits](/collections/oscp/kernel-exploits)). Last, because they are noisy and can panic the box. Loly was built around a `4.4.0` kernel exploit. Rank the candidates with [linux-exploit-suggester](/collections/oscp/linux-exploit-suggester) rather than picking off a `searchsploit` list.

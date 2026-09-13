---
title: "Credential Hunting"
slug: credential-hunting
category: notes
handbook: oscp
tags: ["credentials", "linux"]
draft: false
pubDatetime: 2026-07-19T23:38:46+03:00
modDatetime: 2026-09-09T21:52:45+03:00
description: "A password reused by root is one of the cheapest escalations there is."
---
A password reused by root is one of the cheapest escalations there is. Root's own password is hashed in `/etc/shadow`, but the passwords services need, and the commands admins type, often sit in plaintext in history files, config files, and scripts. Admins reuse passwords, so any password found is worth trying against `su root`. This is the concrete work behind the "credentials at rest" step of [Privilege Escalation](/collections/oscp/privilege-escalation-linux), and it overlaps with [Weak File Permissions](/collections/oscp/weak-file-permissions) (loose perms on the auth files themselves).

## History Files

A password typed inline on a command line gets logged to that program's history:

```bash
cat ~/.*history | less        # .bash_history, .mysql_history, .psql_history, ...
```

A line like `mysql -h somehost -uroot -ppassword123` gives a password to try. Read other users' histories too where they are readable.

### Aliases and login scripts

The same dotfiles that hold history also hold whatever the account holder prepared for themselves. Run `alias` and read the shell startup files:

```bash
alias
cat ~/.bashrc ~/.bash_aliases ~/.profile ~/.bash_profile ~/.zshrc 2>/dev/null
```

An alias or an exported variable can embed a credential or a whole credentialed command. On Boolean the escalation was a single line in remi's environment, `alias root='ssh -l root -i ~/.ssh/keys/root 127.0.0.1'`, which named the key, the target, and the loopback-only restriction all at once; running `alias` was the entire privesc. Exported passwords (`export DB_PASS=...`) and `PROMPT_COMMAND`/`PS1` hooks are the same find. This runs for free after a foothold, before any enumeration script.

## Config Files

Services store the credentials they authenticate with, usually in cleartext:

```bash
grep -riE "password|passwd|pass=|secret|api[_-]?key" /etc /home /var/www 2>/dev/null
```

The course example is an OpenVPN profile whose `auth-user-pass /etc/openvpn/auth.txt` points at a plaintext credentials file:

```bash
cat myvpn.ovpn            # ... auth-user-pass /etc/openvpn/auth.txt
cat /etc/openvpn/auth.txt # root \n password123
su root                   # reuse it
```

Other common homes: `wp-config.php`, `settings.py`, `.env`, database dumps, mail and backup configs. When the leaked credential is a database root and the daemon runs as OS root, escalate through [MySQL Privilege Escalation](/collections/oscp/mysql-privilege-escalation) instead of `su`.

An application that keeps its own account list in a file rather than a database is the same find with hashes instead of cleartext, and the file is usually a dotfile beside the config: eXtplorer's `config/.htusers.php` on Extplorer held an MD5 and a bcrypt in a PHP array. Read the usernames before the hashes. A name that also appears in `/etc/passwd` turns an application password into a system password, which is what makes cracking it worth the wait.

One hit is not the end of the search. The same config file often exists more than once in an application tree, in a subdirectory, a backup module, an installer copy, and the duplicates hold different values. On Sea two `database.php` files shared the same `$hidden_creds` shape: the one under the renamed admin directory held the low-privileged user that a leaked log pointed at, and the one at the docroot root held root. Read the whole output of a config sweep and compare the copies against each other rather than stopping at the first result. The same applies to the path: once one file in a directory turns out to be readable over HTTP, walk up and request its siblings.

The variable names matter as much as the values. `ssh_user`/`ssh_password` states which service the credential belongs to and skips the usual round of spraying it at everything, while `$cfg_mb_pwdmin` or `$cfg_mb_pwdtype` in the same sweep are password *policy* settings and not credentials at all.

### Configs read without a shell

The same files are often reachable before a foothold, through an exposed `.git` ([git-dumper](/collections/oscp/git-dumper)), a backup archive left in the web root, or [File Inclusion](/collections/oscp/file-inclusion). Two things change when the config arrives that early:

- The account to try the password on is the application's own admin login, not `root`. On bullyBox the `bb-config.php` database password was also the BoxBilling admin password, which was the one thing the authenticated RCE needed.
- Commit metadata is a username source. `git log` gives the author name and email of whoever deployed the app, and that address is usually a real account in it.

An app config also names the paths and prefixes worth requesting directly, such as an `admin_area_prefix` pointing at a panel that fuzzing may not reach.

### Backup archives of home directories

A web-exposed directory of per-user archives is a different find from a leaked app config, because it carries private SSH keys and shell dotfiles rather than database strings. The filenames are also a user list obtained without touching SMB or LDAP.

Read the sizes in the listing before downloading anything. A skeleton home directory is `.bashrc`, `.profile` and `.bash_logout`, which compresses to a fixed few kilobytes, so archives that all sit within tens of bytes of each other hold nothing but the skeleton and the one that is several times larger is the one with files in it. On Sorcerer three archives were 2818 to 2834 bytes and the fourth was 8274, which pointed at the account holding an SSH key pair and a `tomcat-users.xml.bak` before a single `unzip`.

List the archive rather than unpacking and running `ls`:

```bash
unzip -l max.zip
tar tzf max.tar.gz
```

Everything worth having in a home directory is a dotfile, and a plain `ls` on the unpacked result hides all of them. On Sorcerer that turned a directory containing `.ssh/id_rsa` into an apparent two-file archive and sent the box down the wrong branch for a while. Use `unzip -l` before unpacking, or `ls -la` after, and never a bare `ls`.

A key recovered this way arrives with the archive's stored permissions and will be ignored by `ssh` until it is `chmod 600` ([SSH Key Access](/collections/oscp/ssh-key-access#log-in)).

## Local Mail

A box that runs a local MTA delivers mail to per-user spool files, and admins leave passwords in them. The tell is a mail daemon (Exim, Postfix, sendmail) bound to `127.0.0.1:25` in `netstat -tunlnp`, which external scans never see. Read the current user's spool first, then any other readable one:

```bash
ls -la /var/mail /var/spool/mail        # /var/mail/<user>, often symlinked from /var/spool/mail
cat /var/mail/$(whoami)
```

On Plum there were no sudo rights, no unusual SUID, and no database to loot (a flat-file CMS), so the usual passes came up empty. `/var/mail/www-data` held a message from root, "URGENT - DDOS ATTACK", handing over the root password in cleartext, which SSH accepted directly. When the standard escalations produce nothing, the mail spool is a cheap check that the enumeration scripts do not surface prominently.

## Network Captures

A `.pcap` handed over in a lab, or captured with `tcpdump`/`Wireshark` from a compromised host, is credentials in motion instead of credentials at rest. Anything that travels cleartext on the wire is readable from the capture: FTP, Telnet, HTTP basic auth and form logins, SNMP community strings, SMTP AUTH, POP3/IMAP logins, and LDAP simple binds.

```bash
tshark -r capture.pcap -Y 'http.request or ftp.request.command == "PASS"'   # quick protocol filter
strings -n 8 capture.pcap | grep -iE 'pass(word)?|login|authorization'       # blunt fallback
```

In Wireshark the same work is manual: apply a protocol display filter, follow the TCP stream on anything interesting (`Analyze > Follow > TCP Stream`), and pull the credential from the request. On a lab capture with mixed traffic, follow each TCP/system conversation and read the human messages too; credentials are sent by users in chat or mail as often as by protocols. Dropped or seen-once credentials then feed back through spraying ([Password Spraying](/collections/oscp/password-spraying)) like any found password.

## SSH Keys

A readable private key is a login as its owner. Hunt for keys left where they should not be:

```bash
find / \( -name "id_*" -o -name "*.pem" -o -name "*_key" \) 2>/dev/null
ls -la /.ssh /home/*/.ssh 2>/dev/null
```

The world-readable root key case is worked in [Weak File Permissions](/collections/oscp/weak-file-permissions): copy it to Kali, `chmod 600`, confirm `PermitRootLogin`, then `ssh -i key root@TARGET`.

## Process Memory

A secret a program read or was handed at runtime sits in its address space in cleartext, even when it never lands on disk that way: a password typed at a login prompt, a token loaded from a vault, the database credential a daemon authenticated with. A process still running is a source, so dumping its memory and grepping the dump pulls the string back out.

Dumping another user's process needs the right to attach to it (ptrace). That comes from running the dumper as root (a `sudo -l` entry for `gcore` or `gdb`), from `cap_sys_ptrace` on a binary ([Linux Capabilities](/collections/oscp/linux-capabilities)), or from the target being a process the current user already owns when `/proc/sys/kernel/yama/ptrace_scope` allows it.

Pick a PID likely to hold a credential, dump it, and search:

```bash
ps -eo pid,user,command           # a service that authenticates, or an auth process mid-login
sudo gcore -o /tmp/dump <pid>     # writes /tmp/dump.<pid>
strings -n 6 /tmp/dump.<pid> | grep -iE 'pass|pwd|secret|token'
```

`gcore` pauses the process only for the snapshot, but the dump is large and the credential can sit anywhere in it, so widen the search (`-A2 -B2`, shorter `-n`) rather than trusting one keyword. Good targets are a web app worker, a database client, a custom daemon, or an authentication process caught while a password is being entered. A process named for what it holds is the obvious pick: on Pelican a root `/usr/bin/password-store` was allowed to be dumped through a sudo `gcore` rule, and paging the core with `strings | less` (the keyword `grep` came back thin) surfaced a `001 Password: root:` line holding root's own password. Skip system plumbing whose memory is certificates and tokens rather than human passwords: the wasted attempt there was dumping VMware's `VGAuthService`, whose core is gibberish for this purpose. gcore reports a saved core on any live PID, so confirm what a process actually is in `ps` before spending a dump on it.

`/proc/<pid>/environ` is the cheaper first look when the secret was passed as an environment variable, needing only read access to the file and no dump at all:

```bash
sudo cat /proc/<pid>/environ | tr '\0' '\n' | grep -i pass
```

Reuse whatever comes out with `su` and against every service login, as below.

## Always Try su

For every password or hash found, test it before moving on:

```bash
su root        # or su <user>
```

`su` reads the password from a terminal. From a raw shell with no TTY it fails with `must be run from a terminal`, which reads like a wrong password and is not, so upgrade the shell first ([Reverse Shells](/collections/oscp/reverse-shells)).

Do not stop at the service it came from. A password that a publickey-only SSH rejects may still authenticate an admin console that binds to system accounts, which is a shell and a key-write from there. On Cockpit the SQLi leaked a password that SSH would not take, and it logged straight into Cockpit on 9090 as the same system user. See [SSH Key Access](/collections/oscp/ssh-key-access). With a foothold already open the same rejection matters less: on Extplorer the cracked password went nowhere over SSH and straight through `su` from the `www-data` shell.

Password reuse across accounts and services is the whole premise. A service password is worth trying as the root password, and the reverse.

### A correct password still refusing a shell

`su` checks the password before it looks at the account's shell, so the two failure modes tell different things apart. `su: Authentication failure` means the password was wrong. `This account is currently not available.` means authentication succeeded and `su` handed off to the account's configured shell, which is `/usr/sbin/nologin`, and that binary just prints this line and exits. Reaching the second message is confirmation a reused password was correct, not a dead end to write off as a wrong guess:

```
$ su zabbix
Password:
This account is currently not available.
```

A service account with `nologin` cannot be reached this way at all, `-s /bin/bash` does not help either, since `su` only honors a shell override from the caller when the caller is already root; from any other account it silently falls back to the account's own `nologin` shell. On Zab the zabbix system account's password matched the one leaked from the Zabbix web config, correctly predicting reuse, but the account itself stayed unreachable until a different route (the Zabbix web application, not `su`) gave a shell as that same user.

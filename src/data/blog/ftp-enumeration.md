---
title: "FTP Enumeration"
slug: ftp-enumeration
category: notes
handbook: oscp
tags: ["ftp", "enumeration"]
draft: false
pubDatetime: 2026-07-21T21:42:14+03:00
modDatetime: 2026-09-13T20:51:50+03:00
description: "FTP on 21 is worth three checks: the version banner for a known exploit, anonymous access for readable or writable files, and whether an upload directory doubles as a web root."
---
FTP on 21 is worth three checks: the version banner for a known exploit, anonymous access for readable or writable files, and whether an upload directory doubles as a web root. Anonymous login succeeding is not the same as FTP being a path, and a hung directory listing is usually a data-channel problem, not a dead service.

## Banner and Version

The banner prints on connect and is the first lead. Search it before anything else:

```bash
nc TARGET 21
# 220 (vsFTPd 3.0.2)
searchsploit vsftpd
```

The classic hit is **vsftpd 2.3.4**, which ships a backdoor (CVE-2011-2523): a username ending in `:)` opens a root shell on port 6200. Version 3.0.2 (on Snookums) is not vulnerable, so the banner ruled that out immediately. ProFTPD and other daemons have their own version-bound bugs, so the banner decides whether there is an exploit at all.

## Anonymous Login

```bash
ftp TARGET
# Name: anonymous
# Password: (anything, e.g. anonymous)
```

`230 Login successful` means anonymous read is allowed. That only covers the control channel on 21, so login works even when listing does not.

### 534 Policy requires SSL (Microsoft FTP)

Microsoft FTP Service can answer every login with `534 Policy requires SSL`, rejecting credentials at the policy layer before checking them. Test whether the server actually offers TLS before writing the port off:

```text
lftp TARGET
lftp TARGET:~> set ftp:ssl-force true
lftp TARGET:~> set ftp:ssl-protect-data true
lftp TARGET:~> login anonymous
```

`ftp:ssl-force is set and server does not support or allow SSL` closes the loop: policy demands TLS, the server offers none, so no credential will ever authenticate. Seen on Billyboss. Confirm once and move on; further probing is wasted.

## The Data-Channel Hang

FTP uses two connections: the **control channel** on 21 for commands, and a **separate data channel** on another port for every `LIST` and `RETR`. When login works but `ls`/`dir` hangs, the data channel is the problem, not the login.

```text
ftp> ls
229 Entering Extended Passive Mode (|||38246|).   # then hangs
```

- **Passive mode**: the server opens a high random port and the client connects out to it. This hangs when the target firewall permits only 21 inbound and drops the high passive ports.
- **Active mode** (`passive` to toggle off): the server connects back to the client's data port. This hangs when the client bound the data socket to the wrong interface (for example `eth0` instead of the VPN `tun0`), so the target has no route back.

On Snookums both directions hung, and LinPEAS later showed `iptables` active on the box, consistent with the passive ports being filtered. QuackerJack behaved the same way, anonymous login accepted and the listing hanging after the passive reply, and the box fell to a web application instead.

The fix is to stop fighting the interactive client and use `curl` or `wget`, which handle the data channel more reliably:

```bash
curl ftp://TARGET/ --user anonymous:anonymous        # directory listing
curl --disable-epsv ftp://TARGET/ --user anonymous:anonymous   # if EPSV specifically hangs
wget -m --no-passive-ftp ftp://user:pass@TARGET/               # mirror everything, active mode
```

## Transferring Files

Inside the interactive client:

```text
ftp> binary                 # before any non-text file
ftp> ls -la                 # dotfiles are hidden from a plain ls
ftp> cd pub
ftp> lcd /home/kali/loot    # where downloads land, defaults to the cwd ftp was launched from
ftp> get config.php
ftp> get config.php /tmp/config.php    # rename on the way down
ftp> prompt off             # stop the per-file y/n confirmation
ftp> mget *                 # everything in this directory
ftp> put shell.php          # upload, if the share is writable
ftp> !ls                    # run a local command without leaving the session
ftp> exit
```

`binary` is the one that bites. Several clients default to ASCII mode, which rewrites line endings in transit and silently corrupts anything that is not text: an archive fails to unpack, an executable will not run, a hash of the file will not match. Set it before any `get` that is not plain text, and treat a downloaded file that is subtly the wrong size as a missing `binary` rather than a bad file on the server.

`mget *` covers one directory only. It does not recurse and does not expand to dotfiles, so a share with nested folders needs a mirror.

Outside the client:

```bash
wget -m --no-passive-ftp ftp://anonymous:anonymous@TARGET/    # mirror everything, active mode
wget -m ftp://user:pass@TARGET/                               # passive, the default
curl -O ftp://TARGET/config.php --user anonymous:anonymous    # single file
curl -T shell.php ftp://TARGET/ --user anonymous:anonymous    # upload
```

`wget -m` is the fastest way to pull an entire anonymous share onto disk with recursion handled, and it avoids the interactive client's transfer mode and prompting entirely. It reads the same `LIST` output the client does, so anything hidden from a plain listing stays hidden and still needs `ls -la` in the client to spot.

### 550 on a file that is visible

Listing a directory and reading a file in it are separate permissions, so a name appears in `ls -la` while `get` returns `550 Failed to open file`. The columns say why:

```text
drwxr-xr-x  2 0     0     4096  .                    # world-readable directory, hence the name is visible
-r--------  1 33    33     170  .fuhfjkzbdsfuybe...  # mode 400, owner UID 33, no group or world bits
-rwxr-xr-x  1 0     0     5436  control-panel.php    # world-readable, downloads fine
drwxr-xr-x  4 1002  1002  4096  ..                   # the login account's own home
```

The daemon opens the file as the account that logged in, so a 550 means that UID does not satisfy the mode. Retrying through `curl ftp://` or `wget` changes nothing, because the denial happens on the server's filesystem after authentication.

The numeric owner is what turns this from a dead end into a lead. UID 33 is `www-data` on Debian and Ubuntu, meaning the web server can read a file the FTP session cannot. On SpiderSociety the FTP root was also the web root, the same `index.html`, `images/` and application directory in both views, so the file sat under a URL and Apache served it as the user who owned it:

```bash
curl http://TARGET/libspider/.fuhfjkzbdsfuybefzmdbbzdcbhjzdbcukbdvbsdvuibdvnbdvenv
```

That returned the SSH credentials the FTP account was never allowed to read. Compare the FTP listing against the site before assuming a file needs an exploit to reach: when the two trees match, every FTP path is also a URL, and the web server's identity is a second set of permissions to read through. If the roots are not shared, the owner still names who can read it, which makes the file a target for a file-read primitive in whatever runs as that user, see [File Inclusion](/collections/oscp/file-inclusion).

A deliberately unguessable filename combined with mode 400 is a marker, not an accident. The name is meant to be found by listing and the contents fetched some other way.

## What to Look For

- **Readable files**: credentials, configs, keys, source.
- **Writable upload**: `anon_upload_enable` on. If the FTP root is also a web root (`/var/www`), upload a webshell and browse to it, which turns FTP into code execution. See [Webshells](/collections/oscp/webshells) and [Reverse Shells](/collections/oscp/reverse-shells).
- **Log files**: an application log left in an anonymous share leaks the install layout for free, since error messages carry absolute paths (`/var/www/SeaCMS/th4o4p/database.php` named the product, the docroot, and a renamed admin directory on Sea). Expect the bulk of a planted log to be manufactured noise with one real line in it, and expect the plausible-looking lines to be the decoys: a traversal-shaped `?id=../etc/passwd` was filler while a routine-sounding warning about a password "exposed in request" was the path. Grep for URLs and parameters, then request them.
- **Account metadata**: an anonymous listing can expose usernames even when the account files are unreadable. On AuthBy, zFTPServer's `accounts` filenames gave `admin` and `offsec`, enough to target FTP instead of guessing the Basic Auth prompt. See [Brute Forcing Logins](/collections/oscp/brute-forcing-logins).
- **Directory names as an application fingerprint**: the listing can name the installed software even with nothing worth downloading. On Algernon anonymous FTP exposed `ImapRetrieval`, `PopRetrieval`, and `Spool`, which are SmarterMail's own working directories, so the FTP root identified the product and pointed at its web service (SmarterMail on 9998) before that interface had been located. Read unfamiliar directory names as a product tell, then look up the version and its CVE.

If anonymous login works but the share is empty and there is no upload, note it and move on. Anonymous FTP is frequently a rabbit hole, and the intended path is usually another service.

## Where This Sits

FTP is one line in the attack-surface table from [Information Gathering](/collections/oscp/information-gathering). Credentials found here feed [Credential Hunting](/collections/oscp/credential-hunting); a writable web root feeds [File Inclusion](/collections/oscp/file-inclusion) or a direct webshell.

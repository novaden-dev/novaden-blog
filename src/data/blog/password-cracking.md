---
title: "Password Cracking"
slug: password-cracking
category: notes
handbook: oscp
tags: ["password-attacks"]
draft: false
pubDatetime: 2026-07-22T21:58:53+03:00
modDatetime: 2026-09-13T19:42:38+03:00
description: "Offline recovery of a password from a captured artifact: a protected file, an encrypted key, or a hash."
---
Offline recovery of a password from a captured artifact: a protected file, an encrypted key, or a hash. The `*2john` helpers turn a protected file into a hash, then [john](/collections/oscp/john) or [hashcat](/collections/oscp/hashcat) runs a wordlist against it. This is for a specific artifact already in hand, not online guessing against a live service, which is [Brute Forcing Logins](/collections/oscp/brute-forcing-logins).

## Identifying the hash type

A raw hash lifted from a database dump, `/etc/shadow`, or a config file has to be identified before a mode can be chosen. Hashes in Modular Crypt Format carry a `$id$` prefix that names the algorithm:

| Prefix | Algorithm | hashcat -m |
| --- | --- | --- |
| `$1$` | MD5 crypt | 500 |
| `$apr1$` | Apache MD5 crypt | 1600 |
| `$2a$` `$2b$` `$2y$` | bcrypt | 3200 |
| `$5$` | SHA-256 crypt | 7400 |
| `$6$` | SHA-512 crypt | 1800 |
| `$y$` | yescrypt | not supported |

A bcrypt hash is a fixed 60 characters, `$2a$` then the cost factor, then a 22 character salt and a 31 character digest, using bcrypt's own base64 alphabet that includes `.` and `/`:

```
$2a$08$NxmF1vhrsnMypsJ1fJkR5OyxtBLWDChyHS4sAT.6ue6SyR2rbmFvS
 |   |  \_____ 22 char salt _____/\______ 31 char hash ______/
 |   cost factor 2^8
 bcrypt
```

Bare hashes with no prefix are identified by length and character set: 32 hex is MD5 or NTLM, 40 hex is SHA-1, 64 hex is SHA-256. Tools that guess it:

```bash
hashid '$2a$08$Nxm...'          # candidate types from the prefix
nth -t '$2a$08$Nxm...'          # name-that-hash, ranks likely modes
hashcat --identify hash.txt     # prints the matching -m modes
```

Dumps often come from [Database Enumeration](/collections/oscp/database-enumeration) or [Credential Hunting](/collections/oscp/credential-hunting). Save one hash per line into a file before cracking.

Apache `.htpasswd` entries commonly use `$apr1$salt$digest`. This is an Apache variant of MD5 crypt; john labels it `md5crypt` and accepts the full `user:hash` line. Hashcat uses mode `1600` for it rather than the generic `$1$` mode. AuthBy used this format to recover the Basic Auth password.

## Protected files to a hash

The `*2john` scripts ship with john and extract a crackable hash from a file:

```bash
pdf2john infrastructure.pdf > pdf.hash      # PDF
zip2john secret.zip        > zip.hash       # ZIP
office2john report.docx    > office.hash    # Word, Excel, PowerPoint
ssh2john id_rsa            > key.hash       # passphrase-protected SSH key
keepass2john Database.kdbx > kp.hash        # KeePass
```

## Crack with john

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt pdf.hash
john --wordlist=/usr/share/wordlists/rockyou.txt --rules=best64 pdf.hash
john --show pdf.hash
```

`--rules=best64` applies common mutations to each word, appended digits, capitalization, leetspeak, so it catches passwords that are variations of a wordlist entry rather than an exact match. On Nickel `infrastructure.pdf` cracked to a mutated word this way, where a plain run missed it. `--show` reprints recovered passwords from the pot file after a run.

A raw hash from a dump or `/etc/shadow` skips the `*2john` step, john reads it straight from the file, auto-detects the type, and needs no GPU or OpenCL backend. `--format=bcrypt` forces the type when detection is ambiguous.

With both system files in hand, `unshadow` merges them so each hash carries its username, and john reports which account cracked instead of a bare line number:

```bash
unshadow passwd.txt shadow.txt > creds.txt
john --wordlist=/usr/share/wordlists/rockyou.txt creds.txt
```

Accounts with `*` or `!` in the password field have no password set and are skipped. Ways to obtain the two files are in [Weak File Permissions](/collections/oscp/weak-file-permissions) and [Linux Groups](/collections/oscp/linux-groups).

## Crack with hashcat

hashcat is faster on a GPU and takes the same hash with an explicit mode number:

```bash
hashcat -m 10500 pdf.hash /usr/share/wordlists/rockyou.txt   # PDF 1.4 - 1.6
hashcat -m 13400 kp.hash  /usr/share/wordlists/rockyou.txt   # KeePass
hashcat -m 3200  db.hash  /usr/share/wordlists/rockyou.txt   # bcrypt
hashcat --show -m 10500 pdf.hash
```

john auto-detects the format, hashcat needs the mode. `hashcat --help | grep -i <format>` finds the right `-m`.

On a Kali VM with no GPU, hashcat exits at once with `No OpenCL, HIP or CUDA compatible platform found`. The backend problem and the CPU-runtime options are in [hashcat](/collections/oscp/hashcat). john needs no backend, so it is the default for a single hash on the VM, even though CPU-speed bcrypt is the ceiling either way.

## yescrypt

`$y$` is the default shadow hash on Ubuntu 22.04 and later, and it is the one entry in the table with no hashcat mode. yescrypt is memory-hard by design, which is exactly what defeats the GPU parallelism hashcat exists for, so there is no `-m` to look for. john takes it through the system's libcrypt:

```bash
john --format=crypt --fork=4 --wordlist=/usr/share/wordlists/rockyou.txt root.hash
john --show --format=crypt root.hash
```

`--format=crypt` is CPU-bound and single-threaded without `--fork`, so set it to the core count. `john --test --format=crypt` prints the rate before committing to a run, and it lands in the low hundreds of hashes per second, meaning a full rockyou pass is hours rather than minutes.

Because rockyou is ordered by frequency, a weak password falls in the first few minutes or usually not at all. Start the run in a tmux pane and keep enumerating rather than waiting on it. On Ochima the root hash came out of a readable `/etc` backup, never cracked, and the box fell to the cron job that wrote the backup instead.

## Online lookups for unsalted hashes

A bare MD5, SHA-1 or NTLM has no salt, so the same password always produces the same digest and someone has already computed it. Pasting it into hashes.com or crackstation answers in seconds where a local run still has to work through rockyou. On QuackerJack the rConfig admin's 32 hex characters came back instantly.

## Notes

- Keep the filename the `*2john` output was built from, so `--show` maps the crack back to it.
- `No password hashes loaded` means the helper does not support that file or the file is not actually encrypted.
- A recovered password is worth trying elsewhere, since reuse is common. See [Credential Hunting](/collections/oscp/credential-hunting).
- Before starting a run, name what the password opens that is not open already. An application's own admin hash is worth little once that application is already executing commands: on ZenPhoto the `zp_administrators` hash was worked long after the RCE had made the admin panel redundant. A hash for a system account, a reused password, or a service on another port is the one that pays.
- bcrypt is deliberately slow, so a full rockyou run against a `$2a$` hash takes far longer than a fast hash like MD5. The cost factor after the second `$` sets how slow. It does not decide whether the hash falls, only the price per candidate: a `$2a$08$` hash cracked in two seconds on Extplorer because the password sat near the front of rockyou, while the same cost on Codo never cracked. Start the run before writing a hash off.
- A value in a password column that does not match the length or character set of any hash is probably plaintext, not something to crack. On Codo the `anonymous` account stored a plaintext taunt where a hash would be.

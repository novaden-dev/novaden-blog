---
title: "Base64 and Encodings"
slug: base64-and-encodings
category: notes
handbook: oscp
tags: ["encoding"]
draft: false
pubDatetime: 2026-07-18T17:48:53+03:00
modDatetime: 2026-09-13T18:05:53+03:00
description: "Encoded data shows up constantly: in files left on web servers, in config values, in tokens."
---
Encoded data shows up constantly: in files left on web servers, in config values, in tokens. The first job is to recognise the encoding, the second is to recognise what the decoded bytes are.

## Recognise Base64

- Character set of `A-Z a-z 0-9 + /`, often ending in one or two `=` padding characters.
- Length is a multiple of 4 once padding is included.

The `==` at the end of InfoSecPrep's `secret.txt` was the first tell that it was base64.

## Decode

```bash
# from a file
base64 -d secret.txt

# from a string
echo 'aGVsbG8=' | base64 -d
```

For unknown or layered encodings, CyberChef with the *Magic* operation detects the scheme and can chain decoders. It was what confirmed the InfoSecPrep key.

## Recognise the Decoded Content by Its Prefix

A base64 string encodes the same leading bytes every time, so the start of the base64 reveals what the decoded data is without decoding it:

| Base64 starts with | Decodes to | Meaning |
|---|---|---|
| `LS0tLS1CRUdJTi` | `-----BEGIN` | A PEM block (key or certificate) |
| `LS0tLS1CRUdJTiBPUEVOU1NI` | `-----BEGIN OPENSSH` | OpenSSH private key |
| `LS0tLS1CRUdJTiBSU0E` | `-----BEGIN RSA` | RSA private key |
| `H4sI` | gzip magic bytes | gzip-compressed data |
| `UEsDBA` | `PK\x03\x04` | ZIP archive |
| `/9j/` | JPEG magic bytes | JPEG image |
| `iVBORw0KGgo` | PNG magic bytes | PNG image |

On InfoSecPrep the blob started `LS0tLS1CRUdJTiBPUEVOU1NI`, so it was an OpenSSH private key before decoding it. A private key plus an open SSH port is a login, covered in InfoSecPrep.

## After Decoding a Key

Save the decoded key, tighten permissions, and log in:

```bash
base64 -d secret.txt > id_rsa
chmod 600 id_rsa
ssh -i id_rsa user@target
```

SSH ignores a private key that others can read, so `chmod 600` before use.

## Encoded Credentials, Not Hashes

Application databases sometimes store passwords base64-encoded instead of hashed. Base64 is reversible, so decode it rather than sending it to John. A stored value made only of `A-Z a-z 0-9 + /` with `=` padding is the tell that it is encoding, not a hash (`$1$`, `$6$`, `$2b$` prefixes mark a hash). On Snookums the `users` table held base64 values, and decoding michael's gave his cleartext password, reused directly for SSH.

```bash
echo 'U0c5a...' | base64 -d
```

If one decode still looks like base64 (same character set and padding), decode again. Layered base64 is common.

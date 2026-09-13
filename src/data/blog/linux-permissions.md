---
title: "Linux Permissions"
slug: linux-permissions
category: notes
handbook: oscp
tags: ["linux", "privilege-escalation"]
draft: false
pubDatetime: 2026-07-19T23:38:46+03:00
modDatetime: 2026-09-13T18:05:23+03:00
description: "Every Linux privilege escalation is an access-control violation, and access control in Linux is built on permissions."
---
Every Linux privilege escalation is an access-control violation, and access control in Linux is built on permissions. Knowing the model that a vector abuses comes before the vector itself: how users, groups, and files relate, and how the kernel decides who can do what. This is the theory that [Privilege Escalation](/collections/oscp/privilege-escalation-linux) and [SUID Binaries](/collections/oscp/suid-binaries) rely on.

The goal of privesc is a shell running as root (UID 0), the account the kernel grants access to every file. A single misconfiguration sometimes reaches it. More often several small ones combine, and spotting them means reading permissions correctly.

## Users, Groups, Files

Permissions are a relationship between three things.

- Users: configured in `/etc/passwd`, password hashes in `/etc/shadow`. Each user has an integer UID. Root is UID 0, and that number, not the name, is what makes it root.
- Groups: configured in `/etc/group`. A user has one primary group (by default named after the account) and any number of supplementary groups. Users belong to many groups, groups hold many users.
- Files and directories: each has a single owner and a single group. Permissions are defined in three sets: owner, group, and other (everyone else, also called world). Only the owner can change a file's permissions.

These three files are the first to read after a foothold. `/etc/passwd` for accounts, `/etc/group` for group membership, `/etc/shadow` if it is readable (a finding in itself).

## Reading Permission Strings

`ls -l` prints the mode as ten characters:

```text
$ ls -l /bin/date
-rwxr-xr-x 1 root root 60416 Apr 28  2010 /bin/date
```

Character 1 is the type: `-` file, `d` directory, `l` symlink. The next 9 are three sets of `rwx` for owner, group, and other:

```text
- rwx r-x r-x
│ │   │   └ other:  r-x
│ │   └────── group:  r-x
│ └────────── owner:  rwx
└──────────── type:   file
```

A set can also be written numerically: `r=4 w=2 x=1` summed per set, so `rwxr-xr-x` is `755`. Useful when running `chmod` during an escalation.

## File vs Directory Permissions

The same three bits mean different things depending on the target.

Files:

- read: the contents can be read.
- write: the contents can be modified.
- execute: the file can be run as a process.

Directories:

- execute: the directory can be entered (`cd`). Without it, neither read nor write does anything, so execute is the prerequisite.
- read: the directory listing can be read (`ls`).
- write: files can be created, renamed, and deleted inside it.

The directory rules matter for privesc. Write on a directory allows deleting or replacing files owned by another user inside it, which is how a writable directory holding a root-run script becomes an escalation. See [Cron Jobs](/collections/oscp/cron-jobs), and Walla for the sudo version, where a `root:root 644` script could not be edited but could be deleted and rewritten because the web user owned the home directory it sat in. A file that cannot be written is not a closed door until `ls -ld` on its parent says so.

## Special Permissions

Beyond `rwx`, three bits change execution and inheritance. They appear in the execute position of a set as `s`, `s`, and `t` respectively (uppercase if the underlying execute bit is off).

- setuid (SUID): on a file, it runs with the effective UID of its owner, not the caller. When the owner is root and the binary can run code or read files, that is a direct escalation. Shows as `s` in the owner set: `-rwsr-xr-x`. This is the subject of [SUID Binaries](/collections/oscp/suid-binaries).
- setgid (SGID): on a file, it runs with the file's group. On a directory, new files created inside inherit that directory's group instead of the creator's primary group. Shows as `s` in the group set.
- sticky bit: on a directory, only a file's owner can delete or rename it, even when the directory is world-writable (`/tmp` is the classic case). Shows as `t` in the other set: `drwxrwxrwt`.

Find SUID files with `find / -perm -4000 -type f 2>/dev/null`, the standard first sweep covered in [SUID Binaries](/collections/oscp/suid-binaries).

## Real, Effective, and Saved UID/GID

A user is identified by three IDs, not one, and knowing which is checked explains why SUID works.

- Real UID: the actual identity, the UID from `/etc/passwd`. Checked least often.
- Effective UID: used for most access-control decisions. Normally equal to the real UID, but running a SUID process sets it to the file owner's UID. `whoami` reports the effective UID, so a successful SUID abuse prints `root`.
- Saved UID: lets a SUID process drop its effective UID back to the real one and later restore it, without losing track of the elevated value.

Inspect them:

```bash
# effective IDs (id shows euid/egid only when they differ)
$ id
uid=1000(user) gid=1000(user) euid=0(root) egid=0(root) groups=0(root),...

# real, effective, saved, and filesystem IDs of the current shell
$ cat /proc/$$/status | grep '[UG]id'
Uid:    1000    0    0    0
Gid:    1000    0    0    0
#       real    eff  saved fs
```

`euid=0` while `uid=1000` means the process runs with root's effective identity, the state a SUID escalation aims to reach and keep.

## Why This Matters for Privesc

The permission model is what every Linux vector bends.

- SUID abuse works because the effective UID becomes the owner's. bash resets it back at startup unless launched with `-p`, which preserves the elevated effective UID, the mechanism behind InfoSecPrep's `bash -p`. Detail in [SUID Binaries](/collections/oscp/suid-binaries).
- Writable files run by root exploit directory and file write bits: if root runs a script that can be modified (or a script in a writable directory), that code runs as root. See [Cron Jobs](/collections/oscp/cron-jobs).
- Group membership from `/etc/group` can grant a path on its own (`docker`, `lxd`, `disk`, `adm`, `sudo`). These bypass the file bits entirely rather than bending them, since the access is to a device or a socket. See [Linux Groups](/collections/oscp/linux-groups).

Any escalation starts by establishing the current identity and reading what the target grants. The workflow is in [Privilege Escalation](/collections/oscp/privilege-escalation-linux).

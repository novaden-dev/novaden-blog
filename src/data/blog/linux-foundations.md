---
author: Kayra
pubDatetime: 2024-01-04T09:00:26Z
title: Linux Foundations
slug: linux-foundations
featured: false
draft: false
tags: ["linux"]
category: notes
description: The mental model behind Linux. Components, distributions, filesystem hierarchy, the shell, paths, redirection, and the permissions system.
---

## Introduction

Linux is an operating system, the same way Windows and macOS are. The difference is what's underneath: it's built around the Linux kernel, and most of the surrounding ecosystem is open source. In practice, that's what you'll find running most servers, containers, embedded devices, and the security tools you'll be working with.

## Core Components

A Linux system is made up of a few layered pieces:

- **Kernel**: the core of Linux. Manages hardware resources, memory, and system processes.
- **Daemons**: background services that handle things like scheduling, printing, and networking. They run without a user interface.
- **Shell**: the command-line interface (e.g. `bash`, `zsh`). It's how you issue commands to the operating system.
- **Graphics Server & Window Manager**: provides the graphical interface (e.g. GNOME, KDE). Optional, since many Linux servers run without a GUI at all.

## Distributions

A *distribution* (or "distro") is an operating system built on top of the Linux kernel, packaged with its own selection of utilities, package manager, default shell, and desktop environment. A few common ones:

- **Fedora**: sponsored by Red Hat. Gets new kernels and packages relatively quickly compared to long-term-support distros, so it's a good fit for desktop use. It's my current daily driver.
- **Ubuntu**: Debian-based, popular for both desktops and servers.
- **Kali**: Debian-based, ships preloaded with security and penetration-testing tools.

The kernel underneath is the same. What differs is the packaging, defaults, and philosophy.

## Filesystem Hierarchy

Linux organizes everything (files, devices, even processes) into a single tree rooted at `/`. Knowing what each top-level directory is *for* makes the system far easier to navigate.

| Path | Description |
| --- | --- |
| `/` | The root directory. Everything hangs off it. |
| `/bin` | Essential command binaries available to all users. |
| `/boot` | Bootloader files and kernel images. |
| `/dev` | Device files representing hardware. |
| `/etc` | System-wide configuration files. |
| `/home` | User home directories. |
| `/lib` | Shared libraries needed by `/bin` and `/sbin`. |
| `/media` | Mount points for removable media. |
| `/mnt` | Temporary mount point for manual mounts. |
| `/opt` | Optional or third-party software. |
| `/root` | Home directory for the root user. |
| `/sbin` | System administration binaries, mostly for root. |
| `/tmp` | Temporary files. Usually wiped on reboot. |
| `/usr` | User programs, libraries, and documentation. |
| `/var` | Variable data: logs, mail spools, caches. |

## The Shell

The shell is a text-based interface that lets you communicate directly with the operating system. The most common one is the **Bourne-Again Shell (BASH)**.

When you open a terminal, you'll see a prompt that looks something like this:

```text
kayra@fedora:~/SoulSiphon/PersonalWork/novaden-blog$
```

Breaking that down:

- `kayra`: the current user
- `fedora`: the hostname
- `~/SoulSiphon/PersonalWork/novaden-blog`: the current working directory (`~` is shorthand for the user's home)
- `$`: the prompt symbol, indicating an unprivileged user

When you're logged in as `root`, the prompt symbol changes to `#`:

```text
root@fedora:/home/kayra/SoulSiphon/PersonalWork/novaden-blog#
```

That single character is a useful safety cue. If you see `#`, you have full administrative privileges and can do real damage.

## Relative vs Absolute Paths

There are two ways to reference a file or directory:

- **Absolute path**: the full path starting from `/`. It works from anywhere on the system.
- **Relative path**: the path from your current working directory.

For example, `cd /opt/` will always land you in `/opt` regardless of where you are, because it's an absolute path. By contrast, `cd opt` only works if you're already sitting in `/`, since it's interpreted relative to wherever you are.

Two special symbols come up constantly in relative paths:

- `.`: the current directory
- `..`: the parent directory

## File Descriptors and Redirection

A **file descriptor (FD)** is a reference, maintained by the kernel, that lets the system manage input/output operations. Every process starts with three file descriptors by default:

| FD | Name | Purpose |
| --- | --- | --- |
| `0` | STDIN | Standard input. Data fed *into* a command. |
| `1` | STDOUT | Standard output. Regular output *from* a command. |
| `2` | STDERR | Standard error. Error messages. |

Because these are just numbered streams, you can redirect them independently. The shell uses `<` for input and `>` for output:

```bash
# Discard error messages
command 2>/dev/null

# Send stdout and stderr to separate files
command 1>stdout.txt 2>stderr.txt

# Feed a file in as stdin
cat < input.txt
```

> **Note:** When you use `>` to redirect output, the target file is created if it doesn't exist and **overwritten without warning** if it does. Use `>>` to append instead.

You can also chain commands together by piping STDOUT from one into STDIN of the next using `|`. This is how you stitch small Linux commands together into bigger workflows:

```bash
find /etc/ -name "*.conf" 2>/dev/null | grep systemd | wc -l
```

That one-liner finds every `.conf` file under `/etc/`, silently discards permission errors, filters for ones mentioning `systemd`, and counts the results.

## Exit Codes

When a command finishes, it returns a numeric **exit code** (also called exit status). `0` means success, and anything else means something went wrong. The convention is universal: shells, scripts, CI runners, and other programs all branch on it.

You can inspect the most recent command's exit code with the special variable `$?`:

```bash
ls /nonexistent
echo $?     # 2
```

A few codes show up often enough to be worth recognizing:

| Code | Meaning |
| --- | --- |
| `0` | Success |
| `1` | General error (catch-all) |
| `2` | Misuse of the command (bad arguments, syntax) |
| `126` | Found but not executable (e.g. missing `x` bit) |
| `127` | Command not found |
| `128+N` | Killed by signal `N` (so `137` = SIGKILL/9, `130` = SIGINT/2 from Ctrl+C) |

Two operators chain commands based on the previous exit code:

- `&&` runs the next command only if the previous one succeeded
- `||` runs the next command only if the previous one failed

```bash
# Only run the binary if the build succeeded
make && ./run

# Print a fallback message if the request failed
curl -fsSL example.com || echo "request failed"
```

In shell scripts, you set your own exit code with `exit N`. `exit 0` declares success, and any nonzero value signals failure to whatever called the script. This is what makes `set -e`, CI pipelines, and pre-commit hooks work: they're all just reading `$?`.

## Permissions

Linux permissions are assigned to **users** and **groups**. A user can belong to multiple groups, and permissions stack across them.

Every file or directory has:

- An **owner** (a user)
- An associated **group**
- A set of permissions defined separately for the **owner**, the **group**, and **others** (everyone else)

### Representing Permissions

Permissions can be written in two equivalent ways: as letters (`rwx`) or as numbers. Each permission has a numeric value:

- `r` (read) = 4
- `w` (write) = 2
- `x` (execute) = 1

You sum the values to get a single digit per category. A three-digit number (e.g. `744`) gives owner, group, others, in that order.

For example, a file with read/write/execute for the owner and read-only for everyone else:

- Owner: `rwx` = 4 + 2 + 1 = **7**
- Group: `r--` = 4 + 0 + 0 = **4**
- Others: `r--` = 4 + 0 + 0 = **4**

That gives `744`.

### What Each Permission Actually Means

The `r`, `w`, `x` bits mean different things for files and directories, which is a common source of confusion:

| Permission | On a file | On a directory |
| --- | --- | --- |
| **Read (r)** | View the file's contents | List the directory's contents (names of files and subdirectories) |
| **Write (w)** | Modify the file's contents | Create, delete, or rename entries inside the directory |
| **Execute (x)** | Run the file as a program | Traverse the directory (e.g. `cd` into it, run `ls -l` inside it) |

> **Gotcha:** Read on a directory lets you list names, but without execute you can't actually access anything inside it.

### Special Permissions

Beyond the standard `rwx` bits, three special permission bits show up regularly, especially in security contexts:

- **SUID (Set User ID)**: when set on an executable, the file runs with the privileges of its *owner*, regardless of who runs it. Often abused for privilege escalation when set on the wrong binary.
- **SGID (Set Group ID)**: when set on an executable, the file runs with the privileges of its *owning group*. When set on a directory, new files created inside it inherit the directory's group ownership, which is useful for shared collaboration directories.
- **Sticky Bit**: applied to directories. Restricts file deletion so that even users with write access to the directory can only delete files *they* own. `/tmp` is the classic example.

> **Quick reference:** the actual commands for changing ownership, permissions, redirection, and everyday shell tasks live in the [Linux Cheat Sheet](/posts/linux-cheatsheet).

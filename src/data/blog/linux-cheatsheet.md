---
author: Kayra
pubDatetime: 2026-05-27T00:00:00Z
title: Linux Cheat Sheet
slug: linux-cheatsheet
featured: false
draft: false
tags:
  - linux
  - cheatsheet
  - notes
description: A growing quick-reference of the Linux commands I actually reach for day to day, from navigation and search to processes, services, and packages.
---

A living quick-reference for the Linux commands I actually use. Each section pairs commands with the moment you'd reach for them. For the model behind any of this, see [Linux Foundations](/posts/linux-foundations).

## Getting Help

```bash
# Full manual page
man ls

# Short usage summary
ls --help

# Friendlier examples (install with: sudo dnf install tldr)
tldr tar
```

## Navigation

```bash
# Where am I
pwd

# Change directory
cd /etc                # absolute path
cd ../..               # parent of parent
cd ~                   # home directory
cd -                   # previous directory

# List files (long format, including hidden ones starting with .)
ls -la

# Visualize directory tree (limit depth with -L)
tree -L 2 dir/
```

## Files and Directories

```bash
# Create empty file
touch file.txt

# Create directory (and any missing parents)
mkdir -p path/to/new/dir

# Copy file (use -r for directories)
cp file.txt backup.txt
cp -r src/ dst/

# Move or rename
mv old.txt new.txt
mv file.txt ~/Documents/

# Delete
rm file.txt
rm -rf dir/            # recursive + force; no recovery
```

> **Danger:** `rm -rf` has no undo. Double-check the path, especially when it contains variables. `rm -rf $UNSET_VAR/` becomes `rm -rf /`.

## Viewing Files

```bash
# Dump whole file
cat file.txt

# Page through (q to quit, / to search)
less file.txt

# First / last N lines
head -n 20 file.txt
tail -n 20 file.txt

# Follow a log live
tail -f /var/log/syslog

# Count lines, words, bytes
wc -l file.txt
```

## Search

```bash
# Find files by name
find /etc -name "*.conf"

# Find directories by name (case-insensitive)
find / -type d -iname "backup" 2>/dev/null

# Find files larger than 100MB
find / -type f -size +100M 2>/dev/null

# Find files modified in the last 7 days
find . -type f -mtime -7

# Find files accessed in the last 24 hours
find . -type f -atime -1

# Find files owned by a user
find /home -user kayra

# Find files with exact permissions
find ~ -type f -perm 600

# Find empty files or directories
find . -type f -empty
find . -type d -empty

# Run a command on every match (one process per file)
find . -name "*.log" -exec rm {} \;

# Run a command in batches (bundles many files per process; faster)
find . -name "*.log" -exec rm {} +

# Pipe results safely (handles spaces and newlines in filenames)
find . -name "*.log" -print0 | xargs -0 rm

# Grep recursively, case-insensitive, with line numbers
grep -rin "TODO" .

# Show matches with surrounding context (before/after)
grep -B 2 -A 2 "error" app.log

# Count matches per file
grep -c "ERROR" app.log

# List filenames only (no matched lines)
grep -rl "API_KEY" .

# Invert: lines NOT matching the pattern
grep -v "DEBUG" app.log

# Match whole word only (so "log" doesn't hit "logging")
grep -w "log" file.txt

# Extended regex with alternation
grep -E "warn|error|fatal" app.log

# Print only the matched text, not the full line
grep -oE '\b[0-9]{1,3}(\.[0-9]{1,3}){3}\b' access.log

# Locate (uses an indexed database, much faster than find)
locate nginx.conf
sudo updatedb               # refresh the index

# Where is a command's binary
which python3
```

## Text Processing

```bash
# === sed (stream editor) ===

# Print the file with the first match per line replaced (no in-place edit)
sed 's/foo/bar/' file.txt

# Replace every occurrence on every line (g = global)
sed 's/foo/bar/g' file.txt

# Edit the file in place; -i.bak also keeps a backup as file.txt.bak
sed -i 's/foo/bar/g' file.txt

# Use a different delimiter when the pattern contains /
sed 's|/var/log|/tmp|g' paths.txt

# Print only matching lines (-n silences default output)
sed -n '/error/p' app.log

# Print a line range (10 through 20)
sed -n '10,20p' file.txt

# Delete blank lines
sed '/^$/d' file.txt

# === awk (field processor) ===

# Print the 1st and 3rd whitespace-separated fields
awk '{print $1, $3}' file.txt

# Custom field separator (here, colon for /etc/passwd)
awk -F: '{print $1}' /etc/passwd

# Filter rows then print
awk '$3 > 1000 {print $1}' data.txt

# Sum a column
awk '{sum += $2} END {print sum}' data.txt

# Print lines longer than 80 characters
awk 'length > 80' file.txt

# Count occurrences of a value in column 1
awk '{count[$1]++} END {for (k in count) print k, count[k]}' data.txt

# === jq (JSON processor) ===

# Pretty-print JSON
jq . data.json

# Extract a nested field
jq '.user.name' data.json

# Iterate an array, picking a field from each element
jq '.items[].id' data.json

# Filter array elements by a condition
jq '.users[] | select(.active == true)' data.json

# Build a new object from existing fields
jq '{name: .user.name, id: .user.id}' data.json

# Raw string output (no surrounding quotes), useful for piping
jq -r '.users[].email' data.json

# Pipe curl output through jq
curl -s https://api.example.com/users | jq -r '.[].email'
```

> **Note:** `sed -i` rewrites the file with no undo. Run the command without `-i` first to confirm the output looks right, then re-run with `-i`.

## Editors

```bash
# === nano (beginner-friendly, modeless) ===

# Open or create a file
nano file.txt

# Open with line numbers shown
nano -l file.txt

# Inside nano (^ means Ctrl):
#   ^O  write (save), then Enter to confirm filename
#   ^X  exit (prompts to save if modified)
#   ^W  search        | ^\  search & replace
#   ^K  cut line      | ^U  paste
#   ^G  show help

# === vi / vim (modal, ubiquitous on servers) ===

# Open or create a file
vi file.txt

# vi has modes. Press Esc to return to Normal mode from anywhere.
#   i        enter Insert mode (start typing)
#   v        enter Visual mode (select text)
#   :        enter Command mode

# In Command mode:
#   :w       save                | :q     quit
#   :wq      save and quit       | :q!    discard and quit
#   :42      jump to line 42

# In Normal mode:
#   /foo     search forward; n = next, N = previous
#   gg / G   jump to top / bottom of file
#   dd       delete (cut) current line
#   yy       yank (copy) current line
#   p        paste below cursor
#   u        undo                | Ctrl+R  redo
```

> **Tip:** If you find yourself stuck in `vi` and just need out, press `Esc`, then type `:q!` and Enter to discard changes and quit.

## Redirection and Pipes

```bash
# Discard error messages
command 2>/dev/null

# Send stdout and stderr to separate files
command 1>stdout.txt 2>stderr.txt

# Send both stdout and stderr to the same file
command > combined.txt 2>&1

# Overwrite (creates the file or replaces its contents)
command > out.txt

# Append (creates if missing, adds to the end if it exists)
command >> out.txt

# Feed a file in as stdin
cat < input.txt

# Pipe stdout of one command into stdin of the next
ps aux | grep nginx
```

> **Note:** `>` overwrites without warning. Use `>>` whenever you want to preserve what's already there.

## Permissions and Ownership

```bash
# Make a script executable
chmod +x script.sh

# Standard executable (owner: rwx, others: rx)
chmod 755 script.sh

# Standard file (owner: rw, others: r)
chmod 644 notes.md

# Private file, e.g. SSH keys
chmod 600 ~/.ssh/id_rsa

# Apply to a directory and everything under it
chmod -R 755 dir/

# Change owner
chown user file
chown user:group file
chown -R user:group dir/

# Change just the group
chgrp group file

# Reference: r=4 w=2 x=1, order = owner group other
```

### Special Permission Bits

```bash
# SUID: runs as file owner regardless of caller
chmod u+s binary
chmod 4755 binary

# SGID: runs as file's group; on dirs, children inherit the group
chmod g+s binary
chmod 2755 dir/

# Sticky bit: only the file's owner (or root) can delete it
chmod +t /shared
chmod 1777 /shared

# Hunt for SUID binaries (useful for privilege-escalation checks)
find / -perm -4000 -type f 2>/dev/null
```

## Processes

```bash
# List all processes
ps aux

# Filter by name
ps aux | grep nginx
pgrep -a nginx

# Interactive process viewer
top
htop                          # nicer; install if missing

# Kill by PID
kill 12345
kill -9 12345                 # force (SIGKILL)

# Kill all matching processes by name
killall nginx

# Background and foreground jobs
command &                     # run in background
jobs                          # list backgrounded jobs
fg %1                         # bring job 1 to foreground
bg %1                         # resume job 1 in background

# Keep a process running after the terminal closes
nohup long-running-command &
```

> **Note:** `kill -9` does not give the process a chance to clean up. Try `kill PID` (SIGTERM) first and only escalate if it ignores you.

## Services (systemd)

```bash
# Check status
systemctl status postgresql

# Start, stop, restart
sudo systemctl start postgresql
sudo systemctl stop postgresql
sudo systemctl restart postgresql

# Reload config without restarting (if the service supports it)
sudo systemctl reload nginx

# Enable or disable on boot
sudo systemctl enable postgresql
sudo systemctl disable postgresql

# List running services
systemctl list-units --type=service --state=running

# View logs for a specific service
journalctl -u postgresql

# Follow logs in real time
journalctl -u postgresql -f

# Last hour of logs
journalctl --since "1 hour ago"
```

## Package Management

```bash
# === Fedora / RHEL (dnf) ===

sudo dnf install package
sudo dnf remove package
sudo dnf upgrade
dnf search keyword
dnf info package

# === Debian / Ubuntu (apt) ===

sudo apt install package
sudo apt remove package
sudo apt update && sudo apt upgrade
apt search keyword
apt show package
```

## Networking

```bash
# Show interfaces and IPs
ip a

# Show routing table
ip r

# Reachability check
ping -c 4 example.com

# HTTP request (headers only, then verbose)
curl -I https://example.com
curl -v https://example.com

# Show listening ports with the owning process
ss -tulnp

# DNS lookup
dig example.com
nslookup example.com

# Trace route to a host
traceroute example.com
```

## Quick Web Server

```bash
# Serve the current directory on port 8000 (Python 3)
python3 -m http.server 8000

# Bind to a specific interface (here, loopback only)
python3 -m http.server 8000 --bind 127.0.0.1

# Serve a different directory without cd-ing into it
python3 -m http.server 8000 --directory ~/public

# Same idea with PHP, if it's already installed
php -S 0.0.0.0:8000

# Same idea with busybox (handy on minimal systems)
busybox httpd -f -p 8000
```

> **Note:** `python3 -m http.server` is for quick file transfers and local testing only. It has no auth, no TLS, and is single-threaded.

## Disk and Space

```bash
# Filesystem usage, human-readable
df -h

# Size of this directory
du -sh ~/Documents

# Top-level breakdown of a directory
du -h --max-depth=1 /var
```

## Users and Groups

```bash
# Who am I, and what groups am I in
whoami
id

# Who else is logged in
who
w

# Run a command as root
sudo command

# Switch to another user
su - username

# Change your password
passwd
```

## Archives

```bash
# Create a gzip tarball
tar -czvf out.tar.gz dir/

# Extract a gzip tarball
tar -xzvf in.tar.gz

# List contents without extracting
tar -tzvf archive.tar.gz

# Zip and unzip
zip -r archive.zip dir/
unzip archive.zip
```

## Keyboard Shortcuts

| Shortcut | Action |
| --- | --- |
| `Tab` | Auto-complete file or command name |
| `Tab Tab` | Show all possible completions |
| `Ctrl+L` | Clear the screen |
| `Ctrl+C` | Cancel the current command |
| `Ctrl+D` | Exit the shell, or send EOF |
| `Ctrl+R` | Reverse search through history |
| `Ctrl+A` | Move cursor to start of line |
| `Ctrl+E` | Move cursor to end of line |
| `Ctrl+W` | Delete the word before the cursor |
| `Ctrl+U` | Delete from cursor to start of line |
| `↑` / `↓` | Cycle through command history |
| `!!` | Run the last command again |
| `!$` | Last argument of the previous command |

---
title: "tmux"
slug: tmux
category: notes
handbook: oscp
tags: ["linux"]
draft: false
pubDatetime: 2026-07-24T12:03:13+03:00
modDatetime: 2026-09-13T19:42:38+03:00
description: "Terminal multiplexer for the working environment."
---
Terminal multiplexer for the working environment. Sessions survive disconnects, panes keep a listener and a shell side by side, and the logging plugin records pane output as report evidence. The configuration lives in `~/.tmux.conf`; the file below is the current one, and every binding in this note assumes the prefix it sets.

## Install

```bash
sudo apt install tmux
```

## Start a Session

Change into the box directory before starting tmux:

```bash
cd results/TARGET

tmux new -s OSCP
```

New windows inherit the session's starting directory, so they open in the box directory instead of the home directory.

Use a distinct session name when several sessions are needed:

```bash
tmux new -s BOXNAME
```

List existing sessions:

```bash
tmux ls
```

Attach to a session:

```bash
tmux attach -t OSCP
```

Kill a session after its work is finished:

```bash
tmux kill-session -t OSCP
```

## Prefix Keys

tmux commands begin with a prefix. With the default configuration, press `Ctrl-B`, release both keys, then press the command key.

The configuration below changes the prefix to `Ctrl-A`. After reloading it, press `Ctrl-A`, release both keys, then press the command key.

## Configuration

The personal tmux configuration is stored at:

```text
~/.tmux.conf
```

Edit it with any text editor:

```bash
nano ~/.tmux.conf
```

Configuration:

```tmux
# Remap the prefix to Ctrl-A, matching GNU Screen
unbind C-b
set -g prefix C-a
bind C-a send-prefix

# Quality of life
set -g history-limit 10000
set -g allow-rename off
set -g mouse on

# Join a pane from another window into the current window
bind-key j command-prompt -p "join pane from:" "join-pane -s '%%'"

# Send the current pane to another window
bind-key s command-prompt -p "send pane to:" "join-pane -t '%%'"

# Use vi keys in copy mode
set-window-option -g mode-keys vi

# Load tmux-logging
run-shell /opt/tmux-logging/logging.tmux
```

Reload the file without restarting tmux:

```bash
tmux source-file ~/.tmux.conf
```

From inside tmux, the same command can be run through its command prompt:

```text
Ctrl-A, release, :
source-file ~/.tmux.conf
```

The prefix changes as soon as the configuration is loaded. Use `Ctrl-A` for subsequent commands.

Check configuration errors by running the reload command in a normal terminal. tmux prints the line number when it cannot parse an option or binding.

## Navigation

A session holds windows, a window divides into panes, and the green border marks the active pane, with the arrow bindings changing which pane owns it.

These bindings assume the prefix has been changed to `Ctrl-A`:

```text
Ctrl-A, release, c       create a window
Ctrl-A, release, ,       rename the current window
Ctrl-A, release, n       next window
Ctrl-A, release, p       previous window
Ctrl-A, release, 0..9    jump to a numbered window
Ctrl-A, release, %             vertical split, panes side by side
Ctrl-A, release, "             horizontal split, panes above and below
Ctrl-A, release, arrow         select a pane
Ctrl-A, release, Ctrl-arrow    resize the active pane
Ctrl-A, release, {             swap with the previous pane
Ctrl-A, release, }             swap with the next pane
Ctrl-A, release, d             detach from the session
```

The resize bindings can be repeated while holding `Ctrl` and pressing an arrow.

With two panes, `{` and `}` look like moving left and right. They actually swap the active pane with the previous or next pane in tmux's pane order.

### Shell Line Movement

The remapped prefix consumes the first `Ctrl-A`. Send a literal `Ctrl-A` through tmux to move to the beginning of the shell command line:

```text
Ctrl-A, release, Ctrl-A    beginning of the line
```

`Ctrl-E` does not conflict with the tmux prefix:

```text
Ctrl-E                     end of the line
```

Close a pane or window by exiting its shell:

```bash
exit
```

## Copy Mode and Scrollback

With `set -g mouse on`, the wheel scrolls through tmux's pane history and enters copy mode automatically. Without it, the wheel reaches the shell as `Up` and `Down`, cycling through command history.

Enter copy mode with the keyboard:

```text
Ctrl-A, release, [
```

With `mode-keys vi`, useful keys inside copy mode are:

```text
?           search backward through pane history
Page Up     move up one page
Page Down   move down one page
Space       begin selecting text
Enter       copy the selection to the tmux buffer and leave copy mode
q           leave copy mode without copying
```

Paste the most recently copied tmux buffer:

```text
Ctrl-A, release, ]
```

Copy mode operates on tmux's pane history, not the terminal emulator's scrollback, and the configured history limit keeps up to 10,000 lines per pane.

## Joining and Sending Panes

The custom `j` binding joins a pane from another window into the current window:

```text
Ctrl-A, release, j
join pane from: SESSION:WINDOW.PANE
```

Example:

```text
OSCP:2.0
```

The custom `s` binding sends the current pane to another window:

```text
Ctrl-A, release, s
send pane to: SESSION:WINDOW
```

Example:

```text
OSCP:3
```

List the available targets before moving panes:

```bash
tmux list-panes -a -F '#S:#I.#P  #W'
```

## Logging

Loading the plugin defines its tmux bindings. It does not immediately record every pane. Logging is started and stopped separately for the current pane.

Install the plugin into the path used by the configuration:

```bash
sudo git clone https://github.com/tmux-plugins/tmux-logging.git \
  /opt/tmux-logging
```

Confirm that the entry point exists:

```bash
ls -l /opt/tmux-logging/logging.tmux
```

The `run-shell` line at the bottom of the configuration loads it. Reload the configuration after the clone.

With the remapped prefix, toggle logging for the current pane:

```text
Ctrl-A, release, Shift-P
```

Pressing it once starts recording everything typed and printed in that pane. Pressing it again stops recording. This is useful for logging a shell or an important enumeration command without recording unrelated panes. The status line briefly reports whether logging started or stopped.

Logs are written to the home directory by default with names similar to:

```text
~/tmux-OSCP-0-1-20260724T120000.log
```

Find recent logs:

```bash
ls -lt ~/tmux-*.log
```

Saving the complete history is separate from live logging. It writes the history still retained by `history-limit`:

```text
Ctrl-A, release, Alt-Shift-P
```

Capture only the text currently visible in the pane:

```text
Ctrl-A, release, Alt-P
```

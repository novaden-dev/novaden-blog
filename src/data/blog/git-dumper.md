---
title: "git-dumper"
slug: git-dumper
category: notes
handbook: oscp
tags: ["web"]
draft: false
pubDatetime: 2026-07-24T12:03:13+03:00
modDatetime: 2026-09-13T20:51:50+03:00
description: "Rebuilds a git repository from an exposed `.git/` directory over HTTP."
---
Rebuilds a git repository from an exposed `.git/` directory over HTTP. Finding `.git/` during [Web Content Discovery](/collections/oscp/web-content-discovery) means the application's source, and often its history, is downloadable: credentials in config files, hardcoded keys, an admin path, or a file that was deleted in a later commit but still lives in an old object. Used on bullyBox, where the repository held the BoxBilling config and the admin password an authenticated RCE needed.

## 403 on /.git/ Is Not a Blocker

A `403` on `/.git/` usually means directory listing is off, not that the path is protected. The files underneath are still served. Check the one file every repository has:

```bash
curl -s http://TARGET/.git/HEAD
```

`ref: refs/heads/master` (or `main`) means the dump will work. `.git/config` is the second check. If those return `403` or `404` as well, the server is blocking the whole directory and there is nothing to pull.

git-dumper handles both cases. With listing enabled it walks the index; without it, it fetches the known paths (`HEAD`, `config`, `index`, `packed-refs`, `logs/HEAD`, `objects/info/packs`) and recursively resolves every object hash it finds inside them.

## Install

Not packaged in Kali, and Kali's system Python is externally managed so plain `pip install` fails. Use pipx:

```bash
sudo apt install -y pipx
pipx install git-dumper
pipx ensurepath
```

`pipx ensurepath` adds `~/.local/bin` to `PATH`, which needs a new shell to take effect.

## Use

```bash
git-dumper http://TARGET/.git/ ~/loot/target-repo
```

Useful options:

- `-b BRANCH`: an extra branch name to try. Without listing, git-dumper guesses common refs, so a repository whose work lives on `dev` or `feature-x` comes down incomplete unless the name is supplied. Repeatable.
- `-H "NAME=VALUE"`: extra headers, separated by `=` not `:` (for example `-H "Cookie=session=..."`), for a `.git/` behind authentication.
- `-u`: user agent, when a WAF is filtering the default.
- `--proxy http://127.0.0.1:8080`: route through [Burp Suite](/collections/oscp/burp-suite) to see what is actually being fetched.

## After the Dump

The dump ends with its own `git checkout .`, so the working tree normally comes down populated. If the dump was incomplete the checkout can fail or leave files missing; check and finish it by hand:

```bash
cd ~/loot/target-repo
git status
git checkout -- .
```

Then read the history, which is the point of doing this rather than just fuzzing for source files:

```bash
git log --oneline --all          # every commit on every recovered branch
git branch -a                    # branches that came down
git show <commit>                # full contents of one commit
git diff <old> <new>             # what changed between two
git log --diff-filter=D --name-only --all    # files deleted at some point
```

Secrets are usually in a commit that was later "fixed", so grep the patches rather than the checked-out files:

```bash
git log -p --all | grep -iE "pass|passwd|secret|token|api[_-]?key|BEGIN .*PRIVATE KEY"
```

Also worth reading directly: `.git/config` for a remote URL with credentials in it, and `.git/logs/HEAD` for commit hashes and committer names that become usernames to spray.

## Browsing It in a GUI

Once the working tree is checked out the code is just files on disk, so any editor opens it. For reading the history rather than the current state, `gitk` shows the commit graph with the diff of each commit in one window:

```bash
sudo apt install -y gitk
gitk --all
```

`--all` includes every recovered branch, not just the checked-out one. Clicking through commits is faster than `git log -p` for spotting a config file that was added and then removed.

## Incomplete Dumps

A partial download is normal when some objects are packed or a ref was missed. Check what is broken:

```bash
git fsck
```

Missing objects that git-dumper still fetched can be read directly by hash, which is enough to recover a single file without a working checkout:

```bash
git cat-file -p <hash>
```

---
author: Kayra
pubDatetime: 2026-05-27T00:00:00Z
title: Git Cheat Sheet
slug: git-cheatsheet
featured: false
draft: false
tags: ["tech", "cheatsheet"]
category: notes
description: A growing quick-reference of the Git commands I actually reach for. Staging, branching, rebasing, undoing things, and recovering from a bad day.
---

A living quick-reference for the Git commands I actually use. Each section pairs commands with the moment you'd reach for them. For the model behind any of this, see [Git Foundations](/posts/git-foundations).

## Setup

```bash
# Set identity (used in every commit you make)
git config --global user.name "Kayra"
git config --global user.email "you@example.com"

# Default editor for commit messages
git config --global core.editor "vim"

# Use main as the default branch name for new repos
git config --global init.defaultBranch main

# Sensible pager defaults
git config --global core.pager "less -FRX"

# Make pushes default to current branch only
git config --global push.default current

# Show every setting and where it came from
git config --list --show-origin
```

## Starting a Repository

```bash
# Initialize a new repo in the current directory
git init

# Clone an existing repo
git clone git@github.com:user/repo.git

# Clone into a specific folder
git clone git@github.com:user/repo.git my-folder

# Shallow clone (just the latest commit, much faster)
git clone --depth 1 git@github.com:user/repo.git
```

## Inspecting State

```bash
# What's changed, staged, untracked
git status

# Short, two-letter status (X = index, Y = working tree)
git status -s

# Unstaged changes
git diff

# Staged changes (what's about to be committed)
git diff --staged

# Diff between two refs
git diff main..feature

# Show a specific commit
git show abc1234

# Who last touched each line of a file
git blame file.txt
```

## Logging History

```bash
# Compact one-line log with graph and refs
git log --oneline --graph --decorate --all

# Last 5 commits with stats
git log -n 5 --stat

# Commits that touched a specific file (including renames)
git log --follow -- path/to/file

# Commits by author
git log --author="Kayra"

# Commits matching a message pattern
git log --grep="fix typo"

# Find commits that added or removed a specific string
git log -S "function_name"
```

## Staging and Committing

```bash
# Stage a specific file
git add file.txt

# Stage every change in the current dir and below
git add .

# Stage interactively, hunk by hunk
git add -p

# Unstage a file (keep the change in the working tree)
git restore --staged file.txt

# Commit staged changes
git commit -m "Add login form"

# Stage all tracked, modified files and commit in one step
git commit -am "Fix typo"

# Edit the most recent commit (message and/or contents)
git commit --amend
git commit --amend --no-edit       # keep the existing message
```

> **Danger:** `--amend` rewrites the previous commit, including its hash. Never amend a commit you have already pushed to a shared branch.

## Branches

```bash
# List local branches (current marked with *)
git branch

# List all branches (local + remote-tracking)
git branch -a

# Create a branch (but stay where you are)
git branch feature-x

# Create and switch in one step
git switch -c feature-x

# Switch to an existing branch
git switch main

# Rename current branch
git branch -m new-name

# Delete a merged branch
git branch -d old-branch

# Force-delete (even if unmerged)
git branch -D old-branch
```

## Merging

```bash
# Merge another branch into the current one
git merge feature-x

# Force a merge commit, even if a fast-forward is possible
git merge --no-ff feature-x

# Abort a merge in progress
git merge --abort

# After resolving conflicts, mark files resolved and finish
git add resolved-file.txt
git commit
```

## Rebasing

```bash
# Replay current branch on top of main
git rebase main

# Interactive rebase: reorder, squash, edit, drop commits
git rebase -i HEAD~5

# Continue a paused rebase after resolving conflicts
git add resolved-file.txt
git rebase --continue

# Skip the current commit during rebase
git rebase --skip

# Abort a rebase, return to where you started
git rebase --abort
```

> **Danger:** Rebasing rewrites history. If you have pushed the commits being rebased to a shared branch, don't rebase them.

## Stashing

```bash
# Save uncommitted changes and clean the working tree
git stash

# Stash including untracked files
git stash -u

# Stash with a message
git stash push -m "WIP login refactor"

# List stashes
git stash list

# Reapply most recent stash (keeps it on the stack)
git stash apply

# Reapply and drop from the stack
git stash pop

# Show what's in a stash
git stash show -p stash@{0}

# Drop a specific stash
git stash drop stash@{0}

# Clear every stash
git stash clear
```

## Remotes

```bash
# List remotes
git remote -v

# Add a remote
git remote add origin git@github.com:user/repo.git

# Change a remote URL
git remote set-url origin git@github.com:user/new-repo.git

# Download remote commits without merging
git fetch
git fetch --all                   # all remotes

# Fetch and merge upstream into current branch
git pull

# Pull with rebase instead of merge
git pull --rebase

# Push current branch to its tracked upstream
git push

# First push: set upstream for the branch
git push -u origin feature-x

# Force-push, safely (refuses if the remote moved since your last fetch)
git push --force-with-lease

# Delete a remote branch
git push origin --delete old-branch

# Prune deleted remote-tracking branches
git fetch --prune
```

> **Danger:** Plain `--force` will silently overwrite teammates' work if they pushed since you last fetched. Use `--force-with-lease` instead. Never force-push to `main`.

## Tags

```bash
# List tags
git tag

# Lightweight tag at the current commit
git tag v1.0.0

# Annotated tag (preferred for releases)
git tag -a v1.0.0 -m "Release 1.0.0"

# Tag a specific commit
git tag -a v0.9.0 abc1234 -m "Beta release"

# Push a tag
git push origin v1.0.0

# Push all tags
git push --tags

# Delete a tag locally and remotely
git tag -d v1.0.0
git push origin --delete v1.0.0
```

## Undoing Things

```bash
# Discard unstaged changes to a file
git restore file.txt

# Discard ALL unstaged changes (destructive)
git restore .

# Unstage a file (keep working-tree changes)
git restore --staged file.txt

# Move branch pointer back, keep changes staged
git reset --soft HEAD~1

# Move branch pointer back, unstage but keep changes
git reset HEAD~1

# Move branch pointer back AND wipe changes (destructive)
git reset --hard HEAD~1

# Make a new commit that undoes an old one (safe for shared history)
git revert abc1234

# Show every recent position of HEAD (rescue tool)
git reflog

# Recover a "lost" commit (after a bad reset, rebase, or branch delete)
git switch -c recovered abc1234   # the hash from reflog
```

> **Danger:** `git reset --hard` and `git restore .` discard uncommitted work with no warning. Stash first if you are not sure.

## Cherry-Pick

```bash
# Apply a specific commit from another branch onto the current one
git cherry-pick abc1234

# Cherry-pick a range
git cherry-pick abc1234..def5678

# Continue or abort after resolving conflicts
git cherry-pick --continue
git cherry-pick --abort
```

## Bisect

```bash
# Start a binary search for the commit that introduced a bug
git bisect start
git bisect bad                    # current commit is broken
git bisect good v1.0.0            # this earlier ref worked

# Git checks out a midpoint, you test, then mark:
git bisect good
git bisect bad

# When done, return to where you started
git bisect reset
```

## Cleaning Up

```bash
# Preview what would be removed (always run this first)
git clean -n

# Remove untracked files
git clean -f

# Remove untracked files and directories
git clean -fd

# Also remove gitignored files
git clean -fdx

# Garbage collect, prune unreachable objects
git gc --prune=now
```

> **Danger:** `git clean` deletes files Git is not tracking, so they cannot be recovered from history. Always preview with `-n` first.

## Ignoring Files

```bash
# Project-level ignores (committed to the repo)
echo "node_modules/" >> .gitignore
echo ".env" >> .gitignore

# Your-machine-only ignores (not committed)
echo "*.local" >> .git/info/exclude

# Stop tracking a file that's now in .gitignore
git rm --cached secrets.env
```

## Aliases

```bash
# Set an alias
git config --global alias.co checkout
git config --global alias.st status
git config --global alias.lg "log --oneline --graph --decorate --all"

# Use it
git lg
```

## Useful One-Offs

```bash
# Who changed lines 10-20 of a file
git blame -L 10,20 file.txt

# Show the contents of a file at a specific commit
git show abc1234:path/to/file.txt

# Restore a deleted file from history
git checkout abc1234 -- path/to/file.txt

# What changed between two tags
git diff v1.0.0..v1.1.0

# Repo size and object count
git count-objects -vH
```

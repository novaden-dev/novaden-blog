---
author: Kayra
pubDatetime: 2026-05-27T00:00:00Z
title: Git Foundations
slug: git-foundations
featured: false
draft: true
tags: ["git"]
category: notes
description: The three areas, commits as snapshots, branches as pointers, HEAD, remotes, and why merge and rebase differ.
---

## Introduction

Git is a version control system: it tracks the state of a project over time. You can get by with a handful of memorized commands (`git add`, `git commit`, `git push`) right up until something goes wrong. Then the commands stop making sense, because nothing underneath explains them.

## What Git Actually Stores

At its core, Git is a content-addressable filesystem. Every file you commit is hashed (SHA-1 by default), and that hash is its identity. Two files with identical contents share the same hash and are stored once. A directory is stored as a *tree* object that lists files (with their hashes) and any subtrees inside it. A commit is a small object that points to one root tree, plus metadata: author, date, message, and a pointer to its parent commit (or commits, for merges).

Everything else in Git is built on those three object types: blob (file), tree (directory), commit (snapshot in time).

> **Note:** Git stores snapshots, not diffs. The diff you see in `git log` or `git show` is computed on demand by comparing two snapshots, not retrieved from storage.

## The Three Areas

Every change in a Git repository moves through three areas:

- **Working tree**: the files on disk that you can edit with any editor.
- **Staging area** (also called the *index*): a snapshot of what your next commit will look like.
- **Repository**: the history of committed snapshots, stored under `.git/`.

You move changes between them with a small set of commands:

- `git add` copies a working-tree file into the staging area.
- `git commit` records the staging area as a new commit in the repository.
- `git checkout` / `git restore` pulls files out of the repository back into the working tree.

## Commits as Snapshots

A commit is a snapshot of your whole project at a point in time, plus a pointer to the commit (or commits) that came before it. Follow the pointers and you get a graph of history.

Three things follow from this:

- Each commit has a unique hash. You can refer to any commit by its hash, or by a unique prefix of it.
- You can never truly *edit* a commit. Anything that looks like editing (`git commit --amend`, rebase) actually creates a new commit and quietly moves a pointer.
- History is a graph, not a line. Merge commits have two parents; everything else has one.

## Branches and HEAD

A branch in Git is not a folder or a copy of the code. It is a single file containing a commit hash. `.git/refs/heads/main` is literally a text file with one line: the hash of the latest commit on `main`.

When you commit on a branch, Git creates a new commit whose parent is the current tip, then updates the branch file to point at the new commit. The branch "moves forward."

**HEAD** is a separate pointer that says *where you are right now*. Normally HEAD points at a branch (e.g. `ref: refs/heads/main`), and the branch points at a commit. When you commit, both advance together. If you check out a specific commit hash directly, HEAD points at that commit instead of at a branch. This is "detached HEAD" state. It is fine for inspection, but a foot gun for new work, because any commits you make there are not on any branch.

> **Watch out:** Detached HEAD itself is not dangerous. *Forgetting* commits made in detached HEAD is. If you do real work there, create a branch (`git switch -c temp`) before switching away.

## Merging and Rebasing

When two branches diverge and you want to bring them back together, Git offers two strategies. They produce different histories.

- **Merge**: creates a new commit (a merge commit) with two parents. History keeps both branch lines and joins them at the merge. Non-destructive.
- **Rebase**: replays the commits from one branch on top of another, one by one. The original commits are discarded and rewritten as new commits with new hashes. History looks linear, but it is not the literal history.

Both are fine. Merge keeps the history exactly as it happened. Rebase turns it into a straight line. Most teams settle on a rule: rebase before sharing, merge once shared. The warning "don't rebase shared branches" exists because rebase changes every hash. If a teammate already has the old commits, their copy and yours stop matching, and untangling that is no fun.

## Remotes

A remote is a nickname for another copy of the repo, usually on GitHub. `origin` is the conventional name for the remote you cloned from, but there is nothing special about the name itself.

Two operations move commits between you and a remote:

- `git fetch` downloads commits from the remote into local *remote-tracking* branches (e.g. `origin/main`). It does not touch your local branches.
- `git push` uploads your local commits to the remote.

`git pull` is `git fetch` followed by a merge or rebase of `origin/<branch>` into your local branch, depending on config. Handy, but it hides the steps. When something breaks, run `fetch` and then `merge` or `rebase` yourself, so you can see exactly what moved.

## The Reflog

Because Git rewrites pointers (branches, HEAD) constantly, it keeps a private journal of every move: the **reflog**. `git reflog` shows where HEAD has been over the last 90 days by default, even for commits that no branch points at anymore.

This is the single most important recovery tool in Git. If you "lose" work to a `reset --hard`, a botched rebase, or a deleted branch, the commits are almost always still in the reflog, reachable by hash. Git only deletes them for real after they age out: 90 days for reachable commits, 30 for unreachable.

> **Note:** The reflog is local to your machine. It is not pushed to remotes. If you destroy a commit on your laptop and have not pushed it, the reflog is what saves you. If you destroy it after pushing, the remote still has it.

## `.git` Is Just a Directory

The `.git/` directory at the root of every repo contains the entire history. Some of what lives in it:

| Path | What it is |
| --- | --- |
| `objects/` | Every blob, tree, and commit, stored by hash. |
| `refs/heads/` | One file per local branch, each containing a commit hash. |
| `refs/remotes/` | Remote-tracking branches. |
| `HEAD` | A file pointing at the current branch (or commit, in detached HEAD). |
| `config` | Per-repo settings. |
| `hooks/` | Scripts that run at specific events (`pre-commit`, `pre-push`, etc.). |

You can `cat` any of these files. The whole system is open. When a command does something confusing, looking at how `.git/` changed before and after is often the fastest way to understand what happened.

> The commands are in the [Git Cheat Sheet](/posts/git-cheatsheet).

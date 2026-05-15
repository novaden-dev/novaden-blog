# Categorization Plan

**This document defines the canonical tag taxonomy for novaden-blog.** It is not just a migration plan — it is the source of truth for how every post on this site is tagged, going forward. All existing posts, all migrated posts, and all future posts must conform to the scheme below. Any tag that is not defined here should not appear in `src/data/blog/`.

Plan scope covers migrating notes from `NotesHubGitBook-main/` and other PersonalWork directories into this Astro blog, AND bringing the two pre-existing posts into the scheme.

## Scope

- **Source (security):** `NotesHubGitBook-main/` — 142 markdown files, 100% security/infosec
- **Source (general):** `HomeLabBackUp4Checking/`, `infra-cluster-manifests/`, `Prism/`, `TouchGrass/`, `notfromsugar/`, `AhmedHamdyConsultant/`, `expense-tracking/`, `VisaStressRelief/`, `strategic_recommendations.txt` — ~30 files
- **Target:** `src/data/blog/` (flat directory, Astro collection)
- **Excluded:** `brainspill`/`brainspill1` (duplicates), Dendron/ClaudeCode source trees, AnkiDecks (CSVs), Scripts, encrypted ransomware files, binary backups
- **Archived content:** None detected in source (no archive folders, no `archived:`/`draft:` frontmatter)

## Tag Scheme — Two Axes, 7 Tags

Tags split across two axes. Every post gets **exactly one subject tag**, and **zero or one format tag(s)**. This keeps subject-based discoverability intact (a security writeup still shows up under `security`) while preserving format-based browsing (all writeups in one place regardless of subject).

### Subject tags (pick exactly 1)

| Tag | What it captures | Example content |
|-----|------------------|-----------------|
| `fundamentals` | Encyclopedic "how X works" — timeless, conceptual | HDD vs SSD, TCP/IP, Linux permissions, OSI model, cognitive biases, game theory |
| `security` | All security content — attacks, vulns, pentesting, web sec, defensive | AD exploitation, command injection, password attacks, XSS, privilege escalation, HTB box compromises |
| `tech` | Experiential tech writing — tutorials, opinions, migrations, homelab | Windows→Fedora, k3s homelab setup, dev tooling choices, Kubernetes architecture |
| `personal` | Career, health, visa, life | Resume strategy, visa monitor, diabetes notes, burnout recovery |

### Format tags (pick 0 or more, add to subject)

| Tag | When to add | Example |
|-----|-------------|---------|
| `writeups` | Step-by-step compromise of a specific machine/lab with console output | `["security", "writeups"]` for HTB Nibbles |
| `cheatsheet` | Terse reference — mostly command dumps / syntax tables, assumes you know the tool | `["security", "cheatsheet"]` for an OSCP command dump; `["tech", "cheatsheet"]` for a git one-liner reference |
| `tool-guide` | Tutorial that teaches a specific tool — intro prose + commands + explanations of flags/options | `["security", "tool-guide"]` for the hydra or nmap write-up |

**`cheatsheet` vs `tool-guide`:** both cover tools, but the reader intent differs. Cheatsheets are for reference while working ("what flag do I need?"). Tool guides are for learning ("how do I use this tool?"). If a file opens with "X is a Y used for Z" and walks through usage with context, it's a tool-guide. If it's just a dump of commands with minimal prose, it's a cheatsheet.

## Tag Assignment Rules

1. Pick the subject first, not the format. Ask: "what is this post *about*?" — not "what does it *look like*?"
2. Add `writeups` if the post is a walkthrough with concrete enumeration/exploitation steps against a named target.
3. Add `cheatsheet` if the post is ≥70% command reference / syntax tables with minimal prose.
4. Add `tool-guide` if the post teaches a specific tool end-to-end (intro + usage + flag explanations).
5. Format tags are mutually exclusive in practice — a post is one of {writeups, cheatsheet, tool-guide}, not two. The rare exception is a writeup that ends with a cheat-sheet section; even then, prefer the primary format.
6. Never tag a post with a format tag alone — format tags require a subject.

### Sharpening `fundamentals` vs `tech`

The boundary is fuzzy in practice because "how it works" (fundamentals) and "architecture" (tech) sound similar. Apply this single discriminator:

- **`fundamentals`** = tool-agnostic, evergreen explainers. No named product, vendor, or version. Would still be accurate in 10 years. Examples: HDD vs SSD, TCP/IP, OSI model, Linux permissions model, hashing vs encryption, cognitive biases.
- **`tech`** = implementation-specific writing. Named products, versions, tutorials, setup logs, migrations, opinions. Examples: k3s homelab setup, Kubernetes architecture in my cluster, Windows→Fedora migration, why I switched from nvim to Zed.

If the post names a specific product/tool/version as its subject → `tech`. If it would read identically regardless of which tool you use → `fundamentals`.

### Worked examples

- HTB Nibbles walkthrough → `["security", "writeups"]`
- OSCP info-gathering command dump → `["security", "cheatsheet"]`
- Hydra tool walkthrough (intro + commands + flag explanations) → `["security", "tool-guide"]`
- Nmap tool walkthrough → `["security", "tool-guide"]`
- Git rebase reference → `["tech", "cheatsheet"]`
- HDD vs SSD explainer → `["fundamentals"]`
- Windows→Fedora migration story → `["tech"]`
- Resume strategy doc → `["personal"]`
- Linux permissions explainer → `["fundamentals"]`
- AD exploitation guide (prose) → `["security"]`

## Decisions Made

- **7 tags across two axes, not 7 flat.** 4 subject tags (pick one) + 3 format tags (pick zero or one). Fixes discoverability: a security tool-guide is findable under `security` AND under `tool-guide`.
- **`tool-guide` added as a distinct format tag.** Tool tutorials (hydra, nmap) are different from terse cheatsheets — reader intent is "learn the tool", not "look up a flag".
- **No `infrastructure` or `product` tag.** Too thin on their own; folded into `tech`.
- **No `draft` tag.** Use Astro's `draft: true` frontmatter field instead (it's a status, not a topic).
- **No `web-security` sub-tag.** Folded into `security` — splitting creates thin tags.
- **No `cert-prep` tag.** Certificate material follows the normal subject rules — the cert boundary isn't a topic. Apply the rules per-file:
  - Most cert content (`password-attacks.md`, `attacking-common-applications.md`, `sqlmap-essentials.md`, etc.) → `security`.
  - Platform-specific docs (e.g. `introduction-to-academy.md`, anything that only makes sense inside HTB Academy) → `tech` (names a specific platform, fails the tool-agnostic test).
  - Pentest operational material (e.g. `setting-up.md` — penetration-testing VMs, VPN setup, on-site kit) → `security`.
  - Pure platform/tooling meta docs with no reusable content (e.g. GitBook template files) → excluded from migration.
- **No offensive/defensive split.** Current corpus is 95% offensive; revisit when defensive posts reach 5+.

## Frontmatter Template

```yaml
---
author: "Kayra"
pubDatetime: 2024-01-18T00:00:00Z   # see Date Policy below — do NOT use migration date
modDatetime: 2026-04-20T00:00:00Z   # set to migration date so "last updated" reflects the import
title: "..."
slug: "..."                          # must match filename minus .md
tags: ["security"]                   # one subject tag + optional format tag(s)
description: "..."
draft: false                         # true for stubs/skeletons
---
```

## Date Policy

The site sorts posts by `pubDatetime` in `src/utils/getSortedPosts.ts`, filters in `src/utils/postFilter.ts`, and emits RSS from `src/pages/rss.xml.ts`. Getting dates wrong breaks homepage ordering, archive pages, and the feed.

**Source reality:**
- The extracted `NotesHubGitBook-main/` directory is not a git repo and all 142 files share mtime `2024-01-18` (zip extraction). Unusable.
- **The user will provide the upstream GitHub repo URL.** The migration script will clone it and use git history for per-file dates. This is the canonical source of truth.
- Other source directories (`HomeLabBackUp4Checking/`, `Prism/`, etc.) have their own filesystem mtimes — usable as a fallback, or ideally their own git history if available.

**Rules:**

1. **GitBook migration batch (142 files, from cloned upstream):**
   - `pubDatetime` = `git log --diff-filter=A --follow --format=%aI -- <path> | tail -1` (first-commit date for the file — when it was actually authored)
   - `modDatetime` = `git log -1 --format=%aI -- <path>` (last-commit date for the file)
   - If `--follow` reveals a rename, the first-commit date of the original path wins — preserves authorship chronology across renames.
   - Result: posts sort by when they were actually written. Homepage, archive, and RSS all behave correctly.

2. **Non-GitBook source directories:**
   - If the directory is a git repo → same rule as (1): first-commit date for `pubDatetime`, last-commit date for `modDatetime`.
   - If not a git repo → per-file filesystem `mtime` for `pubDatetime`, migration run date for `modDatetime`.
   - Files with degenerate mtimes: fall back to the directory's oldest file mtime.

3. **Stubs / drafts:** still get a `pubDatetime` from git history, but `draft: true` keeps them out of the feed until fleshed out. When un-drafted, update `pubDatetime` to the un-draft date only if the content was substantially rewritten; otherwise keep the original authorship date.

4. **Manual override:** the user may hand-edit `pubDatetime` for specific posts when they have better knowledge than git (e.g., content pasted in from elsewhere that predates the commit). Not required.

5. **RSS impact:** on migration day, the feed emits the 142-post batch ordered by each post's real `pubDatetime` — spread across however long the GitBook repo existed. Subscribers see a historical import ordered chronologically, not a same-day flood. Clean outcome.

## Series Support (Schema Extension)

The taxonomy has no "series" tag by design — series is a structural concept, not a topic. For multi-part content like the 14-post Novaden homelab sequence (v0.1, v1.1, …), we extend the Astro content schema with two optional fields.

**Schema change in `src/content.config.ts`:**

```ts
series: z.string().optional(),
seriesOrder: z.number().optional(),
```

Additive only — existing posts unaffected.

**Usage:**

```yaml
tags: ["tech"]
series: "homelab"
seriesOrder: 0.1
```

**Current series:**

| Series slug | Source | Count | Subject tag |
|-------------|--------|-------|-------------|
| `homelab` | `SecondBrain/.../Novaden/v*.md` | 14 | `tech` |

Series pages (e.g. `/series/homelab`) can be added later as an Astro dynamic route; the schema extension is the prerequisite. Do not invent a `homelab` tag — series grouping replaces that need.

## Existing Off-Scheme Tags

Two posts already live in `src/data/blog/` with tags that predate this taxonomy:

- `tearing-it-down.md` — tags: `homelab`, `meta`
- `whats-cooking.md` — tags: `meta`

Neither `homelab` nor `meta` is part of the new scheme. Remap as part of this migration:

| Old tag | New tag(s) | Reasoning |
|---------|-----------|-----------|
| `homelab` | `tech` | Homelab is the canonical `tech` example in this plan — implementation-specific, named products (k3s, etc.). |
| `meta` (on `tearing-it-down`) | `personal` | The post is a reflection on why the author dismantled their homelab — content is about the author's decisions, not the blog itself. Pair with `tech` if homelab content is still the spine. |
| `meta` (on `whats-cooking`) | `personal` | A "what this blog is" intro is about the author. If future blog-meta posts accumulate (changelog, site updates), revisit — could earn a dedicated `meta` subject tag later. |

**Status: applied.** Both live posts have been updated to the new scheme:
- `src/data/blog/tearing-it-down.md` → `tags: ["tech", "personal"]` ✓
- `src/data/blog/whats-cooking.md` → `tags: ["personal"]` ✓

As of this writing, every post in `src/data/blog/` conforms to the taxonomy. No off-scheme tags remain. The migration script must preserve this invariant.

## Migration Effort Estimate

- Migration script: 30–60 min
- Script run on ~170 files: seconds
- Manual cleanup (GitBook `{% hint %}` shortcodes, `<figure>` blocks, broken image paths, relative `../` links): **4–8 hours**
- **Total: ~1 focused day**

## Special Handling

- **Stubs / skeletons** (~10 files in source): migrate with `draft: true`
- **Meta/template docs** (`cheat-sheets/for-developers.md`, `writeups/making-a-post.md`): exclude — GitBook platform docs, not content
- **Duplicate dirs** (`write-ups/` + `writeups/`, nested `basic-concepts/basic-concepts/`): consolidate during migration
- **Pure tool references** (9 files in `tools/`): tag `cheatsheet`; consider whether they belong in a separate `/reference` hub rather than the post feed

## Open Questions

- Should `tools/` content live in the post feed or a separate reference hub?
- If/when defensive security content grows past 5 posts, split `security` into `security-offensive` + `security-defensive`?

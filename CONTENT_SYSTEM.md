# Content System

This document defines **what** to write, **where it goes**, **how the pieces fit together**, and **how every post is tagged**. It is the canonical source of truth for content architecture and taxonomy on this blog.

It complements [CONTENT_FORMATTING.md](./CONTENT_FORMATTING.md), which defines how each individual element (code blocks, tables, prose voice, etc.) is formatted.

The goal: a repeatable system that scales across many certifications and topics, without duplicating knowledge or fighting taxonomy.

---

## The Three Post Archetypes

Every post on this blog is one of three things. Mixing them is the main thing to avoid.

| Archetype | Job | Voice | Lives in |
|---|---|---|---|
| **Atom** | Teach one concept | Third-person, instructional | `src/data/blog/<topic>-<concept>.md` |
| **Cheat sheet** | Quick-reference real commands for one task family | Third-person, terse | `src/data/blog/<topic>-cheatsheet.md` |
| **Cert review** | Meta / journey post about a certification | First-person | `src/data/blog/<cert>-review.md` |

Knowledge lives in **atoms**. Commands you'd type live in **cheat sheets**. Personal experience and course reviews live in **cert reviews**. Cert reviews link to atoms; they do not re-teach.

A fourth informal category exists: **personal / journey posts** (homelab series, life, career). These follow the same formatting and tagging rules as other posts but don't fit one of the three archetypes above.

---

## Atom Standard

### Purpose
Teach one concept. Evergreen, reusable across multiple certifications and contexts.

### When something earns an atom
Only when there is a **model to explain**: a why, a mental framework, gotchas, or behavior that surprises people. Concept-shaped things include:

- Permissions (owner/group/other, rwx, numeric, special bits)
- File descriptors and redirection
- TLS handshake, OAuth flow, container namespaces
- The filesystem hierarchy (what each directory is *for*)

### When something does NOT earn an atom
If your entry is `command: brief description` with no model to teach, it belongs in a cheat sheet, not an atom. Examples that are cheat-sheet-only:

- `pwd: shows current directory`
- `cd: changes directory`
- `clear: clears the screen`

A useful test: **if you removed all the commands from the atom draft, is there still meaningful content left?** If no, it's cheat-sheet material.

### Voice
Third-person, instructional. Write so the reader landing cold understands without context.

- Pick "you" or "we" and stay consistent within a single atom. Default to "you".
- Light first-person opinion is allowed sparingly when it adds real value (e.g. "in practice I almost always reach for `find` over `locate` because the database goes stale"). Maximum one or two per atom.

### Structure
- `## Introduction` opens with one short paragraph framing what the concept is and why it matters
- `## <Section>` for each sub-topic
- `### <Subsection>` for breakdowns inside a section
- End with a `> **Quick reference:**` blockquote linking to the relevant cheat sheet

### Use commands as illustration, not as content
When you mention a command inside an atom, show the canonical form once as an example of the concept. Do not list every flag, every variation, or every related command. Those belong in the cheat sheet.

**Example:**
> Numeric mode is faster once you internalize the math. To give a script standard executable permissions (owner: rwx, group/others: rx) you'd run:
> ```bash
> chmod 755 script.sh
> ```
> Why 755? Owner = 4+2+1 = 7, group = 4+0+1 = 5, others = 4+0+1 = 5.

The atom shows the *why*. The cheat sheet collects the *what*.

### One file vs splitting
**Default: one file per topic.** Do not pre-split. Let structure emerge from use.

Split into separate atoms when at least one of these is true:

- A section grows past ~500 words and is clearly self-contained
- You find yourself wanting to link to just that section from multiple cert reviews
- The single file becomes annoying to navigate while writing

Permissions and FD/redirection are likely future spinouts from `linux-foundations.md` — but only when they earn it, not preemptively.

---

## Cheat Sheet Standard

### Purpose
A reference page you keep open during a real task: exam, lab, engagement, daily work. Optimized for scanning, not learning.

### Entry format
Every command gets a single-line comment above it explaining **what you want**, then the real command with real values.

```bash
# Make a script executable
chmod +x script.sh

# Standard executable (owner: rwx, others: rx)
chmod 755 script.sh

# Private file, e.g. SSH keys
chmod 600 ~/.ssh/id_rsa
```

**Rules:**

- The comment is the index. You scan comments to find the line, not commands.
- Real examples, not placeholders. `chmod 600 ~/.ssh/id_rsa` over `chmod <mode> <file>`.
- Variations of the same command grouped together (the `-R` recursive form sits next to the non-recursive form).
- One short reference line per section if useful (e.g. `# Reference: r=4 w=2 x=1, order = owner group other`).

### Inclusion test
**Would I have actually typed this command in the last 12 months?** If no, cut it. Cheat sheets are not man pages. Exhaustive flag listings belong to `man`.

### Organize by task, not by command
In the moment of needing a cheat sheet, you know the *task* ("make this executable"), not the syntax. Section headings should reflect tasks ("Permissions and Ownership", "Process management", "Services"), not commands ("chmod", "ps", "systemctl").

### Granularity: when one cheat sheet, when many

> A cheat sheet covers what you'd keep open in one tab for one kind of task.

Start with one cheat sheet per topic (`linux-cheatsheet.md`, `kubernetes-cheatsheet.md`). Split out a sub-area when:

- You'd open it standalone in a real task ("I'm down a sed rabbit hole and don't need `chmod`")
- The section grows past ~one screen of scrolling
- A different cluster of tools serves a different moment (e.g. `text-processing-cheatsheet.md` for grep/sed/awk glue, separate from `linux-cheatsheet.md`)

Do not pre-split. Renaming markdown files is cheap.

### Dangerous commands get warnings
Use a blockquote immediately after the code block:

```markdown
> **Danger:** `rm -rf` has no undo. Double-check the path, especially when it contains variables. `rm -rf $UNSET_VAR/` becomes `rm -rf /`.
```

### Intro line
Every cheat sheet starts with a one-line intro that points to the relevant atom(s):

> A living quick-reference for the Linux commands I actually use. For the model behind any of this, see [Linux Foundations](/posts/linux-foundations).

---

## Cert Review Standard

### Purpose
A meta post about a certification: what it is, who it's for, your verdict, what was hard, how long it took. Pure review and journey. **Zero teaching content.** Teaching lives in atoms.

### Structure
- What the cert is, who it targets, format, duration
- What you learned that was genuinely new (link to atoms for each)
- What was already familiar (link to existing atoms)
- What was missing, weak, or annoying
- Your verdict: would you recommend it, and to whom
- Optional: a cram sheet of the must-knows, if you found yourself wanting one

Optional per-module journey entries are fine if you want them, but the curator role is the same: pointers, opinions, experience, never re-teaching the content.

### Voice
First-person. This is your story.

---

## The Overlap Rule

The atoms-vs-courses problem: every certification covers some material you've already written atoms for (Linux basics, containers, networking).

**The rule:** atoms are tagged by their topic, never by the cert that happened to teach them. Cert reviews **link to** atoms, never duplicate them.

- If a cert covers something your atom already explains, the cert review links to the atom.
- If the cert covers a gap your atom doesn't address, expand the atom or write a new atom for the gap.
- The cert review is the curator, not the content.

So a Linux explainer that you happened to write while studying CDP is still `[linux, notes]`, not `[cdp, linux, notes]`. The CDP cert review is `[cdp, certification]` and links to that atom. Writing OSCP later, you reuse the same atom; the new cert review links to it again.

---

## Tag Scheme

Tags split across **three independent axes**. A post can have one or more tags from each.

### Axis 1: Topic tags (1 or more, open vocabulary)
What the post is *about*. The primary filter readers use.

Examples in use today: `linux`, `security`, `tech`, `personal`, `fundamentals`, `homelab`, `web`, `containers`, `kubernetes`, `networking`, `iac`, `cloud`, `cdp`, `oscp`, `active-directory`, `htb`.

**Rules:**

- Every post has at least one topic tag.
- Pick the most specific tag that's useful. `linux` beats `tech` for a Linux-specific post. `kubernetes` beats `containers` when it's specifically k8s.
- Cert names ARE topic tags. A CDP cert review is tagged `cdp`. Content that incidentally appeared in the CDP curriculum is **not** — it's tagged by what it teaches (`linux`, `containers`, etc.).
- Open vocabulary, but resist thin tags. If you'd only ever use a tag for one post, fold it into a broader one. Promote a tag to standalone once it covers 5+ posts.

### Axis 2: Format tags (0 or 1)
The *shape* of the post. Optional.

| Tag | When to add | Example |
|-----|-------------|---------|
| `writeups` | Step-by-step compromise of a specific machine or lab, with console output | HTB Nibbles compromise |
| `cheatsheet` | Terse reference, mostly command dumps and syntax tables, assumes you know the tool | Linux cheat sheet |
| `tool-guide` | Tutorial that teaches a specific tool end-to-end (intro prose + commands + flag explanations) | A from-scratch hydra or nmap walkthrough |

**`cheatsheet` vs `tool-guide`:** both cover tools, but reader intent differs. Cheat sheets are for reference while working ("what flag do I need?"). Tool guides are for learning ("how do I use this tool?"). If a file opens with "X is a Y used for Z" and walks through usage with context, it's `tool-guide`. If it's mostly commands with minimal prose, it's `cheatsheet`.

Format tags are mutually exclusive in practice. A post is `writeups`, `cheatsheet`, OR `tool-guide`, not two.

### Axis 3: Meta tags (0 or 1)
The *role* of the post in the content system.

| Tag | When to add |
|-----|-------------|
| `notes` | Knowledge content. Atoms and cheat sheets. The post teaches a concept, explains a model, or serves as reference. |
| `certification` | Cert reviews. The post is about your experience taking a certification. |

Meta tags are mutually exclusive: a post is either `notes` (knowledge) or `certification` (cert review), not both.

Personal posts, journey posts (homelab series), and life content get **no meta tag**. The absence of a meta tag signals "this is not knowledge content or a cert review."

---

## Tag Assignment Rules

Numbered for use as a decision aid when you're tagging a post:

1. **Pick the topic tag(s) first.** Always at least one. Pick the most specific useful one. Add more if multiple topics genuinely apply (e.g. `[linux, fedora]` for a Fedora-specific Linux post).
2. **Add a format tag only if the post is clearly a writeup, cheat sheet, or tool guide.** Most atoms don't get a format tag.
3. **Add the meta tag if applicable:** `notes` for atoms and cheat sheets; `certification` for cert reviews. Personal and journey posts get no meta tag.
4. **Format tags and meta tags never stand alone.** Every post has at least one topic tag.
5. **`cheatsheet` vs `tool-guide`:** apply the reader-intent test in the section above.
6. **Series go in `series:` + `seriesOrder:` frontmatter, never as tags.** No `homelab` tag — the homelab series is structurally grouped by the series field, with `tech` as the topic tag.
7. **Drafts use Astro's `draft: true` frontmatter, not a tag.** Status is not a topic.

---

## Worked Examples

| Content | Tags |
|---|---|
| Linux foundations atom | `[linux, notes]` |
| Linux cheat sheet | `[linux, cheatsheet, notes]` |
| HTB Nibbles writeup | `[security, htb, writeups, notes]` |
| OSCP info-gathering command dump | `[security, oscp, cheatsheet, notes]` |
| Hydra from-scratch walkthrough | `[security, tool-guide, notes]` |
| Nmap tool walkthrough | `[security, networking, tool-guide, notes]` |
| Git rebase reference | `[tech, cheatsheet, notes]` |
| AD exploitation guide (prose explainer) | `[security, active-directory, notes]` |
| HDD vs SSD explainer | `[fundamentals, notes]` |
| TCP/IP explainer | `[networking, fundamentals, notes]` |
| CDP cert review | `[cdp, devsecops, certification]` |
| OSCP cert review | `[oscp, security, certification]` |
| Windows-to-Fedora migration story | `[linux, fedora, personal]` |
| Resume strategy | `[personal]` |
| "What's cooking" blog intro | `[personal]` |
| Tearing it down (homelab retrospective) | `[tech, personal]` |
| Homelab v1.0 (part of series) | `[tech]` + `series: homelab, seriesOrder: 1.0` |

Note: `fundamentals` is still a useful topic tag for tool-agnostic explainers that don't fit a more specific topic (e.g. HDD vs SSD). But for things that DO have a specific topic (`linux`, `kubernetes`, `networking`), use the specific one.

---

## Decisions Made

These document *what was decided and why*, including rejected alternatives. They exist to prevent re-litigating settled questions.

- **Open topic vocabulary** (not a closed subject set). Closed 4-subject vocab (`fundamentals`/`security`/`tech`/`personal`) was too coarse: `linux` is more useful than `fundamentals` for filtering. Open vocab is more granular, future-proof, and aligns with how readers actually search.
- **Three independent axes** (topic + format + meta). Meta tags carry signal orthogonal to subject and format. They distinguish "this is knowledge content" from "this is personal" even when both could share a topic tag.
- **`notes` meta tag.** Separates knowledge content from personal/journey posts. Without it, a `[linux]`-tagged Linux explainer and a `[linux]`-tagged "my Linux journey" post are indistinguishable.
- **`certification` meta tag.** Separates cert reviews from other content. Lets readers find all cert reviews via one tag.
- **Cert names ARE topic tags for cert reviews.** A CDP cert review is `[cdp, certification]`. But content that incidentally appeared in the CDP curriculum is NOT tagged `cdp` — it's tagged by what it teaches. This keeps atoms reusable across certs.
- **No `cert-prep` tag.** The cert boundary is not a topic. Atoms tag by their actual topic (`linux`, `active-directory`, etc.).
- **No `homelab` tag.** Homelab content uses `series: homelab` + `seriesOrder:` frontmatter, tagged `tech`. Series grouping replaces the tag need.
- **No `draft` tag.** Use Astro's `draft: true` frontmatter. Status is not a topic.
- **No `web-security` sub-tag.** Folded into `security` until web content reaches 5+ posts. Splitting creates thin tags.
- **No offensive/defensive security split.** Current corpus is 95% offensive; revisit when defensive posts reach 5+.
- **No `infrastructure` or `product` tag.** Too thin on their own; folded into `tech`.
- **Format tags and meta tags never stand alone.** Every post has at least one topic tag.

---

## Frontmatter Template

```yaml
---
author: Kayra
pubDatetime: 2026-05-27T00:00:00Z
modDatetime: 2026-05-27T00:00:00Z   # optional; set when significantly revised
title: "..."
slug: "..."                          # must match filename minus .md
tags: ["linux", "notes"]             # topic + optional format + optional meta
description: "One concrete sentence describing what's in this post."
draft: false                         # true for stubs / work-in-progress
series: "homelab"                    # optional, only for series posts
seriesOrder: 1.0                     # optional, only for series posts
featured: false
---
```

---

## Series Support

The taxonomy has no "series" tag by design. Series is a **structural** concept, not a topic. For multi-part content like the 14-post Novaden homelab sequence (v0.1, v1.1, …), the Astro content schema has two optional fields.

**Schema** (in `src/content.config.ts`):

```ts
series: z.string().optional(),
seriesOrder: z.number().optional(),
```

**Usage:**

```yaml
tags: ["tech"]
series: "homelab"
seriesOrder: 0.1
```

**Current series:**

| Series slug | Source | Count | Topic tag |
|-------------|--------|-------|-----------|
| `homelab` | `SecondBrain/.../Novaden/v*.md` | 14 | `tech` |

Series pages (e.g. `/series/homelab`) are an Astro dynamic route; the schema extension is the prerequisite. Do not invent a topic tag for a series — the series field replaces that need.

---

## Date Policy

The site sorts posts by `pubDatetime` in `src/utils/getSortedPosts.ts`, filters in `src/utils/postFilter.ts`, and emits RSS from `src/pages/rss.xml.ts`. Getting dates wrong breaks homepage ordering, archive pages, and the feed.

### For ongoing new posts

- `pubDatetime`: set to the date you publish the post.
- `modDatetime`: set when you significantly revise (not for typo fixes). Optional.

### For the pending migration batch

Source reality:

- The extracted `NotesHubGitBook-main/` directory is not a git repo and all 142 files share an mtime of `2024-01-18` (zip extraction artifact). Unusable as-is.
- The upstream GitHub repo will be cloned by the migration script and git history used for per-file dates. This is the canonical source of truth.
- Other source directories (`HomeLabBackUp4Checking/`, `Prism/`, etc.) have their own filesystem mtimes — usable as fallback, or ideally their own git history if available.

Rules:

1. **GitBook migration batch (from cloned upstream):**
   - `pubDatetime` = `git log --diff-filter=A --follow --format=%aI -- <path> | tail -1` (first-commit date for the file)
   - `modDatetime` = `git log -1 --format=%aI -- <path>` (last-commit date)
   - If `--follow` reveals a rename, the first-commit date of the original path wins. Preserves authorship chronology across renames.
   - Result: posts sort by when they were actually written. Homepage, archive, and RSS all behave correctly.

2. **Non-GitBook source directories:**
   - If the directory is a git repo, same rule as above.
   - If not a git repo, per-file filesystem `mtime` for `pubDatetime`, migration run date for `modDatetime`.
   - Files with degenerate mtimes: fall back to the directory's oldest file mtime.

3. **Stubs and drafts:** still get a `pubDatetime` from git history, but `draft: true` keeps them out of the feed until fleshed out. When un-drafted, update `pubDatetime` to the un-draft date only if the content was substantially rewritten; otherwise keep the original authorship date.

4. **Manual override:** hand-edit `pubDatetime` for specific posts when you have better knowledge than git (e.g., content pasted in from elsewhere that predates the commit).

5. **RSS impact:** on migration day, the feed emits the 142-post batch ordered by each post's real `pubDatetime`, spread across however long the GitBook repo existed. Subscribers see a historical import ordered chronologically, not a same-day flood.

---

## Cross-linking

- **Atom to cheat sheet:** every atom ends with `> **Quick reference:** [Linux Cheat Sheet](/posts/linux-cheatsheet)` pointing to the relevant cheat sheet.
- **Cheat sheet to atom:** every cheat sheet's intro line points to the related atom(s).
- **Cert review to atoms:** every concept covered in the cert gets a link to its atom.
- **URL pattern:** `/posts/<slug>` (set by `slug:` in frontmatter, decoupled from filename).

Wiki-style cross-references between atoms (e.g. linking from a `linux-permissions.md` atom to `linux-foundations.md`) are encouraged when they help.

---

## File Layout

For now: **flat** under `src/data/blog/`, matching the existing convention. Naming patterns:

- Atoms: `<topic>-<concept>.md` (e.g. `linux-foundations.md`, `linux-permissions.md`, `kubernetes-rbac.md`)
- Cheat sheets: `<topic>-cheatsheet.md` (e.g. `linux-cheatsheet.md`, `kubernetes-cheatsheet.md`)
- Cert reviews: `<cert>-review.md` (e.g. `cdp-review.md`, `oscp-review.md`)
- Series posts: `<series-slug>-<order>-<short-title>.md` (existing pattern, e.g. `homelab-v1-0-from-server-to-data-center.md`)

Subfolders (`notes/`, `certifications/`) are a future option when post count justifies it. Same principle as cheat sheet granularity: do not pre-organize.

---

## Workflow

**Starting a new topic from scratch (e.g., starting Kubernetes notes):**

1. Start a single atom (`kubernetes-foundations.md`) and write conceptual material as you learn.
2. In parallel, start an empty cheat sheet (`kubernetes-cheatsheet.md`).
3. As you write the atom, every command you'd actually type goes into the cheat sheet too (under the right section, with a "# what you want" comment above it).
4. When the atom grows past ~500 words for a sub-area that's clearly self-contained, split it into its own atom (`kubernetes-rbac.md`, `kubernetes-networking.md`).
5. When the cheat sheet gets dense enough in one sub-area that it deserves a dedicated reference, split it (`kubectl-cheatsheet.md`).
6. Never write a cheat sheet from scratch later. Build it as a byproduct of writing atoms.

**Writing a cert review (e.g., after finishing CDP):**

1. List every concept the cert covered.
2. For each, check: does an atom exist? If yes, link to it. If no, write the missing atom first (tagged by topic, not by cert).
3. Write the review post with links, opinions, and experience. No teaching.
4. Tag it `[<cert>, certification]` plus any relevant topic tags (e.g. `devsecops`, `security`).

---

## What NOT to Do

- **Don't duplicate teaching across cert reviews.** Knowledge lives in atoms exactly once.
- **Don't write a mega cheat sheet** covering everything. It rots, becomes unfindable, and tanks SEO.
- **Don't write an atom entry for a tool with no concept** (`pwd: shows current directory` is cheat-sheet content, not an atom).
- **Don't pre-design taxonomy.** Folder structure, cheat sheet splits, atom splits all emerge from use, not planning.
- **Don't include commands you'd never type in real life.** Cheat sheets are not exhaustive flag references; that's what `man` is for.
- **Don't write first-person in atoms** beyond the occasional opinion. Atoms are reference; first-person dates them.
- **Don't tag atoms with cert names.** Atoms tag by topic. Only cert reviews get cert tags.
- **Don't invent thin tags.** If a tag would apply to one post, fold it into a broader one. Promote later if it earns 5+ posts.
- **Don't add `## Remediation`** to atoms or cheat sheets. That section is for security/vuln posts only.

---

## Pending Migration

The blog corpus is partially migrated. The remaining batch is pending.

### Scope

- **Source (security):** `NotesHubGitBook-main/` (142 markdown files, security/infosec).
- **Source (general):** `HomeLabBackUp4Checking/`, `infra-cluster-manifests/`, `Prism/`, `TouchGrass/`, `notfromsugar/`, `AhmedHamdyConsultant/`, `expense-tracking/`, `VisaStressRelief/`, `strategic_recommendations.txt` (~30 files).
- **Target:** `src/data/blog/` (flat directory, Astro collection).
- **Excluded:** `brainspill`/`brainspill1` (duplicates), Dendron/ClaudeCode source trees, AnkiDecks (CSVs), Scripts, encrypted ransomware files, binary backups.
- **Archived content:** none detected in source (no archive folders, no `archived:`/`draft:` frontmatter).

### Special Handling

- **Stubs / skeletons** (~10 files in source): migrate with `draft: true`.
- **Meta/template docs** (`cheat-sheets/for-developers.md`, `writeups/making-a-post.md`): exclude. GitBook platform docs, not content.
- **Duplicate dirs** (`write-ups/` + `writeups/`, nested `basic-concepts/basic-concepts/`): consolidate during migration.
- **Pure tool references** (9 files in `tools/`): tag with the relevant topic + `cheatsheet` + `notes`. Consider whether they belong in a separate `/reference` hub rather than the post feed (see Open Questions).

### Migration Effort Estimate

- Migration script: 30–60 min
- Script run on ~170 files: seconds
- Manual cleanup (GitBook `{% hint %}` shortcodes, `<figure>` blocks, broken image paths, relative `../` links): **4–8 hours**
- Total: ~1 focused day

### Open Questions

- Should `tools/` content live in the post feed or a separate reference hub?
- If/when defensive security content grows past 5 posts, split `security` into `security-offensive` + `security-defensive`?
- What's the upstream GitHub repo URL for the GitBook source (needed for date policy)?

---

## Summary Checklist

For every new post:

- [ ] Archetype is clear: atom, cheat sheet, cert review, or personal/journey
- [ ] If atom: there is a concept being taught (not just commands listed)
- [ ] If cheat sheet: every command has a `# what you want` comment above it, with real values
- [ ] If cert review: zero teaching; only review + links to atoms
- [ ] Voice matches archetype (third-person for atoms/cheat sheets, first-person for cert reviews and journeys)
- [ ] At least one topic tag, picked at the most specific useful level
- [ ] Format tag (`writeups`/`cheatsheet`/`tool-guide`) added only if the shape matches
- [ ] Meta tag added: `notes` for atoms/cheat sheets, `certification` for cert reviews, nothing for personal/journey
- [ ] No format or meta tag standing alone (every post has at least one topic tag)
- [ ] Series posts use `series:` + `seriesOrder:` frontmatter, not a series tag
- [ ] Atom links to its cheat sheet; cheat sheet links back to its atom(s)
- [ ] Frontmatter is complete and `description` is one concrete sentence
- [ ] Follows [CONTENT_FORMATTING.md](./CONTENT_FORMATTING.md) for prose, voice, tables, code, and blockquotes

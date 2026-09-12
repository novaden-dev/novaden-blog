# Content Audit Plan

Every file gets read by a human. This says in what order, and what to decide
about each one.

**Order: this repo, then GitBook, then OSCP.** The reason is one-directional:
every GitBook and OSCP decision is *"does this merge into, replace, or
supplement what the blog already has?"*, and that question has no answer until
the blog is settled. Read the sources first and you read all 242 of their files
twice.

**Within each source: by topic cluster, not file by file.** Content judgments
are comparative. You cannot decide whether the iOS checklist earns its own file
without the Android one open beside it, or whether `secure-code-review-by-stack`
should exist without `secure-code-review-methodology` next to it. Alphabetical
order means opening the same file four times and closing nothing. One cluster is
one sitting, and a sitting ends with decisions that stay made.

| Phase | Source | Files to read | Words |
|---|---|---:|---:|
| A | this repo (`src/data/blog`) | 55 | 143,071 |
| B | GitBook (importable surface) | 67 | 60,596 |
| C | GitBook `archive-backup-bin/` | 111 | skim only |
| D | OSCP vault | ~175 | after its cleanup |

Not read at all: 46 GitBook nav files, templates, and section stubs under 150
words. `SUMMARY.md` is read once, as a map of how the old site was organised,
never as content.

---

## The verdict vocabulary

One of these per file. Write it in the checkbox line as you go.

| Verdict | Means |
|---|---|
| **keep** | Publishes as is. Maybe a typo pass, nothing structural. |
| **improve** | The content is right, something around it is not: description, tags, structure, formatting. |
| **merge** | Folds into another file. Name which one, and which is the survivor. |
| **split** | Two reader needs in one file. Name the split. |
| **archive** | Real, historical, stays readable, stops being maintained. |
| **remove** | Delete. Nothing links to it and nothing is lost. |
| **review** | Cannot decide alone. Note what the blocker is and move on, do not stall the sitting. |

## The four questions per file

Ask them in this order. The first "no" usually settles it.

1. **Who opens this, and what do they want?** If you cannot answer in one
   sentence, the file has a problem no formatting fix will solve.
2. **Does another file already answer that?** If yes: same need, or genuinely
   different scope? Same need means merge. Different scope means both stay and
   the titles and intros must say how they differ.
3. **Is it finished?** Does it end, or does it stop?
4. **Does it still hold?** Written a year ago and still true, or written a year
   ago and now wrong? Wrong-but-historical is `archive`, not `remove`.

Record the answer, not the deliberation. `content-audit/INVENTORY.md` already
carries the machine signals per file (overlap scores, orphan status, formatting
deviations, credential-shaped strings). Use it as the second opinion, not the
first.

---

# Phase A: this repo (55 files)

Ordered so that the cheapest calibration comes first and the decisions that
depend on sharp criteria come last.

## A1. personal / homelab (10 files, ~12,000 words) START HERE

Your own story, so you read fast, and it holds the only two live defects. You
calibrate what "audit" means on material you know cold, before spending it on a
16,000-word checklist.

Read chronologically. It is a narrative and it only makes sense in order.

- [ ] `homelab-v0-1-why-i-bought-a-mini-pc-instead-of-therapy.md` (1,105w)
- [ ] `homelab-v1-0-from-server-to-data-center.md` (1,344w)
- [ ] `homelab-v1-1-the-great-wall-of-fire.md` (1,193w)
- [ ] `homelab-v1-2-the-supply-chain.md` (637w)
- [ ] `homelab-v1-3-the-silent-killers.md` (1,175w)
- [ ] `homelab-v1-4-the-governance-wall.md` (1,278w)
- [ ] `homelab-v1-5-real-governance.md` (1,367w)
- [ ] `tearing-it-down.md` — **EMPTY.** Frontmatter only, zero words, and
      `featured: true`, so it is pinned on the homepage right now and renders a
      blank page. Decide: write it, unpublish it, or delete it.
- [ ] `novaden-v2-the-useful-one.md` — **1,404 of its 1,831 words are verbatim
      from `fed-fed-fedora.md`**: the Lenovo repair story, the KDE install, the
      whole nitpicks section, inside a post about a homelab. It also embeds
      `/images/migrated/fedora-01-bluescreen.png`. Read it next to the file
      below, not on its own.
- [ ] `fed-fed-fedora.md` (2,288w) — the source of that text. Also collides by
      name with `other/fed-fed-fedora.md` in GitBook, so settle which one is
      canonical here and Phase B inherits the answer.

**Decisions this sitting must produce:** what happens to the empty file; which
of the two Fedora-text posts is real and what the other becomes; whether the
homelab collection's two `supplementary` placements are right (I added those and
wrote their `note:` lines, including one describing a retrospective that does not
exist).

## A2. ai / llm (3 files, ~10,200 words)

No flags on any of them. A clean cluster right after a broken one tells you
whether your criteria are actually discriminating or just finding fault.

- [ ] `llm-foundations.md`
- [ ] `owasp-llm-top-10.md`
- [ ] `owasp-agentic-top-10.md` — currently `draft: true`. Decide if that is
      still true.

## A3. devsecops + tooling (10 files, ~11,000 words)

Five `-foundations` / `-cheatsheet` pairs. Read each pair together, back to
back. The real question for the cluster is whether the atom/cheatsheet split
described in `CONTENT_SYSTEM.md:34` is holding up in practice or whether it has
become a habit.

- [ ] `linux-foundations.md` + `linux-cheatsheet.md`
- [ ] `docker-foundations.md` + `docker-cheatsheet.md`
- [ ] `git-foundations.md` + `git-cheatsheet.md`
- [ ] `ssh-foundations.md` + `ssh-cheatsheet.md`
- [ ] `devsecops-foundations.md` + `devsecops-cheatsheet.md` — the cheatsheet
      does not link back to its atom, the only pair that breaks the rule.

## A4. pentest process (5 files, ~18,600 words)

Two of these collide by name with GitBook files. Settling them here means Phase
B inherits the answers instead of reopening them.

- [ ] `penetration-testing-process.md` (701w) — **name collision** with
      `study-notes/penetration-tester-htb-cpts/penetration-testing-process.md`
      (309w). Titled "Penetration Testing Fundamentals" but named for a process.
- [ ] `web-information-gathering.md` (1,000w) — **name collision** with the
      GitBook file of the same name (1,035w). The GitBook copy is *longer*.
- [ ] `network-pentest-methodology.md` (5,454w)
- [ ] `api-pentest-methodology.md` (13,535w)
- [ ] `ftp.md` — the only single-protocol note in the corpus. Does it belong
      here, in a services reference, or nowhere?

## A5. secure code review / appsec (5 files, ~17,400 words)

- [ ] `secure-code-review-methodology.md` (5,080w)
- [ ] `secure-code-review-by-stack.md` (3,033w) — read immediately after.
      One process file and one stack file, or one file?
- [ ] `threat-modeling.md` (30 em dashes left in prose) — **needs a structural
      decision**: it nests three levels deep using `#`/`##`/`###`, but
      `CONTENT_FORMATTING.md` allows only `##`/`###`. Demoting produces the
      `####` the same rule bans. Either it is really several files, or the rule
      needs to allow three levels.
- [ ] `application-architecture-layers.md`
- [ ] `cryptography-foundations.md` — no "Quick reference" pointer, which the
      atom rule requires.

## A6. mobile (8 files, ~35,100 words)

Big but self-contained: no GitBook file collides with any of it, so nothing
here can be spoiled by a later decision. Read foundations first to set the
baseline, then the two large checklists back to back.

- [ ] `mobile-security-testing-foundations.md` (2,213w) — the orientation
- [ ] `mobile-app-security-testing.md` (10,775w, Android)
- [ ] `mobile-app-security-testing-ios.md` (10,508w, iOS) — **69% subject
      similarity with the Android one.** Almost certainly correct as two files,
      per-platform, but that is the call to make explicitly rather than assume.
- [ ] `android-fundamentals.md` (1,640w)
- [ ] `android-cheatsheet.md` (651w)
- [ ] `ios-analysis-setup.md` (1,628w)
- [ ] `frida-on-device.md` (756w)
- [ ] `android-security-testing-checklist-legacy.md` (8,563w) — already
      `draft: true` and described as superseded. Confirm `archive` or `remove`,
      and whether anything in it never made it into the MASVS version.

## A7. web app testing (14 files, ~38,900 words) LAST

Biggest cluster, three GitBook collisions, and the corpus's hardest overlap
call. It goes last because by now the criteria from six previous sittings are
sharp, which is what this one needs.

Read the two checklists together first, decide, then the single-topic files.

- [ ] `web-application-pentest-methodology.md` (14,415w, 15 numbered sections)
- [ ] `web-application-security-testing.md` (9,861w, REC/AUT/AUZ prefixes)
      — **53% subject similarity, 0% shared prose.** Written five weeks apart,
      both "per-control checklist with pass condition, fail condition, evidence
      to capture". Zero shared section headings only because the naming schemes
      differ. Same reader need and one must go, or genuinely different
      purposes and both titles must say so.
- [ ] `os-command-injection.md` — **name collision** (GitBook copy is 131w
      vs 542w here)
- [ ] `file-upload-vulnerabilities.md` — **name collision**
- [ ] `information-disclosure.md` — **name collision**
- [ ] `path-directory-traversal.md`
- [ ] `nosql-injection.md`
- [ ] `server-side-request-forgery.md`
- [ ] `cross-site-request-forgery.md`
- [ ] `race-conditions.md`
- [ ] `http-request-smuggling.md`
- [ ] `http-security-headers.md`
- [ ] `html5-security-controls.md`
- [ ] `web-cache-deception.md`

**Cluster question:** eleven single-vulnerability files plus two mega
checklists. Do the checklists link out to the single files, or restate them? If
they restate them, one of the two shapes is redundant.

---

# Phase B: GitBook (67 files, ~60,600 words)

Walked through clusters, not through GitBook's folders. Its folder names are
provenance, not categories: `study-notes/penetration-tester-htb-cpts/` says
where a file came from, not what it is about.

## B1. The collisions (6 files) FIRST

Read each next to the blog file you already settled in Phase A. The Phase A
decision usually dictates the answer here in under a minute.

- [ ] `other/fed-fed-fedora.md` (2,077w) vs blog `fed-fed-fedora.md` (2,288w)
- [ ] `study-notes/.../penetration-testing-process.md` (309w) vs blog (701w)
- [ ] `study-notes/.../web-information-gathering.md` (1,035w) vs blog (1,000w)
- [ ] `basic-concepts/.../os-command-injection.md` (131w) vs blog (542w)
- [ ] `basic-concepts/.../path-traversal-directory-traversal.md` (172w)
- [ ] `basic-concepts/.../authentication.md` (235w)

## B2. fundamentals (14 files, ~15,200 words) — the reason to import at all

This is the subject area the blog does not have: networking, Windows, Active
Directory, GRC, and hands-on security-product labs. Nothing here competes with
an existing file, so these are close to pure addition.

- [ ] `fundamentals/active-directory.md` (2,758w)
- [ ] `fundamentals/introduction-to-web-applications.md` (2,287w)
- [ ] `fundamentals/linux-fundamentals.md` (2,090w) — compare against the blog's
      `linux-foundations.md` before deciding
- [ ] `fundamentals/networking-fundamentals.md` (1,479w)
- [ ] `fundamentals/windows-fundamentals.md` (1,194w)
- [ ] `fundamentals/governance-risk-and-compliance-grc.md` (832w)
- [ ] `fundamentals/other-useful-concepts/regular-expressions-regex.md` (283w)
- [ ] `fundamentals/cyber-security-products/README.md` (1,413w) — a section
      index carrying real content, not nav
- [ ] `fundamentals/cyber-security-products/fortigate-firewall.md` (987w)
- [ ] `fundamentals/cyber-security-products/lab-setup.md` (476w)
- [ ] `.../iam-lab.md` (369w), `.../pam-lab.md` (356w), `.../dlp-lab.md` (355w),
      `.../mdm-lab.md` (344w) — four labs, one shape. One file or four?

## B3. study-notes / HTB CPTS (25 files, ~27,800 words)

The biggest single body, and it needs one decision before any per-file
decisions: **is this a collection, or is it raw material?**

- As a **collection**: a `handbook` in `src/data/collections/`, kept as course
  notes with their own reading order, provenance intact.
- As **raw material**: each file merges into the matching blog atom, and the
  CPTS framing disappears, per the Overlap Rule in `CONTENT_SYSTEM.md:171`
  ("atoms are tagged by their topic, never by the cert that happened to teach
  them").

Decide that first. It changes all 25 verdicts and probably takes ten minutes.

Then read in this order, largest first, since the big ones set the pattern:

- [ ] `web-exploitation/sql-injection.md` (3,170w)
- [ ] `exploitation-and-lateral-movement/active-directory-enumeration-and-attacks-tbc.md` (2,899w)
- [ ] `post-exploitation/windows-privilege-escalation-tbc.md` (2,005w)
- [ ] `exploitation-and-lateral-movement/password-attacks.md` (1,955w)
- [ ] `post-exploitation/linux-privilege-escalation.md` (1,921w) — **45% subject
      overlap** with `certificates/tib3rius-privilege-escalation/linux-privilege-escalation.md`
- [ ] `reconnaissance.../footprinting-just-do-formatting.md` (1,814w)
- [ ] `documentation-and-reporting.md` (1,725w)
- [ ] `web-exploitation/web-attacks-check.md` (1,640w)
- [ ] `web-exploitation/file-inclusion.md` (1,314w)
- [ ] `reconnaissance.../using-the-metasploit-framework.md` (1,307w)
- [ ] `web-exploitation/file-upload-attacks.md` (921w)
- [ ] `web-exploitation/attacking-common-applications-check.md` (884w)
- [ ] `web-exploitation/cross-site-scripting-xss.md` (710w)
- [ ] `reconnaissance.../shells-and-payloads.md` (679w)
- [ ] `exploitation.../attacking-common-services-just-do-formatting.md` (670w)
- [ ] `web-exploitation/command-injection.md` (613w)
- [ ] `exploitation.../pivoting-tunneling-and-port-forwarding.md` (524w)
- [ ] `web-exploitation/attacking-web-applications-with-ffuf-check.md` (514w)
- [ ] `web-exploitation/login-bruteforcing.md` (493w)
- [ ] `web-exploitation/using-web-proxies-check.md` (254w)
- [ ] `reconnaissance.../network-enumeration-with-nmap-continue-here.md` (224w)
- [ ] `reconnaissance.../file-transfers.md` (119w)
- [ ] `reconnaissance.../vulnerability-scanning-check.md` (80w)
- [ ] `certificates/tib3rius-privilege-escalation/linux-privilege-escalation.md` (1,998w)

Note the filenames: `-check`, `-tbc`, `just-do-formatting`, `continue-here`.
Seven files carry a to-do in their own name. That is the author telling you they
are unfinished, and it is worth trusting.

## B4. write-ups (4 files, ~3,100 words)

The first real test of whether a **context** entity is needed: a CTF event
edition, an HTB machine, and two cert experiences are four different kinds of
"a specific thing that happened", none of which is a topic.

- [ ] `write-ups/certificates/web-application-penetration-tester-extreme-ewptxv3.md` (1,095w)
- [ ] `write-ups/certificates/certified-professional-penetration-tester-ecpptv3.md` (741w)
      — both are `cert-review` category, of which the blog currently has zero
- [ ] `write-ups/hack-the-box-machines/linux/code.md` (761w)
- [ ] `write-ups/ctf-events/cyber-hub-2025-ctf.md` (501w)

## B5. tools (6 files, ~2,900 words)

`CONTENT_SYSTEM.md:450` already lists this as an open question: post feed, or
separate reference hub?

- [ ] `tools/ffuf.md` (1,130w) — 73% subject overlap with an archived file
- [ ] `tools/nessus.md` (513w)
- [ ] `tools/john-the-ripper.md` (454w)
- [ ] `tools/nmap.md` (423w)
- [ ] `tools/hydra.md` (134w) — stub
- [ ] `tools/understanding-projects.md` + `writeups/understanding-projects.md`
      — GitBook template docs, duplicated. Expect `remove`.

## B6. learning-process (3 files, ~4,200 words)

Another subject the blog does not cover, and the least security-shaped material
in the corpus. Worth reading as a set: it is either a small collection or three
loose essays.

- [ ] `learning-process/learning-process.md` (2,366w)
- [ ] `learning-process/learning-dependencies.md` (1,125w)
- [ ] `learning-process/learning-mindset.md` (756w)

## B7. other + leftovers (7 files, ~2,000 words)

- [ ] `other/data-structure-and-algorithms-dsa.md` (422w)
- [ ] `other/leet-code/problem-01-two-sum.md` (255w)
- [ ] `other/leet-code/quick-guide-big-o-notation.md` (192w) — is LeetCode a
      subject this publication has, or the start of one it does not want?
- [ ] `basic-concepts/.../business-logic-vulnerabilities.md` (298w) — 79%
      shared prose with an archived permissions file
- [ ] `basic-concepts/.../linx-fundamentals.md` (177w) — note the typo in the
      filename
- [ ] `basic-concepts/inviting-members.md` (57w) — GitBook furniture
- [ ] `cheat-sheets/for-developers.md` (152w) — template

## B8. Read once as a map, never as content

- [ ] `SUMMARY.md` (667w) — the old table of contents. Read it to see how the
      material was organised and what that says about how you thought about it.
      It does not become a page.
- [ ] `README.md` (294w) — the old landing page.

---

# Phase C: GitBook archive-backup-bin (111 files) — skim only

60% of the GitBook repo. The directory name is the previous verdict. Do not
read these one by one until you have decided whether you want anything from the
pile at all.

Skim the top-level folders and answer one question each: *is there anything in
here that exists nowhere else?*

```
for508-advanced-incident-response...    certified-bug-bounty-hunter-cbbh
windows-fundamentals-tryhackme          certified-penetration-testing-specialist-cpts
port-swigger-web-penetration-testing    certified-threat-hunting-professional-ecthpv2
linux-fundamentals-tryhackme            active-directory-tryhackme
htb-archived-write-ups-check            oscp/  getting-started/  cheat-sheets/
```

Only if the answer is yes for a folder does it earn a per-file read, and it
joins the Phase B cluster it belongs to rather than getting its own pass.

Also here, unread and outside git: `_TO_BE_DELETED_network-notes-backup-2026-07-26/`
in this repo, holding ~10 notes (`nmap.md`, `rdp.md`, `databases.md`,
`dns.md`, `email-services.md`, and others). It is gitignored, so if it is the
only copy it is one `rm -rf` from gone. Check that before anything else in this
phase.

---

# Phase D: OSCP vault (~175 files) — after its own cleanup

Not now, by your call: the vault is mid-cleanup and reading it in that state
means reading it twice.

Its shape when the time comes, and the clusters are already obvious from the
folders:

| Area | Files | Note |
|---|---:|---|
| `Labs/` | 72 | Machine write-ups. Real lab IPs by design, per its `AGENTS.md`. |
| `Techniques/` | 62 | The atoms. Will collide heavily with Phase B3 material. |
| `Tools/` | 30 | Collides with Phase B5. |
| `Methodology/` | 6 | The spine. Read these first when the phase starts. |
| `Cheatsheets/` | 1 | `Quick Reference.md` |
| `Attachments/` | 683 PNGs | Screenshots. |

Two things must happen before a single OSCP file is published, regardless of
audit order:

1. **A screenshot scrub.** 683 images from live lab machines. The vault's own
   rules say passwords get blurred, but that is a rule about the notes, not a
   guarantee about the images.
2. **A wikilink and attachment rewrite.** `[[Note]]` and `![[image.png]]` are
   Obsidian syntax that means nothing to Astro, and folder-index links like
   `[[Labs]]` have no target here at all.

Read `Methodology/` first (6 files, the spine), then `Techniques/` against
whatever Phase B3 became, then `Tools/`, then `Labs/` last, since 72 machine
write-ups are the most repetitive and the least ambiguous.

---

## Keeping the audit honest

- One cluster per sitting. Ending a sitting mid-cluster means re-reading it.
- Write the verdict in the checkbox line the moment you decide. A verdict you
  intend to write down later is a verdict you will re-derive.
- `review` is a real answer. Use it and keep moving; a stalled sitting costs
  more than a deferred file.
- Re-run `python3 scripts/inventory.py` after any batch of changes. The
  overlap scores move as files merge, and it will find pairs that only become
  visible once something else is gone.

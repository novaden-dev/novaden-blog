# OSCP Migration Spec

The executable plan for importing the OSCP vault
(`/home/kayra/LearningHub/OffSec/OSCP`) into this publication. The consultant
brief the human supplied is the authority on *principles*; this file records the
*concrete decisions* made against that brief so the copying agent can execute
without re-deciding. Where this file and the brief disagree, the brief wins and
this file is wrong: stop and flag it.

Scope: the 100 publishable notes in `Concepts/`, `Methodology/`, `Techniques/`,
and `Tools/`. **`Labs/` is excluded** (vendor-prohibited machine writeups) and
its 669 images do not migrate. `Attachments/`, `deploy/`, `site/`, `Exam/`,
`OSCP-Exam-Report.*` do not migrate.

## What the shell already provides

- **Tag registry** (`src/utils/tags.ts`): the offensive-security vocabulary
  below is already added. Do not invent tags outside it; if a note needs a
  subject that is not registered, **flag it** (see New tags) rather than
  slugifying a free-form tag.
- **Handbook** (`src/data/collections/oscp.md`): exists as `draft: true` with
  `entries: []`. The build validates every placement's target, so a placement
  may only be added once its target post exists. Fill `entries` as posts land;
  flip `draft: false` when the handbook is worth showing.

## Layout and slugs

- **Flat**, directly under `src/data/blog/`. No subfolders, **no `oscp-`
  prefix.** Knowledge is owned by the flat corpus; OSCP membership is the
  handbook, not the path or the filename. A future CPTS/PNPT handbook must be
  able to reference the same note without it reading as "an OSCP file".
- **Slug** = kebab-case of the title: lowercase, spaces to `-`, drop `()`,
  `.` to `-` where it separates words (`NTDS.dit` to `ntds-dit`), `_` to `-`.
  Filename = `<slug>.md`; also set `slug:` in frontmatter to the same value so
  the URL is `/posts/<slug>`.
- Slugs below are pre-computed. They were checked against existing
  `src/data/blog/` filenames; coexistence cases are flagged.

## Frontmatter defaults

Applied to every migrated note, then overridden per the table:

- `category: notes` for all 100. None are journal or cert-review. (An OSCP
  *cert-review* is a separate future post, not part of this batch.)
- `format`: **none** by default. `methodology` only on the four Methodology
  notes. `cheatsheet`/`guide` on a Tool note only where its shape truly matches
  (see Tools). A technique note is **not** a `guide` just because it lists
  commands.
- `draft: true` for all 100 on arrival. Imported material enters unpublished and
  is un-drafted per note during human review (this is when tags get their final
  check: the schema only validates tags on non-draft posts).
- `tags`: exactly as the table says. Subjects only, 1 to 3, narrowest useful.
- `author`, `pubDatetime`, `modDatetime`: derive dates from the vault's git
  history per the site Date Policy (`git log --diff-filter=A --follow` for
  `pubDatetime`, last-commit for `modDatetime`). `author` defaults to the site
  author.
- `description`: one concrete sentence. Reuse/condense the note's opening line;
  do not invent claims.

## Handbook sections

One handbook, sectioned by attack flow (not by source folder). Section strings
are canonical: use them verbatim in each placement's `section`. Placement `id`
is `oscp-NNN` from the table, assigned once, never reused, never renumbered.
Reading order is the table order. Default `role: step`; use `supplementary`
only for a note that is reference-alongside rather than part of the path
(most Tools are `supplementary`).

Section order:

1. `Concepts`
2. `Methodology`
3. `Techniques/Service Enumeration`
4. `Techniques/Web`
5. `Techniques/Shells and Access`
6. `Techniques/Privilege Escalation (Linux)`
7. `Techniques/Privilege Escalation (Windows)`
8. `Techniques/Credentials`
9. `Techniques/Active Directory`
10. `Techniques/Pivoting`
11. `Tools`

## Tag vocabulary (registered)

`active-directory` (ad) · `kerberos` · `windows` · `privilege-escalation`
(privesc) · `enumeration` (recon, reconnaissance, information-gathering) ·
`lateral-movement` · `persistence` · `credentials` (credential-access,
credential-hunting) · `password-attacks` (password-cracking, password-spraying,
brute-forcing) · `pivoting` (tunneling, port-forwarding) · `shells`
(reverse-shells) · `file-transfers` · `exploit-development` (public-exploits) ·
`encoding` (base64) · `databases` · `smb` · `ftp` · `smtp` · `snmp` · `dns` ·
`rpc` · `web` · `sql-injection` (sqli) · `command-injection` · `file-upload` ·
`file-inclusion` (lfi, rfi) · `template-injection` (ssti) · `mass-assignment` ·
`webdav`. Plus existing `linux`, `ssh`, `networking`.

Rules when tagging: map the note's real subject to the narrowest of these; drop
shape words, `security`/`oscp`/`offensive`/`tech`, and mechanical parents
(tag `sql-injection`, never `sql-injection + web`). A tool or protocol merely
*used* is not a tag; it is a tag only if the note is substantially about it.

## The notes

`category: notes` and `draft: true` on all rows; only `format` deviations are
shown. Source folder is given per subtable.

### 1. Concepts (source: `Concepts/`)

| id | source note | slug | tags | flag |
|----|-------------|------|------|------|
| oscp-001 | Active Directory Concepts.md | active-directory-concepts | active-directory | |
| oscp-002 | Base64 and Encodings.md | base64-and-encodings | encoding | |
| oscp-003 | Linux Permissions.md | linux-permissions | linux, privilege-escalation | |
| oscp-004 | Network Services Handbook.md | network-services-handbook | enumeration, networking | |

### 2. Methodology (source: `Methodology/`) — `format: methodology`

| id | source note | slug | tags | flag |
|----|-------------|------|------|------|
| oscp-005 | Information Gathering.md | information-gathering | enumeration | OVERLAP-A |
| oscp-006 | Privilege Escalation.md | privilege-escalation | privilege-escalation, linux | |
| oscp-007 | Privilege Escalation (Windows).md | privilege-escalation-windows | privilege-escalation, windows | |
| oscp-008 | Active Directory.md | active-directory | active-directory | |

### 3. Techniques: Service Enumeration (source: `Techniques/`)

| id | source note | slug | tags | flag |
|----|-------------|------|------|------|
| oscp-009 | SMB Enumeration.md | smb-enumeration | smb, enumeration | |
| oscp-010 | FTP Enumeration.md | ftp-enumeration | ftp, enumeration | |
| oscp-011 | SMTP Enumeration.md | smtp-enumeration | smtp, enumeration | |
| oscp-012 | SNMP Enumeration.md | snmp-enumeration | snmp, enumeration | |
| oscp-013 | DNS Enumeration.md | dns-enumeration | dns, enumeration | |
| oscp-014 | RPC Enumeration.md | rpc-enumeration | rpc, enumeration | |
| oscp-015 | Database Enumeration.md | database-enumeration | databases, enumeration | |

### 4. Techniques: Web (source: `Techniques/`)

| id | source note | slug | tags | flag |
|----|-------------|------|------|------|
| oscp-016 | SQL Injection.md | sql-injection | sql-injection | |
| oscp-017 | Command Injection.md | command-injection | command-injection | OVERLAP-B (os-command-injection.md) |
| oscp-018 | File Inclusion.md | file-inclusion | file-inclusion | OVERLAP-B (path-directory-traversal.md, light) |
| oscp-019 | File Upload.md | file-upload | file-upload | OVERLAP-B (file-upload-vulnerabilities.md) |
| oscp-020 | Server-Side Template Injection.md | server-side-template-injection | template-injection | |
| oscp-021 | Mass Assignment.md | mass-assignment | mass-assignment | |
| oscp-022 | Web Content Discovery.md | web-content-discovery | web, enumeration | |
| oscp-023 | Virtual Hosts.md | virtual-hosts | web, enumeration | |
| oscp-024 | WebDAV.md | webdav | webdav | |
| oscp-025 | Webshells.md | webshells | web, shells | |
| oscp-026 | ImageMagick.md | imagemagick | file-upload, exploit-development | TAG? (CVE-specific) |
| oscp-027 | ExifTool DjVu Injection.md | exiftool-djvu-injection | file-upload, exploit-development | TAG? (CVE-specific) |
| oscp-028 | Text4Shell.md | text4shell | web, exploit-development | TAG? (CVE-specific) |

### 5. Techniques: Shells and Access (source: `Techniques/`)

| id | source note | slug | tags | flag |
|----|-------------|------|------|------|
| oscp-029 | Reverse Shells.md | reverse-shells | shells | |
| oscp-030 | SSH Key Access.md | ssh-key-access | ssh | |
| oscp-031 | File Transfers.md | file-transfers | file-transfers | |
| oscp-032 | Fixing Public Exploits.md | fixing-public-exploits | exploit-development | |
| oscp-033 | LibreOffice Macros.md | libreoffice-macros | shells | OS? (initial-access via macro) |
| oscp-034 | Restricted Shells.md | restricted-shells | shells | |

### 6. Techniques: Privilege Escalation (Linux) (source: `Techniques/`)

| id | source note | slug | tags | flag |
|----|-------------|------|------|------|
| oscp-035 | Cron Jobs.md | cron-jobs | privilege-escalation, linux | |
| oscp-036 | SUID Binaries.md | suid-binaries | privilege-escalation, linux | |
| oscp-037 | Sudo.md | sudo | privilege-escalation, linux | |
| oscp-038 | Linux Capabilities.md | linux-capabilities | privilege-escalation, linux | |
| oscp-039 | Linux Groups.md | linux-groups | privilege-escalation, linux | |
| oscp-040 | NFS no_root_squash.md | nfs-no-root-squash | privilege-escalation, linux | |
| oscp-041 | Service Exploits.md | service-exploits | privilege-escalation, linux | OS? (confirm not Windows) |
| oscp-042 | Kernel Exploits.md | kernel-exploits | privilege-escalation, linux | OS? (confirm Linux-only) |
| oscp-043 | MySQL Privilege Escalation.md | mysql-privilege-escalation | privilege-escalation, databases | |

### 7. Techniques: Privilege Escalation (Windows) (source: `Techniques/`)

| id | source note | slug | tags | flag |
|----|-------------|------|------|------|
| oscp-044 | Windows Service Exploits.md | windows-service-exploits | privilege-escalation, windows | |
| oscp-045 | Windows Autoruns and Scheduled Tasks.md | windows-autoruns-and-scheduled-tasks | privilege-escalation, windows | |
| oscp-046 | Windows Token Privileges.md | windows-token-privileges | privilege-escalation, windows | |
| oscp-047 | Weak File Permissions.md | weak-file-permissions | privilege-escalation, linux | |
| oscp-048 | Windows Remote Access.md | windows-remote-access | windows | |

### 8. Techniques: Credentials (source: `Techniques/`)

| id | source note | slug | tags | flag |
|----|-------------|------|------|------|
| oscp-049 | Credential Hunting.md | credential-hunting | credentials, linux | |
| oscp-050 | Windows Credential Hunting.md | windows-credential-hunting | credentials, windows | |
| oscp-051 | Brute Forcing Logins.md | brute-forcing-logins | password-attacks | |
| oscp-052 | Password Spraying.md | password-spraying | password-attacks, active-directory | |
| oscp-053 | Password Cracking.md | password-cracking | password-attacks | |

### 9. Techniques: Active Directory (source: `Techniques/`)

| id | source note | slug | tags | flag |
|----|-------------|------|------|------|
| oscp-054 | Active Directory Enumeration.md | active-directory-enumeration | active-directory, enumeration | |
| oscp-055 | AS-REP Roasting.md | as-rep-roasting | kerberos | |
| oscp-056 | Kerberoasting.md | kerberoasting | kerberos | |
| oscp-057 | Kerberos Delegation.md | kerberos-delegation | kerberos | |
| oscp-058 | Silver and Golden Tickets.md | silver-and-golden-tickets | kerberos | |
| oscp-059 | ACL Abuse.md | acl-abuse | active-directory | |
| oscp-060 | AD Lateral Movement.md | ad-lateral-movement | active-directory, lateral-movement | |
| oscp-061 | DCSync.md | dcsync | active-directory, credentials | |
| oscp-062 | NTDS.dit Extraction.md | ntds-dit-extraction | active-directory, credentials | |
| oscp-063 | LAPS.md | laps | active-directory, windows | |
| oscp-064 | LLMNR Poisoning and NTLM Relay.md | llmnr-poisoning-and-ntlm-relay | active-directory, networking | TAG?/PUBLISH (exam-restricted note; ntlm-relay tag?) |
| oscp-065 | AD Persistence.md | ad-persistence | active-directory, persistence | |

### 10. Techniques: Pivoting (source: `Techniques/`)

| id | source note | slug | tags | flag |
|----|-------------|------|------|------|
| oscp-066 | Tunneling and Pivoting.md | tunneling-and-pivoting | pivoting | |

### 11. Tools (source: `Tools/`) — `role: supplementary`

Default `format`: **none**. Tools are tagged by the function they serve, not by
their own name (you search for `ffuf`, you browse by `web`). Set
`format: cheatsheet` only where the note is intentionally compressed reference;
`format: guide` only where it is a genuine step-by-step setup/usage procedure.

| id | source note | slug | format | tags | flag |
|----|-------------|------|--------|------|------|
| oscp-067 | accesschk.md | accesschk | | privilege-escalation, windows | |
| oscp-068 | AutoRecon.md | autorecon | | enumeration | |
| oscp-069 | BloodHound.md | bloodhound | | active-directory | |
| oscp-070 | Burp Suite.md | burp-suite | | web | |
| oscp-071 | Chisel.md | chisel | | pivoting | |
| oscp-072 | evil-winrm.md | evil-winrm | | windows | |
| oscp-073 | feroxbuster.md | feroxbuster | | web, enumeration | |
| oscp-074 | ffuf.md | ffuf | | web, enumeration | |
| oscp-075 | git-dumper.md | git-dumper | | web | |
| oscp-076 | hashcat.md | hashcat | | password-attacks | |
| oscp-077 | icacls.md | icacls | | privilege-escalation, windows | |
| oscp-078 | Impacket.md | impacket | | active-directory | |
| oscp-079 | john.md | john | | password-attacks | |
| oscp-080 | kerbrute.md | kerbrute | | kerberos | |
| oscp-081 | Ligolo-ng.md | ligolo-ng | | pivoting | |
| oscp-082 | LinEnum.md | linenum | | privilege-escalation, linux | |
| oscp-083 | LinPEAS.md | linpeas | | privilege-escalation, linux | |
| oscp-084 | linux-exploit-suggester.md | linux-exploit-suggester | | privilege-escalation, linux | |
| oscp-085 | linux-smart-enumeration.md | linux-smart-enumeration | | privilege-escalation, linux | |
| oscp-086 | Metasploit.md | metasploit | | exploit-development | TAG? (broad framework) |
| oscp-087 | Mimikatz.md | mimikatz | | credentials, windows | |
| oscp-088 | msfvenom.md | msfvenom | | shells | |
| oscp-089 | nc.md | nc | | shells | |
| oscp-090 | NetExec.md | netexec | | active-directory | |
| oscp-091 | powercat.md | powercat | | shells | |
| oscp-092 | PrivescCheck PowerUp SharpUp.md | privesccheck-powerup-sharpup | | privilege-escalation, windows | |
| oscp-093 | pspy.md | pspy | | privilege-escalation, linux | |
| oscp-094 | pyGPOAbuse.md | pygpoabuse | | active-directory | |
| oscp-095 | Rubeus.md | rubeus | | kerberos | |
| oscp-096 | SearchSploit.md | searchsploit | | exploit-development | |
| oscp-097 | SSH Tunnels.md | ssh-tunnels | | pivoting, ssh | |
| oscp-098 | tmux.md | tmux | | linux | TAG? (workflow tool, not an attack subject) |
| oscp-099 | winPEAS.md | winpeas | | privilege-escalation, windows | |
| oscp-100 | WPScan.md | wpscan | | web | |

## Internal links

The vault has ~2070 wikilinks; ~889 sit in these public notes, ~626 of them
between public notes (the rest point into `Labs/`).

1. **Public-to-public** `[[Note Title]]` to `[/posts/<slug>](/posts/<slug>)`
   using the slug map above. Preserve the link only where one note genuinely
   references another concept/technique/tool; drop links that existed only as
   folder/index navigation.
2. **`[[Note#Heading]]`** (~47): resolve to `/posts/<slug>#<slugified-heading>`.
   Verify the heading exists in the target after conversion.
3. **`[[Note|alias]]`** (~1): `[alias](/posts/<slug>)`.
4. **Any link into `Labs/`** (~263): the target is not migrating. Do **not**
   emit a dead link. Replace with plain prose ("seen on a Proving Grounds box")
   or delete the clause where the box name adds nothing. When a Labs link is the
   only evidence for a claim, **flag** it rather than silently cutting.
5. The old `index.md` was navigation; its substance is folded into
   `oscp.md`'s intro. Do not migrate it as a post. Preserve any *substantive*
   line not already in the intro; flag anything whose destination is unclear.

## Overlaps with existing posts

- **OVERLAP-A (methodology):** `information-gathering` (OSCP, mature) vs the thin
  drafts `penetration-testing-process.md`, `network-pentest-methodology.md`,
  `web-application-pentest-methodology.md`, `web-application-security-testing.md`.
  Prefer the OSCP material; absorb unique content from the drafts, repair inbound
  links, retire the weak duplicates. These are **not 1:1** (OSCP info gathering
  is host/network recon; the web drafts are web-scoped), so **flag for human
  review** before deleting anything.
- **OVERLAP-B (same subject, different job):** offensive OSCP note vs existing
  defensive explainer: `command-injection` / `os-command-injection`;
  `file-upload` / `file-upload-vulnerabilities`; `file-inclusion` /
  `path-directory-traversal` (light). Default: **keep both**, shared subject tag,
  distinct titles/descriptions that make the offensive-vs-defensive purpose
  obvious. Apply the test: would you deliberately reach for one over the other
  mid-task? If yes, keep both; if they serve the same retrieval job, merge and
  flag.

## Flag legend (do not guess silently)

- **OVERLAP-A / OVERLAP-B**: handle per the section above; human decides merges.
- **TAG?**: the proposed tag is uncertain (CVE-specific note, broad tool, or
  possible new subject like `ntlm-relay`). Use the proposed tag but list it for
  human review; propose a new registry tag only against the New-tags threshold.
- **OS?**: confirm the note's OS from its body before setting `linux` vs
  `windows`; the opening line was ambiguous.
- **PUBLISH**: `llmnr-poisoning-and-ntlm-relay` already carries an in-note
  caveat that it is not exam-applicable; confirm nothing in it is
  vendor-restricted before un-drafting.

## New tags

Only propose one when no registered tag fits, it is a substantial and durable
subject of the note, browsing it later would be useful, and it is not a
category/format/cert/collection/hierarchy in disguise. Frequency is irrelevant.
Candidates surfaced above (`ntlm-relay`, per-CVE tags): default to the broader
registered tag and flag; do not add without human sign-off.

## Execution order

1. Copy + convert one section at a time, Concepts first, then Methodology, so
   the earliest wikilink targets exist before later notes reference them.
2. For each note: write frontmatter (defaults + table), convert links, add its
   `oscp-NNN` placement to `oscp.md` under the right `section` (`role:
   supplementary` for Tools).
3. Leave every note `draft: true`. Do not flip the handbook to `draft: false`
   until its members are reviewed.
4. Collect all flags into a review list for the human; do not resolve
   OVERLAP/PUBLISH cases autonomously.

---

## Migration log (batch complete)

The remaining 88 notes migrated; the corpus now holds all 100. This section records the concrete decisions made during execution, for the review pass.

- **State:** every migrated note is `draft: true`. Un-drafting per note during human review is what publishes it; nothing flips without that review.
- **Placement ids:** the 12 notes migrated by hand keep their `oscp-s01`–`s12` ids at their table positions. All new notes use the table's `oscp-NNN` ids. Entries were rebuilt in table order (001 → 100); the existing 12 were regrouped from the coarse sections (`Concepts`, `Techniques`) into the canonical section list above.
- **Unpublished members:** the handbook collection itself is already published, so every new placement carries `required: false`: a drafted member is dropped whole from the tree instead of failing the build, and appears as soon as it is un-drafted.
- **Wikilinks:** public-to-public links converted to `/collections/oscp/<slug>`, heading anchors included; every emitted anchor was verified against the target note's headings in github-slugger form, and two underscore-heading anchors were fixed (`cron-jobs.md`: `ld_library_path`, `why-not-ld_preload-here`). No `BROKEN-WIKILINK` case occurred: every `[[...]]` resolved to a public note or a Labs note.
- **Labs links:** dropped to plain prose with the box name kept (`Walla`, `InfoSecPrep`, `Loly`, `GOAD-Light`, …) per spec rule 4. The "only evidence for a claim" judgment is not automatable: during review, scan notes where a box name follows a claim ("is the example here") to confirm the prose still stands without the link.
- **No embeds, no callouts:** zero `![[...]]` image embeds and zero Obsidian callouts in the 100 public notes. (A handful of raw-HTML hits were Apache/MSL syntax inside code fences; left as-is.)
- **OS? resolutions (from body, against the table):** `service-exploits` → Linux confirmed; `kernel-exploits` → Linux confirmed; `weak-file-permissions` → **resolved against the table**: the note is `/etc/shadow`, `/etc/passwd`, john and mkpasswd throughout, zero Windows content, so tags are `[privilege-escalation, linux]`; `libreoffice-macros` → no OS tag added (macro abuse is cross-platform).
- **TAG? (tags applied per table, listed for review):** `imagemagick`, `exiftool-djvu-injection`, `text4shell` (CVE-specific notes on `file-upload`/`web` + `exploit-development`), `llmnr-poisoning-and-ntlm-relay` (TAG? still open: `ntlm-relay`), `metasploit` (broad framework), `tmux` (workflow tool). Resolved since: `weak-file-permissions` — table row 047 corrected to `privilege-escalation, linux` per the body; `llmnr-poisoning-and-ntlm-relay` — **PUBLISH closed by human review** (no PG Practice/Challenge-Lab or exam content; un-drafted, placement `required` restored to default).
- **Overlaps:** no merge was performed. `information-gathering` migrated as its own note (OVERLAP-A human decision pending against the thin pentest drafts); OVERLAP-B pairs (`command-injection`/`os-command-injection`, `file-inclusion`/`path-directory-traversal`, `file-upload`/`file-upload-vulnerabilities`) kept both sides per the default, distinct titles make the offensive/defensive split.
- **Dates:** `pubDatetime` = vault first-commit date (`--diff-filter=A --follow`), `modDatetime` = vault last-commit date, per the site Date Policy.
- **Descriptions:** condensed from each note's opening line. Four descriptions carry an inline link because the opening sentence itself links a note (`password-spraying`, `hashcat`, `linux-smart-enumeration`, `netexec` via `netexec`-adjacent notes), matching the established sample style.
- **Section labels:** the `Techniques: X` colon form nested nothing (the handbook tree splits on `/`), so the 58 placement labels became `Techniques/X`, rendering the eight attack-area groups under one Techniques folder. The canonical section list above was updated to match.
- **Publication and link fixes (second review pass):** all 100 notes un-drafted (87 remaining after the LLMNR review), all placements `required` default. A corpus-wide link audit (628 handbook links) caught a family of 8 conversion bugs across 5 files: two wrong slugs in `linux-permissions` (`privilege-escalation` → `privilege-escalation-linux`), three same-note `[[#Heading]]` links the converter could not parse (reverse-shells ×2, information-gathering ×1) that had mangled into bogus collection-prefixed hrefs, one same-note link in `sql-injection`, and one PG-box link (`Kevin`) restored to plain prose per the Labs rule. Terminal-escape and diagram `[[ ]]` hits are content, not links.

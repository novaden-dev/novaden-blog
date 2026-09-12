#!/usr/bin/env python3
"""
Mechanical conformance fixes for src/data/blog, against CONTENT_FORMATTING.md.

Only changes that are unambiguous. Anything where the right replacement
depends on the sentence is counted and reported, never rewritten: a script
that guesses at prose produces edits nobody can review.

What it changes:
  1. Bullet sub-labels     `- **Label** — text`  ->  `- **Label**: text`
  2. Headings              `## A — B`            ->  `## A: B`
  3. Unlabelled fences     ```                   ->  ```text
  4. A body h1 that just repeats the frontmatter title (the layout already
     renders the title, so the duplicate is noise)
  5. Retired meta tags in the tag list (`notes`, `certification`)

What it refuses to change:
  - Em dashes mid-sentence. Comma, colon, parentheses and full stop are all
    valid replacements and only the author knows which.
  - Frontmatter titles and descriptions. The series numbering in
    FileList.astro parses `v1.2 — Title`, so rewriting those breaks it.
  - Heading levels. threat-modeling.md genuinely nests three deep; demoting
    it would produce the h4s the same rule forbids. That needs a structural
    decision, not a substitution.

Usage:
    python3 scripts/fix-mechanical.py            # dry run, shows every change
    python3 scripts/fix-mechanical.py --apply    # write the files
"""

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

BLOG = Path(__file__).resolve().parent.parent / "src/data/blog"
RETIRED_TAGS = {"notes", "certification", "others"}


def split_fm(raw):
    m = re.match(r"^(---\n.*?\n---\n)(.*)$", raw, re.S)
    return (m.group(1), m.group(2)) if m else ("", raw)


def fix_file(path):
    raw = path.read_text()
    fm, body = split_fm(raw)
    if not fm:
        return None

    title = (re.search(r"^title:\s*(.*)$", fm, re.M) or [None, ""])[1]
    title = title.strip().strip('"').strip("'")

    changes = Counter()
    skipped = Counter()
    out, in_fence = [], False

    for line in body.split("\n"):
        if line.startswith("```"):
            if not in_fence and not line[3:].strip():
                line = "```text"
                changes["unlabelled fence labelled text"] += 1
            in_fence = not in_fence
            out.append(line)
            continue

        if in_fence:
            out.append(line)
            continue

        # 4. A body h1 repeating the title the layout already prints.
        if line.startswith("# ") and line[2:].strip().lower() == title.lower():
            changes["duplicate h1 removed"] += 1
            continue

        # 2. Headings: a colon carries the same break without the dash.
        if re.match(r"^#{1,4} ", line) and "—" in line:
            n = line.count("—")
            line = re.sub(r"\s*—\s*", ": ", line)
            changes["heading em dash to colon"] += n

        # 1. Bullet sub-labels, the case CONTENT_FORMATTING.md spells out.
        new = re.sub(r"(^\s*[-*]\s+\*\*[^*]+\*\*)\s*—\s*", r"\1: ", line)
        if new != line:
            changes["bullet label em dash to colon"] += 1
            line = new

        # Everything else stays, and gets counted for the report.
        if "—" in line:
            skipped["em dash in prose, needs a human"] += line.count("—")

        out.append(line)

    body = "\n".join(out)

    # 5. Tags that the taxonomy retired into `category`.
    def strip_retired(m):
        kept = [t for t in re.findall(r'"([^"]+)"', m.group(1))
                if t not in RETIRED_TAGS]
        return "tags: [" + ", ".join(f'"{t}"' for t in kept) + "]"

    new_fm, n = re.subn(r'tags:\s*\[([^\]]*)\]', strip_retired, fm)
    if new_fm != fm:
        changes["retired tag removed"] += 1
        fm = new_fm

    # Also handle the YAML list form.
    lines, dropped = [], 0
    in_tags = False
    for line in fm.split("\n"):
        if re.match(r"^tags:\s*$", line):
            in_tags = True
            lines.append(line)
            continue
        if in_tags:
            m = re.match(r"^\s+-\s+(.+)$", line)
            if m:
                if m.group(1).strip().strip('"') in RETIRED_TAGS:
                    dropped += 1
                    continue
                lines.append(line)
                continue
            in_tags = False
        lines.append(line)
    if dropped:
        changes["retired tag removed"] += dropped
        fm = "\n".join(lines)

    result = fm + body
    return result if result != raw else None, changes, skipped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write the changes")
    args = ap.parse_args()

    total, total_skipped = Counter(), Counter()
    touched = []

    for path in sorted(BLOG.glob("*.md")):
        got = fix_file(path)
        if got is None:
            continue
        new, changes, skipped = got
        total.update(changes)
        total_skipped.update(skipped)
        if new is not None and changes:
            touched.append((path.name, changes))
            if args.apply:
                path.write_text(new)

    print(f"{'APPLIED' if args.apply else 'DRY RUN'}: "
          f"{len(touched)} files\n")
    for name, changes in touched:
        print(f"  {name}")
        for k, v in changes.most_common():
            print(f"      {v:>4}  {k}")
    print("\nchanged:")
    for k, v in total.most_common():
        print(f"  {v:>4}  {k}")
    print("\nleft alone, needs your judgment:")
    for k, v in total_skipped.most_common():
        print(f"  {v:>4}  {k}")
    if not args.apply:
        print("\nnothing written. re-run with --apply")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Content inventory across every source, one record per file.

This is the audit that has to happen before anything is imported: it reads
every markdown file in every configured source, computes the signals that
decide what to do with it, finds near-duplicates by comparing all files
against each other rather than by anyone noticing them, and proposes an
outcome per file.

Nothing here edits content. It reads, measures, and writes two artifacts:

  content-audit/inventory.json   machine readable, one record per file.
                                 This is also the seed of the migration
                                 manifest: source path, original URL, hash.
  content-audit/INVENTORY.md     the same thing grouped by proposed outcome,
                                 for reading top to bottom.

Usage:
    python3 scripts/inventory.py                 # blog + gitbook
    python3 scripts/inventory.py --with-oscp     # add the OSCP vault
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "content-audit"

# ---------------------------------------------------------------- sources

SOURCES = {
    "blog": dict(
        root=REPO / "src/data/blog",
        glob="*.md",
        live=True,  # already published from this repo
        url="/posts/{slug}",
    ),
    "gitbook": dict(
        root=Path("/home/kayra/SoulSiphon/PersonalWork/NotesHubGitBook"),
        glob="**/*.md",
        live=False,
        url="https://kayra.gitbook.io/hackerkayra/{relpath}",
    ),
    "oscp": dict(
        root=Path("/home/kayra/LearningHub/OffSec/OSCP"),
        glob="**/*.md",
        live=False,
        url="https://oscp.novaden.dev/{relpath}",
    ),
}

# Directories that are not content: build output, dependencies, vendored
# copies. Excluded before anything is measured.
SKIP_DIRS = {
    ".git", "node_modules", "dist", ".astro", "public", "site",
    ".quartz-build", ".obsidian", ".github", ".claude",
}

# Files that are platform furniture rather than writing.
META_NAMES = {
    "SUMMARY.md", "README.md", "Introduction.md", "index.md", "AGENTS.md",
    "making-a-post.md", "understanding-projects.md", "our-features.md",
    "what-we-do.md",
}

# ------------------------------------------------------------- extraction

FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.S)
FENCE = re.compile(r"^```")


def split_frontmatter(raw):
    m = FRONTMATTER.match(raw)
    return (m.group(1), m.group(2)) if m else ("", raw)


def fm_get(fm, key):
    m = re.search(rf"^{key}:\s*(.*)$", fm, re.M)
    if not m:
        return None
    return m.group(1).strip().strip('"').strip("'") or None


def fm_list(fm, key):
    m = re.search(rf"^{key}:\s*(\[.*?\]|\n(?:\s+-\s+.*\n?)+)", fm, re.M)
    if not m:
        return []
    blob = m.group(1)
    found = re.findall(r'"([^"]+)"|\'([^\']+)\'|^\s+-\s+(.+)$', blob, re.M)
    return [(a or b or c).strip() for a, b, c in found if (a or b or c).strip()]


def strip_for_prose(body):
    """Body text with code, images, and markdown syntax removed.

    Similarity is computed on prose only. Security notes share a lot of
    literal command text, and letting that count would make every pair of
    tool notes look like duplicates of each other.
    """
    out, in_fence = [], False
    for line in body.split("\n"):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        out.append(line)
    text = "\n".join(out)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)      # images
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)   # link text only
    text = re.sub(r"`[^`]*`", " ", text)                   # inline code
    text = re.sub(r"[#>*_|\-]+", " ", text)                # markdown syntax
    text = re.sub(r"\s+", " ", text)
    return text.lower().strip()


def shingles(text, n=5):
    words = text.split()
    if len(words) < n:
        return set()
    return {
        hash(" ".join(words[i:i + n])) for i in range(len(words) - n + 1)
    }


def code_blocks(body):
    blocks, cur, in_fence = [], [], False
    for line in body.split("\n"):
        if FENCE.match(line):
            if in_fence:
                blocks.append("\n".join(cur).strip())
                cur = []
            in_fence = not in_fence
            continue
        if in_fence:
            cur.append(line)
    return [b for b in blocks if b]


def quality(body):
    """Deviations from CONTENT_FORMATTING.md, counted not judged."""
    prose_lines, in_fence = [], False
    bad_fences = 0
    for line in body.split("\n"):
        if FENCE.match(line):
            if not in_fence and not line[3:].strip():
                bad_fences += 1
            in_fence = not in_fence
            continue
        if not in_fence:
            prose_lines.append(line)
    prose = "\n".join(prose_lines)
    return dict(
        emdash=prose.count("—"),
        h1=len(re.findall(r"^# ", prose, re.M)),
        h4=len(re.findall(r"^#### ", prose, re.M)),
        unlabelled_fences=bad_fences,
        wikilinks=len(re.findall(r"\[\[[^\]]+\]\]", body)),
        gitbook_hints=len(re.findall(r"\{%\s*hint", body)),
        html_figures=len(re.findall(r"<figure", body)),
    )


# Things that must never be published without a human looking first.
# A credential written down is a publication blocker. An IP address is not:
# on a pentest blog, addresses are the subject matter. They are counted and
# reported, but they never by themselves send a file to review.
SECRET_PATTERNS = [
    (r"(?i)\b(password|passwd|pwd)\s*[:=]\s*\S{3,}", "password assignment", "high"),
    (r"(?i)\bapi[_-]?key\s*[:=]\s*\S{8,}", "api key", "high"),
    (r"(?i)\b(secret|token)\s*[:=]\s*\S{8,}", "secret or token", "high"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "private key", "high"),
    (r"(?i)\bAKIA[0-9A-Z]{16}\b", "aws access key", "high"),
    (r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "ip address", "low"),
]


def sensitive(body):
    high, low = Counter(), Counter()
    for pattern, label, level in SECRET_PATTERNS:
        n = len(re.findall(pattern, body))
        if n:
            (high if level == "high" else low)[label] = n
    return dict(high), dict(low)


# ------------------------------------------------------------- git dates

def git_dates(root):
    """First-add and last-touch date per path, from one pass over history.

    Filesystem mtimes are worthless here (the GitBook export shares one
    mtime across every file), so real dates come from commits. Renames are
    followed so a file keeps the date it was actually written.
    """
    if not (root / ".git").exists():
        return {}
    try:
        log = subprocess.run(
            ["git", "-C", str(root), "log", "--reverse", "--date-order",
             "--format=%x00%aI", "--name-status", "--find-renames"],
            capture_output=True, text=True, timeout=180,
        ).stdout
    except Exception:
        return {}

    first, last, renamed_from = {}, {}, {}
    date = None
    for line in log.split("\n"):
        if line.startswith("\x00"):
            date = line[1:].strip()
            continue
        if not line.strip() or date is None:
            continue
        parts = line.split("\t")
        status = parts[0]
        if status.startswith("R") and len(parts) >= 3:
            old, new = parts[1], parts[2]
            renamed_from[new] = old
            first[new] = first.get(old, date)
            last[new] = date
        elif len(parts) >= 2:
            path = parts[1]
            first.setdefault(path, date)
            last[path] = date
    return {"first": first, "last": last, "renamed": renamed_from}


# ------------------------------------------------------------- collection

def collection_members():
    """Post ids that some collection includes, and where."""
    members = defaultdict(list)
    cdir = REPO / "src/data/collections"
    if not cdir.exists():
        return members
    for f in cdir.glob("*.md"):
        for post in re.findall(r"^\s*post:\s*(\S+)", f.read_text(), re.M):
            members[post].append(f.stem)
    return members


# ------------------------------------------------------------------ scan

def scan(name, cfg):
    root = cfg["root"]
    if not root.exists():
        print(f"  ! source '{name}' not found at {root}, skipped", file=sys.stderr)
        return []

    dates = git_dates(root)
    records = []

    for path in sorted(root.glob(cfg["glob"])):
        rel = path.relative_to(root)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        raw = path.read_text(errors="replace")
        fm, body = split_frontmatter(raw)
        prose = strip_for_prose(body)
        blocks = code_blocks(body)

        relpath = str(rel)
        gd_first = dates.get("first", {}).get(relpath)
        gd_last = dates.get("last", {}).get(relpath)

        slug = fm_get(fm, "slug") or path.stem
        rec = dict(
            source=name,
            path=str(path),
            relpath=relpath,
            slug=slug,
            title=fm_get(fm, "title") or first_heading(body) or path.stem,
            words=len(prose.split()),
            code_blocks=len(blocks),
            headings=len(re.findall(r"^#{2,3} ", body, re.M)),
            category=fm_get(fm, "category"),
            tags=fm_list(fm, "tags"),
            draft=fm_get(fm, "draft") == "true",
            featured=fm_get(fm, "featured") == "true",
            has_frontmatter=bool(fm),
            description=fm_get(fm, "description"),
            pub=(fm_get(fm, "pubDatetime") or "")[:10] or None,
            mod=(fm_get(fm, "modDatetime") or "")[:10] or None,
            git_first=(gd_first or "")[:10] or None,
            git_last=(gd_last or "")[:10] or None,
            archived_area="archive-backup-bin" in relpath,
            is_meta=path.name in META_NAMES,
            quality=quality(body),
            sensitive=sensitive(body)[0],
            addresses=sensitive(body)[1],
            hash=hashlib.sha256(raw.encode()).hexdigest()[:16],
            url=cfg["url"].format(slug=slug, relpath=relpath[:-3]),
            links_out=sorted(set(
                re.findall(r"(?<!!)\[[^\]]*\]\((/posts/[^)#\s]+)", body)
            )),
            _shingles=shingles(prose),
            _prose=prose,
        )
        records.append(rec)
    return records


def first_heading(body):
    m = re.search(r"^#{1,2} (.+)$", body, re.M)
    return m.group(1).strip() if m else None


# ------------------------------------------------------- overlap analysis

def jaccard(a, b):
    if not a or not b:
        return 0.0
    inter = len(a & b)
    if not inter:
        return 0.0
    return inter / len(a | b)


def find_overlaps(records, threshold=0.12):
    """Compare every file against every other file.

    Deliberately not a shortlist: 145 files is 10k comparisons, which is
    cheap, and the point is that overlap gets found rather than noticed.
    """
    scored = defaultdict(list)
    n = len(records)
    for i in range(n):
        a = records[i]
        if a["words"] < 150:
            continue
        for j in range(i + 1, n):
            b = records[j]
            if b["words"] < 150:
                continue
            score = jaccard(a["_shingles"], b["_shingles"])
            if score >= threshold:
                scored[i].append((score, j))
                scored[j].append((score, i))
    for i, hits in scored.items():
        records[i]["near_duplicates"] = [
            dict(other=records[j]["relpath"],
                 source=records[j]["source"],
                 score=round(s, 3))
            for s, j in sorted(hits, reverse=True)[:5]
        ]
    for r in records:
        r.setdefault("near_duplicates", [])
    return records


STOPWORDS = set("""a an and are as at be been but by can could do does for from
has have how i if in into is it its like may more most no not of on or other
own same so some such than that the their them then there these they this to
was we were what when where which while who will with would you your it's
one two also just only very much many any each per via while about after
before over under between both all use used using need needs make makes get
gets take takes see look run runs first next last new old good bad way ways
thing things time times want wants know knows""".split())


def tfidf_vectors(records, top_terms=180):
    """Sparse tf-idf vector per document, keeping only its strongest terms.

    Shingle overlap finds text that was copied. This finds documents about
    the same subject even when none of the sentences match, which is the
    case that matters for two checklists written independently a month
    apart. The two signals answer different questions and neither replaces
    the other.
    """
    import math
    docs = []
    for r in records:
        toks = [w for w in re.findall(r"[a-z][a-z0-9-]{2,}", r["_prose"])
                if w not in STOPWORDS]
        docs.append(Counter(toks))

    df = Counter()
    for d in docs:
        df.update(d.keys())
    n = len(docs)

    vectors = []
    for d in docs:
        if not d:
            vectors.append({})
            continue
        weights = {
            t: (1 + math.log(c)) * math.log(n / (1 + df[t]))
            for t, c in d.items() if df[t] > 1
        }
        top = dict(sorted(weights.items(), key=lambda kv: -kv[1])[:top_terms])
        norm = math.sqrt(sum(v * v for v in top.values())) or 1.0
        vectors.append({t: v / norm for t, v in top.items()})
    return vectors


def find_subject_overlap(records, threshold=0.30, min_words=600):
    """Cosine similarity between every pair, via an inverted index."""
    vectors = tfidf_vectors(records)
    index = defaultdict(list)
    for i, vec in enumerate(vectors):
        if records[i]["words"] < min_words:
            continue
        for term, w in vec.items():
            index[term].append((i, w))

    sims = defaultdict(lambda: defaultdict(float))
    for term, postings in index.items():
        if len(postings) > 60:      # a term in a third of the corpus says nothing
            continue
        for x in range(len(postings)):
            i, wi = postings[x]
            for y in range(x + 1, len(postings)):
                j, wj = postings[y]
                sims[i][j] += wi * wj
                sims[j][i] += wi * wj

    for i, hits in sims.items():
        strong = sorted(((s, j) for j, s in hits.items() if s >= threshold),
                        reverse=True)[:5]
        records[i]["same_subject"] = [
            dict(other=records[j]["relpath"], source=records[j]["source"],
                 score=round(s, 3)) for s, j in strong
        ]
    for r in records:
        r.setdefault("same_subject", [])
    return records


def find_name_collisions(records):
    by_slug = defaultdict(list)
    for r in records:
        by_slug[r["slug"].lower()].append(r)
    for slug, group in by_slug.items():
        if len({r["source"] for r in group}) > 1:
            for r in group:
                r["slug_collision"] = [
                    o["source"] + ":" + o["relpath"] for o in group if o is not r
                ]
    for r in records:
        r.setdefault("slug_collision", [])
    return records


# ------------------------------------------------------ proposed outcomes

def propose(r, inbound, members):
    """One outcome per file, with the reason that produced it.

    Conservative by design: anything needing a judgment call becomes
    'review' rather than a silent decision.
    """
    why = []
    q = r["quality"]

    # A GitBook section README is usually nav, but one of them holds 1,400
    # words. Size decides, not the filename.
    if r["is_meta"] and r["words"] < 150:
        return "exclude", ["platform furniture, not writing"]

    if r["archived_area"]:
        return "archive", ["lives under archive-backup-bin in the source"]

    if r["words"] == 0:
        why.append("no body at all")
        if r["featured"]:
            why.append("but marked featured, so it is pinned publicly")
        return "empty", why

    if r["words"] < 250 and r["code_blocks"] == 0:
        return "stub", [f"{r['words']} words, no code, likely unfinished"]

    if r["slug_collision"]:
        return "duplicate-name", [
            "same slug in another source: " + ", ".join(r["slug_collision"])
        ]

    strong = [d for d in r["near_duplicates"] if d["score"] >= 0.30]
    if strong:
        return "duplicated-text", [
            f"{d['score']:.0%} of the prose is shared with {d['source']}:{d['other']}"
            for d in strong
        ]

    subject = [d for d in r["same_subject"] if d["score"] >= 0.45]
    if subject:
        return "same-subject-review", [
            f"covers the same ground as {d['source']}:{d['other']} "
            f"({d['score']:.0%} subject similarity) with different wording"
            for d in subject
        ]

    if r["sensitive"]:
        why.append("possible sensitive content: " +
                   ", ".join(f"{k} x{v}" for k, v in r["sensitive"].items()))
        return "review-sensitive", why

    if r["addresses"]:
        why.append("contains " +
                   ", ".join(f"{v} {k}es" for k, v in r["addresses"].items())
                   + ", check none are a live host")

    weak = [d for d in r["near_duplicates"] if d["score"] >= 0.15]
    if weak:
        why.append("partial overlap with " +
                   ", ".join(f"{d['source']}:{d['other']} ({d['score']:.0%})"
                             for d in weak))

    if r["source"] == "blog":
        if not inbound.get(r["slug"]) and r["slug"] not in members:
            why.append("orphan: nothing links to it and no collection includes it")
        if not r["description"]:
            why.append("no description")
    for label, key in [("em dashes", "emdash"), ("h1 headings", "h1"),
                       ("unlabelled code fences", "unlabelled_fences"),
                       ("GitBook hint shortcodes", "gitbook_hints"),
                       ("HTML figure blocks", "html_figures"),
                       ("wikilinks to rewrite", "wikilinks")]:
        if q.get(key):
            why.append(f"{q[key]} {label}")

    return ("improve" if why else "keep"), why


# ---------------------------------------------------------------- reports

def write_reports(records, args):
    OUT.mkdir(exist_ok=True)

    for r in records:
        r.pop("_shingles", None)
        r.pop("_prose", None)

    (OUT / "inventory.json").write_text(json.dumps(records, indent=2) + "\n")

    by_outcome = defaultdict(list)
    for r in records:
        by_outcome[r["outcome"]].append(r)

    order = ["empty", "review-sensitive", "duplicated-text", "duplicate-name",
             "same-subject-review", "stub", "improve", "keep", "archive",
             "exclude"]
    blurb = {
        "empty": "Frontmatter but no body. Decide: write, unpublish, or delete.",
        "review-sensitive": "Contains something that looks like a credential, key, or real address. Read before it is published anywhere.",
        "duplicate-name": "The same slug exists in more than one source. One of them wins, or they are genuinely different and one gets renamed.",
        "duplicated-text": "30%+ of the prose is literally shared with another file. Someone pasted. Decide which copy is the real one.",
        "same-subject-review": "Different words, same ground. Same reader need (merge), or different purposes worth keeping apart (label the difference)?",
        "stub": "Short and code-free. Probably unfinished rather than deliberately brief.",
        "improve": "Keep the content, fix what is listed.",
        "keep": "No action found.",
        "archive": "Lives in an archive area of the source. Not imported unless you say so.",
        "exclude": "Platform furniture (nav files, templates, README). Never content.",
    }

    lines = [
        "# Content Inventory",
        "",
        f"Generated by `scripts/inventory.py`. {len(records)} files across "
        f"{len(set(r['source'] for r in records))} sources. Nothing was modified.",
        "",
        "Every file in every configured source appears exactly once, in one",
        "outcome group. Overlap was found by comparing all files against each",
        "other, not by inspection.",
        "",
        "## Totals",
        "",
        "| Outcome | Files | What it means |",
        "|---|---:|---|",
    ]
    for key in order:
        if by_outcome[key]:
            lines.append(f"| `{key}` | {len(by_outcome[key])} | {blurb[key]} |")
    lines += ["", "## By source", "", "| Source | Files | Words |", "|---|---:|---:|"]
    for src in sorted(set(r["source"] for r in records)):
        rs = [r for r in records if r["source"] == src]
        lines.append(f"| {src} | {len(rs)} | {sum(r['words'] for r in rs):,} |")

    for key in order:
        group = by_outcome[key]
        if not group:
            continue
        lines += ["", f"## {key} ({len(group)})", "", blurb[key], ""]
        if key in ("keep", "archive", "exclude"):
            lines.append("<details><summary>show files</summary>")
            lines.append("")
            for r in sorted(group, key=lambda r: (r["source"], r["relpath"])):
                lines.append(f"- `{r['source']}` {r['relpath']} ({r['words']:,}w)")
            lines += ["", "</details>"]
            continue
        for r in sorted(group, key=lambda r: (-r["words"], r["relpath"])):
            dates = r["pub"] or r["git_first"] or "date unknown"
            lines.append(f"### `{r['source']}` {r['relpath']}")
            lines.append("")
            lines.append(f"**{r['title']}** · {r['words']:,} words · {dates}"
                         + (" · **draft**" if r["draft"] else "")
                         + (" · **featured**" if r["featured"] else ""))
            lines.append("")
            for w in r["why"]:
                lines.append(f"- {w}")
            lines.append("")

    (OUT / "INVENTORY.md").write_text("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--with-oscp", action="store_true",
                    help="include the OSCP vault (still work in progress)")
    args = ap.parse_args()

    wanted = ["blog", "gitbook"] + (["oscp"] if args.with_oscp else [])

    records = []
    for name in wanted:
        print(f"scanning {name} ...", file=sys.stderr)
        records += scan(name, SOURCES[name])

    print(f"comparing {len(records)} files against each other ...", file=sys.stderr)
    records = find_overlaps(records)
    records = find_subject_overlap(records)
    records = find_name_collisions(records)

    inbound = Counter()
    for r in records:
        for link in r["links_out"]:
            inbound[link.rstrip("/").split("/")[-1]] += 1
    members = collection_members()
    for r in records:
        r["inbound_links"] = inbound.get(r["slug"], 0)
        r["collections"] = members.get(r["slug"], [])
        r["outcome"], r["why"] = propose(r, inbound, members)

    write_reports(records, args)

    counts = Counter(r["outcome"] for r in records)
    print("\n" + "=" * 52, file=sys.stderr)
    for outcome, n in counts.most_common():
        print(f"  {outcome:<18} {n:>4}", file=sys.stderr)
    print("=" * 52, file=sys.stderr)
    print(f"  wrote {OUT}/INVENTORY.md and inventory.json", file=sys.stderr)


if __name__ == "__main__":
    main()

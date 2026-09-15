# AGENTS.md

Rules for working in this repo. The blog's own writing rules live in `CONTENT_FORMATTING.md` and `CONTENT_SYSTEM.md`; read both before editing any post.

## Humanizing pass checklist (src/data/blog/*.md)

When asked to make a post "more human" or to de-robot prose, read the ENTIRE file front to back, every sentence, including the frontmatter `description`, headings, table cells, and code block comments. Do not stop at the sentence the user quotes: treat every user correction as an example of a whole class of problem, and sweep the file for that entire class.

### 1. No announced frames

Never announce that information is coming or that something matters. State the fact directly.

- Wrong: `This matters for two reasons. ...`
- Wrong: `... and the difference matters:`
- Wrong: `The catch, and it is the whole reason this step is fiddly: ...`
- Wrong: `X is the usual trap. ...`
- Wrong: `The mistake is invisible until ...`
- Wrong: `That last row is the one worth internalising.`
- Right: just delete the frame and let the facts stand, or connect plainly (`Pinning bypass does not help if the routing is wrong.`)

### 2. No dramatic fragments or parallel flourishes

- Wrong: `This is the rig.`
- Wrong: `You cannot satisfy a pin. You defeat it, by one of three routes.`
- Wrong: `Each one fails in its own way.`
- Wrong: `X is the channel between A and B, and ...` (intro sentence that sets a scene before saying anything)

### 3. No "the one ..." constructions

- Wrong: `is the one to build habits around`
- Wrong: `is the one worth memorizing`
- Wrong: `is the one to remember`
- Right: `Use -s by default.` / state what it does and when to reach for it.

### 4. No rank claims or vague statistics

- Wrong: `the single most useful tool`, `The most useful single command in the list`
- Wrong: `Cleanest option`, `This clears the large majority of apps`
- Wrong: vague qualifiers that stand in for a definition: `lenient apps`, `interesting behaviour`, `important things`
- Right: `This works for most apps.` / name the concrete benefit instead. Say which apps, and why.

### 5. No personification or cute idioms

- Wrong: `the app refuses to talk`, `never heard of the CA`, `what it sends home`, `the server answers`, `blinds their detection`, `which the app slipped past`, `lands in a directory`, `disarm the pin at the source`
- Right: `the app does not trust the proxy`, `Burp's CA is not in its trust stores`, `what data it sends back`, `the command exits`, ...

### 6. No writerly compressions

- Wrong: `root and jailbreak checks being the classic case` (absolute construction)
- Wrong: `The trade is that ...` → `The downside is that ...`
- Wrong: `Match it to your Python, not the system` (compressed past clarity)
- Wrong: `drop the PEM in place`, `by whichever path fits`, `before worrying about certificates`
- Right: spell the sentence out plainly, even if it gets a few words longer.

### 7. Jargon must be explained on first use

- Wrong: bare `REPL`
- Right: `an interactive console in the process`

### 8. Steps must be actionable

If a numbered step says "drop X into Y", the reader needs to know where X comes from, how it gets there, and why the details matter (e.g. rename to `libfrida-gadget.so` because Android only loads `lib*.so`). If automation exists (`objection patchapk`), lead with it and keep the manual path as a fallback.

### 9. Content rule hard lines (from CONTENT_FORMATTING.md)

- No em dashes anywhere. Ever.
- Avoid: `overwhelmingly`, `composable`, `leverage`, `seamlessly`, `delve`, `robust`, `cutting-edge`, `mental model`, `gotcha`
- No false causation.
- Consistent `you` (default), never mixed with `we`.
- Bullet sub-labels use colons, not dashes.

### 10. Verification

After editing, reread the full file once more, then grep (scoped to that file only, not the repo) for the pattern classes above: em dash, `worth `, `the one to`, `the one worth`, `usual trap`, `catch,`, `fiddly`, `refuses to`, `sends home`, `never heard`, `the piece that`, `that matter`, `disambiguate`, `build habits`, `batteries`, superlatives. Report what was fixed, and say explicitly that the whole file was checked, not just flagged lines.

When the user quotes a phrase as an objection, it is an example of the class, not a request to fix exactly that one instance.

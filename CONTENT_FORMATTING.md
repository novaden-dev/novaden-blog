# Content Formatting Rules

This document defines the formatting conventions for all blog posts under `src/data/blog/`. When writing or editing a post, follow these rules to maintain consistency across the blog.

For **what** to write and **where it belongs** (atoms vs cheat sheets vs cert reviews), see [CONTENT_SYSTEM.md](./CONTENT_SYSTEM.md).

---

## Voice and Prose

### No em dashes
Do not use em dashes (`—`) in post content. Replace with commas, periods, parentheses, or colons depending on the sentence.

- Wrong: `Fedora — sponsored by Red Hat — is bleeding edge.`
- Right: `Fedora, sponsored by Red Hat, gets new kernels quickly.`
- Right: `Fedora (sponsored by Red Hat) gets new kernels quickly.`

### Plain language
Write words people actually say out loud. Avoid words that signal "AI prose" or "marketing copy":

- Avoid: `overwhelmingly`, `composable`, `leverage`, `seamlessly`, `delve`, `robust`, `cutting-edge`
- Prefer: simpler, more direct alternatives (`mostly`, `you can stitch them together`, `use`, `smoothly`, `dig into`, `solid`, `new`)

### No false causation
Do not invent causal chains that sound nice but are not strictly true. If you're claiming X causes Y, you should be able to defend it. When in doubt, present facts side by side without claiming causation.

- Weak: `Linux is open source, which is why it runs every server.`
- Better: `Linux is open source. In practice, it runs most servers, containers, and embedded devices.`

### Consistent "you" vs "we"
Pick one and stay consistent within a single post. Default to "you" — it's more direct and modern. Do not mix them within the same post.

### Voice by archetype (see CONTENT_SYSTEM.md)
- **Atoms and cheat sheets**: third-person, instructional. Reference material that reads cold.
- **Cert reviews and journey posts** (e.g. homelab series): first-person. Your story.
- Light first-person opinion inside an atom is fine sparingly (one or two per post max) when it adds genuine value.

### Bullet sub-labels
When a bullet has a short label followed by an explanation, use a colon, not an em dash:

- Right: `- **Kernel**: the core of Linux.`
- Wrong: `- **Kernel** — the core of Linux.`

---

## Code Blocks

Always use **fenced code blocks** (triple backticks) with a language specifier. Never use 4-space indentation for code blocks.

```markdown
```json
{"key": "value"}
```
```

Plain text (URLs, paths, shell output without a specific language) should use `text`:

```markdown
```text
/var/www/images/../../../../etc/passwd
```
```

Common language specifiers: `json`, `javascript`, `bash`, `text`, `html`, `css`, `yaml`.

---

## Headings

| Level | Usage |
|-------|-------|
| `##` | Main sections (Introduction, Exploitation, Remediation, etc.) |
| `###` | Subsections within a main section |

Do not use `#` (h1) or `####` (h4) in post bodies.

---

## Remediation Section

Every post should end with a `## Remediation` section. Structure it as follows:

1. An **introductory sentence or short paragraph** summarizing the prevention strategy.
2. A **bullet (unordered) list** using dashes (`-`) of actionable remediation steps.
3. If the section is extensive, group items under a `### General Guidelines` subheading.

Do not use ordered (numbered) lists in Remediation.

---

## Lists

- Use **dashes** (`-`) for unordered lists.
- Use **numbers** (`1.`, `2.`) only for step-by-step instructions or sequences where order matters (e.g., attack steps, testing procedures).

---

## Tables

Use markdown tables when presenting **structured comparison data** — for example:

- Shell metacharacters and their descriptions
- Useful commands across platforms
- Response header meanings
- Cache rule configurations

Do not use tables for simple, linear information that works better as a list or paragraph.

---

## Blockquotes

Use blockquotes (`>`) for notes, tips, warnings, or quoted external documentation. Format them with a bold label:

```markdown
> **Note:** Null byte injection is largely mitigated in modern languages.
> **Testing Tip:** Ensure each test request has a different cache key.
```

---

## Inline Code

Wrap the following in backticks:

- File paths (`/etc/passwd`)
- Code snippets within sentences (`$ne`, `$where`)
- Command names (`whoami`, `nslookup`)
- URL paths (`/.git/`, `/my-profile`)

---

## Bold Text

Use bold (`**`) sparingly for:

- Key takeaways or summary statements
- Important directives in remediation
- Labels in blockquotes (`**Note:**`, `**Testing Tip:**`)

---

## File Ending

Every post file must end with a single trailing newline.

---

## Summary Checklist

- [ ] No em dashes anywhere in the body
- [ ] Voice matches the post archetype (atoms/cheat sheets: third-person; cert reviews/journeys: first-person)
- [ ] Consistent "you" or "we" (no mixing within a post)
- [ ] Plain language, no AI-prose words (`overwhelmingly`, `composable`, `leverage`, etc.)
- [ ] No invented causation in explanations
- [ ] Code blocks are fenced (` ``` `) with a language specifier
- [ ] Remediation uses a dash (`-`) bullet list with an intro sentence (security posts only)
- [ ] Tables are used for comparison data where appropriate
- [ ] Blockquotes use bold labels (`**Note:**`, `**Tip:**`, `**Danger:**`, `**Gotcha:**`)
- [ ] Inline code is backtick-wrapped
- [ ] Headings are `##` and `###` only
- [ ] Bullet sub-labels use a colon, not an em dash
- [ ] File ends with a newline

# novaden-blog

Source for [novaden.dev](https://novaden.dev). The blog is a static site built with [Astro](https://astro.build/), forked from the [AstroPaper](https://github.com/satnaing/astro-paper) theme. Content is authored in Markdown under `src/data/blog`.

## Tech Stack

- **Astro** for static-site generation
- **AstroPaper** theme (customized)
- **pnpm** for package management
- **Tailwind CSS** for styling
- **Pagefind** for client-side full-text search
- **GitHub Actions + GHCR** for image builds
- **Homelab + nginx container** for hosting

## Local Development

Requires Node 20+ and [Corepack](https://nodejs.org/api/corepack.html) enabled (`corepack enable`). The pnpm version is pinned via the `packageManager` field in `package.json`, so Corepack will fetch the right version automatically.

```bash
pnpm install
pnpm dev
```

The dev server runs at `http://localhost:4321`.

> **Note on search:** Pagefind only works after a real build. The `/search` page will show a warning in dev mode until you run `pnpm build` at least once.

## Writing Content

Two standards govern every post on this blog. Read them before adding or editing content:

- [`CONTENT_SYSTEM.md`](./CONTENT_SYSTEM.md) — **what** to write and **where** it goes. Defines the three post archetypes (atoms, cheat sheets, cert reviews), the overlap rule, tag taxonomy, and the workflow for starting a new topic.
- [`CONTENT_FORMATTING.md`](./CONTENT_FORMATTING.md) — **how** to format prose, code, tables, blockquotes, voice, and headings.

### Where things live

| What | Path |
|---|---|
| Blog posts | `src/data/blog/*.md` |
| About page | `src/pages/about.md` |
| Images | `public/images/` (referenced from posts as `/images/<file>`) |
| Site config (title, author, social, etc.) | `src/config.ts` |
| Astro config (env vars, integrations) | `astro.config.ts` |

### Frontmatter schema

Defined in `src/content.config.ts`. Required fields: `title`, `description`, `pubDatetime`. See existing posts for reference (`src/data/blog/linux-foundations.md` is the canonical atom example; `src/data/blog/linux-cheatsheet.md` is the canonical cheat sheet example).

### Post URLs

Routes use the `slug` field in frontmatter, not the filename. Posts are served at `/posts/<slug>`.

## Environment Variables

The blog reads one optional environment variable:

- `PUBLIC_GOOGLE_SITE_VERIFICATION`: Google Search Console verification token. Omit it if you don't use Search Console.

Set it locally with a `.env` file at the repo root, or in your deployment environment.

## Build & Deploy

On every push to `main`:

1. `.github/workflows/deploy.yml` builds the production image using the root `Dockerfile`.
2. The image is published to `ghcr.io/novaden-dev/novaden-blog:latest`.
3. A webhook on my homelab pulls the new image and recreates the blog container.

The production image is a multi-stage build:

- **Build stage:** node:lts with pnpm, runs `pnpm run build` to produce static files in `dist/`.
- **Runtime stage:** nginx:alpine serving `dist/` on port 80.

On every pull request:

- `.github/workflows/ci.yml` runs lint, format check, and a full build. PRs must pass before merge.

## Available Scripts

| Command | What it does |
|---|---|
| `pnpm dev` | Start the dev server at `http://localhost:4321` |
| `pnpm build` | Type-check, build the static site, generate the Pagefind search index |
| `pnpm preview` | Preview the built site locally |
| `pnpm sync` | Regenerate Astro's TypeScript types from content collections |
| `pnpm lint` | Run ESLint |
| `pnpm format` | Auto-format with Prettier |
| `pnpm format:check` | Verify formatting without writing changes |

## Project Layout

```text
.
├── src/
│   ├── data/blog/          # Blog post markdown files
│   ├── pages/              # Astro pages (about, index, posts, tags, search)
│   ├── layouts/            # Page layouts
│   ├── components/         # Reusable Astro components
│   ├── config.ts           # Site config (title, author, social links)
│   └── content.config.ts   # Content collection schema
├── public/                 # Static assets served as-is
├── .github/workflows/      # CI and deploy pipelines
├── Dockerfile              # Production image (multi-stage: build then nginx)
├── CONTENT_SYSTEM.md       # Post archetypes, taxonomy, workflow
└── CONTENT_FORMATTING.md   # Prose, voice, formatting rules
```

## Credits

Based on [AstroPaper](https://github.com/satnaing/astro-paper) by [Sat Naing](https://satnaing.dev/).

## License

MIT. See [LICENSE](./LICENSE).

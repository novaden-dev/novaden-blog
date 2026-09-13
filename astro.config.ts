import { readdirSync, readFileSync } from "node:fs";
import { basename, join } from "node:path";
import { defineConfig, envField, fontProviders } from "astro/config";
import tailwindcss from "@tailwindcss/vite";
import sitemap from "@astrojs/sitemap";
import remarkToc from "remark-toc";
import remarkCollapse from "remark-collapse";
import {
  transformerNotationDiff,
  transformerNotationHighlight,
  transformerNotationWordHighlight,
} from "@shikijs/transformers";
import { transformerFileName } from "./src/utils/transformers/fileName";
import { SITE } from "./src/config";

// /projects skips itself when no app is public, but the sitemap lists every
// static route whether or not a file was written, so it has to be told.
// Mirrors projectFilter for production; the path is PROJECTS_PATH, which can't
// be imported here because content.config.ts pulls in astro:content.
const PROJECTS_DIR = "src/data/projects";
const hasPublicProjects = readdirSync(PROJECTS_DIR, { recursive: true })
  .map(String)
  .filter(file => file.endsWith(".md") && !basename(file).startsWith("_"))
  .some(file => {
    const frontmatter =
      readFileSync(join(PROJECTS_DIR, file), "utf8").split(/^---$/m)[1] ?? "";
    return !/^draft:\s*true\s*$/m.test(frontmatter);
  });

// https://astro.build/config
export default defineConfig({
  site: SITE.website,
  // /series/ was the old address for what are now collections. Nothing here is
  // public yet, but the rename is cheap to make safe, so it gets made safe.
  // Listed explicitly: a static build cannot enumerate a wildcard's paths, and
  // one entry per collection is honest about what actually existed.
  redirects: {
    "/series": "/collections",
    "/series/homelab": "/collections/homelab",
  },
  integrations: [
    sitemap({
      filter: page =>
        (SITE.showArchives || !page.endsWith("/archives")) &&
        (hasPublicProjects || !/\/projects\/?$/.test(page)),
    }),
  ],
  markdown: {
    remarkPlugins: [remarkToc, [remarkCollapse, { test: "Table of contents" }]],
    shikiConfig: {
      // For more themes, visit https://shiki.style/themes
      themes: { light: "min-light", dark: "night-owl" },
      defaultColor: false,
      wrap: false,
      transformers: [
        transformerFileName({ style: "v2", hideDot: false }),
        transformerNotationHighlight(),
        transformerNotationWordHighlight(),
        transformerNotationDiff({ matchAlgorithm: "v3" }),
      ],
    },
  },
  vite: {
    // eslint-disable-next-line
    // @ts-ignore
    // This will be fixed in Astro 6 with Vite 7 support
    // See: https://github.com/withastro/astro/issues/14030
    plugins: [tailwindcss()],
    optimizeDeps: {
      exclude: ["@resvg/resvg-js"],
    },
  },
  image: {
    responsiveStyles: true,
    layout: "constrained",
  },
  env: {
    schema: {
      PUBLIC_GOOGLE_SITE_VERIFICATION: envField.string({
        access: "public",
        context: "client",
        optional: true,
      }),
    },
  },
  experimental: {
    preserveScriptOrder: true,
    fonts: [
      // Three voices. Mono is not decoration here: the shell chrome and every
      // file row are mono because that is what a file listing is. Chivo takes
      // headings, Newsreader takes anything read at length.
      {
        name: "JetBrains Mono",
        cssVariable: "--font-mono",
        provider: fontProviders.google(),
        fallbacks: ["ui-monospace", "SFMono-Regular", "Consolas", "monospace"],
        weights: [400, 500, 700],
        styles: ["normal"],
      },
      {
        name: "Chivo",
        cssVariable: "--font-chivo",
        provider: fontProviders.google(),
        fallbacks: ["Helvetica Neue", "Arial", "sans-serif"],
        weights: [600, 700, 900],
        styles: ["normal"],
      },
      {
        name: "Newsreader",
        cssVariable: "--font-newsreader",
        provider: fontProviders.google(),
        fallbacks: ["Georgia", "Times New Roman", "serif"],
        weights: [400, 500, 600],
        styles: ["normal", "italic"],
      },
    ],
  },
});

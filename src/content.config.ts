import { defineCollection, z } from "astro:content";
import { glob } from "astro/loaders";
import { SITE } from "@/config";
import { FORMATS } from "@/utils/formats";
import { tagProblems } from "@/utils/tags";

export const BLOG_PATH = "src/data/blog";
export const PROJECTS_PATH = "src/data/projects";
export const COLLECTIONS_PATH = "src/data/collections";

const blog = defineCollection({
  loader: glob({ pattern: "**/[^_]*.md", base: `./${BLOG_PATH}` }),
  schema: ({ image }) =>
    z
      .object({
        author: z.string().default(SITE.author),
        pubDatetime: z.date(),
        modDatetime: z.date().optional().nullable(),
        title: z.string(),
        featured: z.boolean().optional(),
        draft: z.boolean().optional(),
        // Subjects only, each one from the registry in src/utils/tags.ts.
        tags: z.array(z.string()).default([]),
        category: z.enum(["notes", "journal", "cert-review"]).default("notes"),
        format: z.enum(FORMATS).optional(),
        ogImage: image().or(z.string()).optional(),
        description: z.string(),
        canonicalURL: z.string().optional(),
        hideEditPost: z.boolean().optional(),
        timezone: z.string().optional(),
      })
      // A published post's tags must be canonical. Drafts are exempt: they are
      // unreviewed, and each one is normalized when it is reviewed, not all at
      // once. This keys off `draft` rather than postFilter because dev shows
      // every draft, and the check must not depend on which command is running.
      .superRefine((data, ctx) => {
        if (data.draft) return;
        for (const message of tagProblems(data.tags)) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            path: ["tags"],
            message,
          });
        }
      }),
});

// Projects are not posts: nobody reads a tool, they use it. So they get their
// own collection rather than a fourth category, which would break the rule
// that `category` describes how something is read.
const projects = defineCollection({
  loader: glob({ pattern: "**/[^_]*.md", base: `./${PROJECTS_PATH}` }),
  schema: z.object({
    name: z.string(),
    tagline: z.string(),
    status: z.enum(["shipping", "prototype", "archived"]),
    stack: z.array(z.string()).default([]),
    repo: z.string(),
    releases: z.string().optional(),
    post: z.string().optional(),
    order: z.number().default(0),
    draft: z.boolean().optional(),
  }),
});

// A placement is one inclusion of one post in one collection. It is a record
// in its own right, not a property of the post: the reading order lives here,
// so reordering a collection never edits an article, and the same post can sit
// in several collections with different neighbours in each.
const placement = z.object({
  // Stable and unique across the whole site. Assigned once and never derived
  // from position, so reordering leaves links and navigation state intact.
  id: z.string(),
  // The target post's id, which is also its /posts/<id> address.
  post: z.string(),
  // Why this item belongs here. Context for a shared item, never a second
  // version of its instructions.
  note: z.string().optional(),
  // step: a numbered part of the reading sequence.
  // supplementary: relevant and listed, but never numbered.
  role: z.enum(["step", "supplementary"]).default("step"),
  // Whether the collection may publish while this target is unavailable.
  // Deliberately separate from `role`: "the reader may skip this" and "the
  // page need not exist yet" are different statements.
  required: z.boolean().default(true),
  // Contextual label for this occurrence. Must stay recognisable as the real
  // title; it renames nothing.
  label: z.string().optional(),
  // Optional grouping heading within the collection.
  section: z.string().optional(),
});

// A collection is a deliberately selected body of content with a stated reader
// purpose. Membership is by reference, so a post is never owned by one.
const readingCollections = defineCollection({
  loader: glob({ pattern: "**/[^_]*.md", base: `./${COLLECTIONS_PATH}` }),
  schema: z.object({
    title: z.string(),
    description: z.string(),
    // How it is read, which is what decides how it is presented:
    //   series       → deliberately ordered, read front to back
    //   handbook     → structured knowledge, entered at any point
    //   reading-list → a curated selection with no implied order
    kind: z.enum(["series", "handbook", "reading-list"]).default("series"),
    status: z.enum(["ongoing", "complete"]).default("ongoing"),
    draft: z.boolean().default(false),
    entries: z.array(placement).default([]),
  }),
});

export const collections = {
  blog,
  projects,
  collections: readingCollections,
};

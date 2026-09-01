import { defineCollection, z } from "astro:content";
import { glob } from "astro/loaders";
import { SITE } from "@/config";

export const BLOG_PATH = "src/data/blog";
export const PROJECTS_PATH = "src/data/projects";

const blog = defineCollection({
  loader: glob({ pattern: "**/[^_]*.md", base: `./${BLOG_PATH}` }),
  schema: ({ image }) =>
    z.object({
      author: z.string().default(SITE.author),
      pubDatetime: z.date(),
      modDatetime: z.date().optional().nullable(),
      title: z.string(),
      featured: z.boolean().optional(),
      draft: z.boolean().optional(),
      tags: z.array(z.string()).default(["others"]),
      category: z.enum(["notes", "journal", "cert-review"]).default("notes"),
      series: z.string().optional(),
      seriesOrder: z.number().optional(),
      ogImage: image().or(z.string()).optional(),
      description: z.string(),
      canonicalURL: z.string().optional(),
      hideEditPost: z.boolean().optional(),
      timezone: z.string().optional(),
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

export const collections = { blog, projects };

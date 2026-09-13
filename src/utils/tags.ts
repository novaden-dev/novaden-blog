import { FORMATS } from "./formats";

// The tag registry: the only place a tag can come from.
//
// A tag names a subject a post is substantially about, and nothing else. How
// a post is read is its category, its shape is its format, and its place in a
// series is a collection placement. How many posts use a tag plays no part: a
// correct tag on one post is still correct.
//
// Each key is the canonical name. Aliases catch the other spellings that
// source notes arrive with, and the build points at the canonical tag rather
// than accepting them, so two names for one subject never coexist. The domain
// groups subjects (technical, career, life) so that split is never repeated on
// posts. A parent lets a broader tag's page include its descendants later,
// which is why a post never carries both.

export const DOMAINS = ["technical", "career", "life"] as const;

type TagDefinition = {
  domain: (typeof DOMAINS)[number];
  aliases?: string[];
  parent?: string;
};

export const TAGS: Record<string, TagDefinition> = {
  docker: { domain: "technical" },
  git: { domain: "technical" },
  gitops: { domain: "technical" },
  kubernetes: { domain: "technical", aliases: ["k3s", "k8s"] },
  linux: { domain: "technical" },
  networking: { domain: "technical" },
  selfhosting: { domain: "technical" },
  ssh: { domain: "technical" },
};

const names = new Set(Object.keys(TAGS));
const formats = new Set<string>(FORMATS);
const aliasOf = new Map<string, string>();

// A broken registry would quietly let bad tags through, so it fails loudly
// instead: an alias that is also a tag, a format word used as a tag, or a
// parent that does not exist.
for (const [name, tag] of Object.entries(TAGS)) {
  if (formats.has(name)) {
    throw new Error(`[tags] "${name}" is a format and cannot be a tag`);
  }
  if (tag.parent && !names.has(tag.parent)) {
    throw new Error(
      `[tags] "${name}" has parent "${tag.parent}", which is not a registered tag`
    );
  }
  for (const alias of tag.aliases ?? []) {
    if (names.has(alias) || formats.has(alias) || aliasOf.has(alias)) {
      throw new Error(
        `[tags] alias "${alias}" of "${name}" is already a tag, a format, or another tag's alias`
      );
    }
    aliasOf.set(alias, name);
  }
}

/**
 * Everything wrong with one post's tags, each message naming the fix. Empty
 * when every tag is canonical.
 */
export function tagProblems(tags: string[]): string[] {
  return tags.flatMap(tag => {
    if (names.has(tag)) return [];
    if (formats.has(tag)) {
      return [
        `"${tag}" is a format, not a tag. Remove it from tags and set \`format: ${tag}\`.`,
      ];
    }
    const canonical = aliasOf.get(tag);
    if (canonical) {
      return [`"${tag}" is an alias. Use the canonical tag "${canonical}".`];
    }
    return [
      `"${tag}" is not a registered tag. Use an existing tag, or add it to src/utils/tags.ts if it is a durable subject.`,
    ];
  });
}

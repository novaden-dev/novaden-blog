import type { CollectionEntry } from "astro:content";
import {
  getCollections,
  type ResolvedCollection,
  type ResolvedPlacement,
} from "./collections";
import { getPath } from "./getPath";
import { slugifyStr } from "./slugify";
import {
  getHandbookConfig,
  type HandbookConfig,
} from "@/handbooks";

// The generic handbook system. These functions take a handbook configuration
// (or resolve one by id) and know nothing about any specific handbook. OSCP,
// DevOps or anything else is just a config passed through here.

export type { HandbookConfig } from "@/handbooks";
export { getHandbookConfig, handbookIds, handbookConfigs, isHandbookId } from "@/handbooks";

/** The in-shell route for a note in a handbook. */
export function handbookHref(config: HandbookConfig, slug: string): string {
  return `${config.base}/${slug}`;
}

/**
 * Where a post is read. A handbook chapter goes to its documentation shell;
 * everything else keeps its ordinary post path. This is what routes every
 * listing, tag page, feed and jump-palette entry into the right place.
 */
export function postHref(post: CollectionEntry<"blog">): string {
  const config = getHandbookConfig(post.data.handbook);
  if (config) return handbookHref(config, post.id);
  return getPath(post.id, post.filePath);
}

/**
 * Resolve an internal handbook cross-link (a target note title, optionally with
 * a heading) to a route within the handbook. Used when converting the source
 * vault's wiki-links.
 */
export function resolveHandbookLink(
  config: HandbookConfig,
  target: string,
  heading?: string
): string {
  const frag = heading ? `#${slugifyStr(heading)}` : "";
  return `${handbookHref(config, slugifyStr(target))}${frag}`;
}

export type TreeNote = {
  type: "note";
  title: string;
  slug: string;
  href: string;
};

export type TreeFolder = {
  type: "folder";
  name: string;
  /** Full path, e.g. "Techniques/Active Directory" — the localStorage key. */
  path: string;
  children: TreeNode[];
};

export type TreeNode = TreeFolder | TreeNote;

const isHidden = (section: string, hiddenPaths?: string[]): boolean =>
  !!hiddenPaths?.some(
    prefix => section === prefix || section.startsWith(`${prefix}/`)
  );

/** Build the hierarchical tree from placements, preserving declared order. */
export function buildHandbookTree(
  items: ResolvedPlacement[],
  config: HandbookConfig
): TreeNode[] {
  const root: TreeFolder = { type: "folder", name: "", path: "", children: [] };

  for (const item of items) {
    const section = item.placement.section?.trim() || "More";
    if (isHidden(section, config.hiddenPaths)) continue;

    const parts = section
      .split("/")
      .map(part => part.trim())
      .filter(Boolean);

    let cursor = root;
    let acc = "";
    for (const part of parts) {
      acc = acc ? `${acc}/${part}` : part;
      let next = cursor.children.find(
        (child): child is TreeFolder =>
          child.type === "folder" && child.path === acc
      );
      if (!next) {
        next = { type: "folder", name: part, path: acc, children: [] };
        cursor.children.push(next);
      }
      cursor = next;
    }

    cursor.children.push({
      type: "note",
      title: item.placement.label ?? item.post.data.title,
      slug: item.post.id,
      href: handbookHref(config, item.post.id),
    });
  }

  return root.children;
}

export type ResolvedHandbook = {
  config: HandbookConfig;
  collection: ResolvedCollection;
  tree: TreeNode[];
};

/** Resolve a handbook by id: its config, its collection, and its nav tree. */
export async function getHandbook(
  id: string
): Promise<ResolvedHandbook | undefined> {
  const config = getHandbookConfig(id);
  if (!config) return undefined;
  const collections = await getCollections();
  const collection = collections.find(entry => entry.id === config.collectionId);
  if (!collection) return undefined;
  return { config, collection, tree: buildHandbookTree(collection.items, config) };
}

/** Every note (placement) in a handbook, in reading order. */
export async function getHandbookDocuments(
  id: string
): Promise<ResolvedPlacement[]> {
  const handbook = await getHandbook(id);
  return handbook?.collection.items ?? [];
}

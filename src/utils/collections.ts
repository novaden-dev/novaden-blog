import { getCollection, type CollectionEntry } from "astro:content";
import postFilter from "./postFilter";

// Collections are resolved from placement records, never from the posts
// themselves. Everything the site shows about a sequence (contents, numbering,
// previous/next, the "you are here" rail) is derived here, from one place, so
// the three can never disagree.

export type Placement = CollectionEntry<"collections">["data"]["entries"][number];

export type ResolvedPlacement = {
  placement: Placement;
  post: CollectionEntry<"blog">;
  /** Position in the reading sequence, or null for supplementary material. */
  step: number | null;
};

export type ResolvedCollection = {
  id: string;
  entry: CollectionEntry<"collections">;
  /** Every resolved placement, in declared order. */
  items: ResolvedPlacement[];
  /** Only the numbered reading steps. */
  steps: ResolvedPlacement[];
  /** Listed, but never numbered. */
  extras: ResolvedPlacement[];
};

export type Membership = {
  collection: ResolvedCollection;
  placement: Placement;
  step: number | null;
};

/**
 * Fails the build with a message naming the file to fix. A dangling reference
 * is a broken page, so it stops the build rather than rendering a gap.
 */
function fail(message: string): never {
  throw new Error(`[collections] ${message}`);
}

/**
 * Resolves every collection against the post corpus and validates the
 * references. Returns public collections only: drafts, and collections whose
 * required members are unavailable, never reach a rendered page.
 */
export async function getCollections(): Promise<ResolvedCollection[]> {
  const defs = await getCollection("collections");
  const posts = await getCollection("blog");

  const byId = new Map(posts.map(post => [post.id, post]));
  const seenPlacements = new Map<string, string>();
  const resolved: ResolvedCollection[] = [];

  for (const entry of defs) {
    const seenTargets = new Map<string, Placement>();
    const items: ResolvedPlacement[] = [];
    let step = 0;

    for (const placement of entry.data.entries) {
      // Placement ids address a specific occurrence, so a duplicate would make
      // two different reading positions indistinguishable.
      const owner = seenPlacements.get(placement.id);
      if (owner) {
        fail(
          `duplicate placement id "${placement.id}" in ${entry.id} (already used in ${owner})`
        );
      }
      seenPlacements.set(placement.id, entry.id);

      const post = byId.get(placement.post);

      if (!post) {
        fail(
          `placement "${placement.id}" in ${entry.id} points at "${placement.post}", which is not a post`
        );
      }

      // Repetition is allowed when it is deliberate, which a note is the
      // evidence for. Without one it is almost always a copy-paste slip.
      const twin = seenTargets.get(placement.post);
      if (twin && !placement.note && !twin.note) {
        console.warn(
          `[collections] ${entry.id} includes "${placement.post}" twice (${twin.id}, ${placement.id}) with no note on either. Intentional repeats should say why.`
        );
      }
      seenTargets.set(placement.post, placement);

      // Availability is about the target existing publicly. It is separate
      // from whether the reader is expected to read it.
      if (!postFilter(post)) {
        if (placement.required && !entry.data.draft) {
          fail(
            `${entry.id} is published but its required member "${placement.post}" (placement ${placement.id}) is not available. Mark the placement \`required: false\`, or publish the post, or draft the collection.`
          );
        }
        // An unavailable optional member is dropped whole. Nothing about it,
        // not even its title, reaches the page.
        continue;
      }

      items.push({
        placement,
        post,
        step: placement.role === "step" ? ++step : null,
      });
    }

    resolved.push({
      id: entry.id,
      entry,
      items,
      steps: items.filter(item => item.step !== null),
      extras: items.filter(item => item.step === null),
    });
  }

  return resolved
    .filter(collection => !collection.entry.data.draft)
    .sort((a, b) => a.entry.data.title.localeCompare(b.entry.data.title));
}

/**
 * Every collection a post appears in. A post belongs to as many as its
 * placements say, which is why a page cannot ask "which series am I in?" and
 * expect one answer.
 */
export function getMemberships(
  postId: string,
  collections: ResolvedCollection[]
): Membership[] {
  return collections.flatMap(collection =>
    collection.items
      .filter(item => item.post.id === postId)
      .map(item => ({
        collection,
        placement: item.placement,
        step: item.step,
      }))
  );
}

/** The step before and after a given placement, within that placement only. */
export function neighbours(
  collection: ResolvedCollection,
  placementId: string
) {
  const index = collection.steps.findIndex(
    item => item.placement.id === placementId
  );
  if (index < 0) return { prev: undefined, next: undefined };
  return {
    prev: collection.steps[index - 1],
    next: collection.steps[index + 1],
  };
}

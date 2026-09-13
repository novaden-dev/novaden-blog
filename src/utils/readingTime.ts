import type { CollectionEntry } from "astro:content";

// A comfortable pace for technical prose. Slower than the usual 250 because
// these posts are read to be understood, not skimmed.
const WORDS_PER_MINUTE = 230;

/**
 * Words a reader actually reads. Code is not read at prose speed, and a
 * cheatsheet can be three-quarters code, so counting it would turn a page of
 * commands into a half-hour essay. Link and image targets go too: a URL is not
 * a word anyone reads.
 */
export function proseWords(markdown: string): number {
  const prose = markdown
    .replace(/^(```|~~~)[^\n]*\n[\s\S]*?^\1[^\n]*$/gm, " ")
    .replace(/<!--[\s\S]*?-->/g, " ")
    .replace(/!\[[^\]]*\]\([^)]*\)/g, " ")
    .replace(/\[([^\]]*)\]\([^)]*\)/g, "$1")
    .replace(/<[^>]+>/g, " ");

  return prose.split(/\s+/).filter(token => /[\p{L}\p{N}]/u.test(token)).length;
}

/** Whole minutes, never less than one: "0 min" reads as an empty file. */
export function getReadingTime(post: CollectionEntry<"blog">): number {
  return Math.max(
    1,
    Math.round(proseWords(post.body ?? "") / WORDS_PER_MINUTE)
  );
}

/**
 * A body of reading, summed from the same whole minutes its rows show, so a
 * total always equals the numbers listed under it.
 */
export function totalReadingTime(posts: CollectionEntry<"blog">[]): number {
  return posts.reduce((sum, post) => sum + getReadingTime(post), 0);
}

/**
 * "25 min", or "1 h 12 min" once a total passes the hour. Single posts stay in
 * minutes: a column of mixed units is harder to scan.
 */
export function formatDuration(minutes: number): string {
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest ? `${hours} h ${rest} min` : `${hours} h`;
}

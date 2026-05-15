import type { CollectionEntry } from "astro:content";
import { slugifyStr } from "./slugify";
import postFilter from "./postFilter";

interface Series {
  series: string;
  seriesName: string;
  count: number;
}

const getUniqueSeries = (posts: CollectionEntry<"blog">[]): Series[] => {
  const counts = new Map<string, { seriesName: string; count: number }>();

  for (const post of posts.filter(postFilter)) {
    const name = post.data.series;
    if (!name) continue;
    const slug = slugifyStr(name);
    const existing = counts.get(slug);
    if (existing) {
      existing.count += 1;
    } else {
      counts.set(slug, { seriesName: name, count: 1 });
    }
  }

  return Array.from(counts.entries())
    .map(([series, { seriesName, count }]) => ({ series, seriesName, count }))
    .sort((a, b) => a.series.localeCompare(b.series));
};

export default getUniqueSeries;

import type { CollectionEntry } from "astro:content";
import { slugifyStr } from "./slugify";
import postFilter from "./postFilter";

const getPostsBySeries = (posts: CollectionEntry<"blog">[], series: string) =>
  posts
    .filter(postFilter)
    .filter(
      post => post.data.series && slugifyStr(post.data.series) === series
    )
    .sort(
      (a, b) => (a.data.seriesOrder ?? 0) - (b.data.seriesOrder ?? 0)
    );

export default getPostsBySeries;

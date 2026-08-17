import type { CollectionEntry } from "astro:content";
import postFilter from "./postFilter";
import { CATEGORIES, CATEGORY_ORDER, type CategoryKey } from "./categories";

export interface CategoryInfo {
  category: CategoryKey;
  label: string;
  description: string;
  count: number;
}

const getUniqueCategories = (
  posts: CollectionEntry<"blog">[]
): CategoryInfo[] => {
  const counts = new Map<CategoryKey, number>();

  for (const post of posts.filter(postFilter)) {
    const category = (post.data.category ?? "notes") as CategoryKey;
    counts.set(category, (counts.get(category) ?? 0) + 1);
  }

  return CATEGORY_ORDER.filter(category => counts.has(category)).map(
    category => ({
      category,
      label: CATEGORIES[category].label,
      description: CATEGORIES[category].description,
      count: counts.get(category)!,
    })
  );
};

export default getUniqueCategories;

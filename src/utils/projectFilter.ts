import type { CollectionEntry } from "astro:content";

// The single answer to "is this app visible?", on the same terms as posts:
// dev shows every app so drafts can be previewed, production shows only what
// has been marked ready. Anything that lists apps must come through here.
const projectFilter = ({ data }: CollectionEntry<"projects">) =>
  import.meta.env.DEV || !data.draft;

export default projectFilter;

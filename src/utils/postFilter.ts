import type { CollectionEntry } from "astro:content";
import { SITE } from "@/config";

// The single answer to "is this post visible?".
//
// Dev shows the whole corpus, drafts and not-yet-due posts included: while
// writing, the thing you need to see is what is *not* live yet. Production
// shows only what has been marked ready and has reached its date. Anything
// that filters posts must come through here, or the two disagree and a
// listing links to a page that was never generated.
const postFilter = ({ data }: CollectionEntry<"blog">) => {
  if (import.meta.env.DEV) return true;

  const isPublishTimePassed =
    Date.now() >
    new Date(data.pubDatetime).getTime() - SITE.scheduledPostMargin;

  return !data.draft && isPublishTimePassed;
};

export default postFilter;

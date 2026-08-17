// Content "kind" axis — the primary way posts are grouped for navigation.
// Exactly one per post. Topic lives in `tags`, sequencing lives in `series`.
//
// The split is by SHAPE, not subject:
//   notes   → stuff you look up (how things work, commands) — you return to it
//   journal → stuff you read (a story, a take, an experience) — once, start to finish
// The same topic can live in both (a Redis cheat sheet vs a Redis war story).
export const CATEGORIES = {
  notes: {
    label: "Notes",
    description:
      "What I know — how things work, plus the cheat sheets I keep open while working.",
  },
  journal: {
    label: "Journal",
    description:
      "What I did, went through, or think — journeys, opinions, and war stories.",
  },
  "cert-review": {
    label: "Cert Reviews",
    description:
      "Honest takes on certifications — what they cost, what they're worth, what to expect.",
  },
} as const;

export type CategoryKey = keyof typeof CATEGORIES;

// Display order on the homepage and category index.
export const CATEGORY_ORDER: CategoryKey[] = ["notes", "journal", "cert-review"];

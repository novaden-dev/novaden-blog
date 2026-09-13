// The format axis: a post's structural shape. Optional, at most one per post,
// and independent of category, so a journal entry can be a write-up.
//
//   cheatsheet  → compressed reference, optimized for fast lookup
//   guide       → a procedural, step-by-step how-to where following it is the point
//   writeup     → a record of building, testing, investigating, or solving something
//   methodology → a repeatable process for a type of work
//   checklist   → an actionable list used to verify or perform work
//
// A post with no format is an explanatory note, and a format is never forced
// onto a post it only roughly fits. These words name shapes, not subjects, so
// the tag registry refuses them as tags.
export const FORMATS = [
  "cheatsheet",
  "guide",
  "writeup",
  "methodology",
  "checklist",
] as const;

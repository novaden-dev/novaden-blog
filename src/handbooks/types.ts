// A handbook is a documentation application rendered from a body of notes. The
// generic handbook system (layout, tree, routing, state) knows nothing about
// any particular handbook: it is handed one of these configurations. To add a
// handbook you write one of these and register it; you never touch the UI.

export type HandbookConfig = {
  /** Stable id. Also the `handbook:` frontmatter value on member notes, the
   *  localStorage namespace, and (by default) the route segment. */
  id: string;
  /** Shown in the top bar and as the handbook's own title. */
  title: string;
  description?: string;
  /** Route base for this handbook, e.g. "/collections/oscp". Member notes live
   *  at `${base}/${slug}`. */
  base: string;
  /** The reading collection (src/data/collections/<id>.md) whose placements
   *  provide this handbook's structure and order. Usually equals `id`. */
  collectionId: string;
  /** Heading shown above the navigation tree. Defaults to `title`. */
  navHeading?: string;
  /** Placement sections to omit from the tree (prefix match on the section
   *  path), e.g. ["Appendix/Internal"]. */
  hiddenPaths?: string[];
  /** Optional note slug the root page should feature; when unset the root
   *  shows the collection's own introduction. */
  defaultDocument?: string;
};

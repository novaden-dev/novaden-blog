import type { HandbookConfig } from "./types";

// The OSCP handbook: one instance of the generic handbook system. Everything
// OSCP-specific lives here, not in any component.
export const oscp: HandbookConfig = {
  id: "oscp",
  title: "OSCP",
  description:
    "A practical PEN-200 field manual: enumeration through Active Directory, built from lab work and repeatable attack paths.",
  base: "/collections/oscp",
  collectionId: "oscp",
  navHeading: "OSCP Field Manual",
};

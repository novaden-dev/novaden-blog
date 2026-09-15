import type { HandbookConfig } from "./types";

// The Mobile handbook: Android and iOS app pentesting. Everything
// mobile-specific lives here, not in any component.
export const mobile: HandbookConfig = {
  id: "mobile",
  title: "Mobile",
  description: "Android and iOS app pentesting notes.",
  base: "/collections/mobile",
  collectionId: "mobile",
  navHeading: "Mobile Pentesting",
};

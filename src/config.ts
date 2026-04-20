export const SITE = {
  website: "https://novaden.dev",
  author: "NovaDen",
  profile: "https://novaden.dev/",
  desc: "Something is getting cooked.",
  title: "NovaDen",
  ogImage: "astropaper-og.jpg",
  lightAndDarkMode: true,
  postPerIndex: 4,
  postPerPage: 4,
  scheduledPostMargin: 15 * 60 * 1000, // 15 minutes
  showArchives: true,
  showBackButton: true,
  editPost: {
    enabled: false,
    text: "Edit page",
    url: "",
  },
  dynamicOgImage: true,
  dir: "ltr",
  lang: "en",
  timezone: "Europe/Istanbul",
} as const;

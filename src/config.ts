export const SITE = {
  website: "https://novaden.dev",
  author: "NovaDen",
  profile: "https://novaden.dev/",
  desc: "This is my notes hub. Part learning diary, part blog, part public scratchpad. Some of it is polished. Some of it is rough.",
  title: "NovaDen",
  ogImage: "og.png",
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

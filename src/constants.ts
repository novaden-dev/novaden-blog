import type { Props } from "astro";
import IconMail from "@/assets/icons/IconMail.svg";
import IconGitHub from "@/assets/icons/IconGitHub.svg";
import IconBrandX from "@/assets/icons/IconBrandX.svg";
import IconLinkedin from "@/assets/icons/IconLinkedin.svg";
import IconWhatsapp from "@/assets/icons/IconWhatsapp.svg";
import IconFacebook from "@/assets/icons/IconFacebook.svg";
import IconTelegram from "@/assets/icons/IconTelegram.svg";
import IconPinterest from "@/assets/icons/IconPinterest.svg";
import { SITE } from "@/config";

interface Social {
  name: string;
  href: string;
  linkTitle: string;
  icon: (_props: Props) => Element;
}

export const SOCIALS: Social[] = [
  {
    name: "GitHub",
    href: "https://github.com/novaden-dev",
    linkTitle: `${SITE.title} on GitHub`,
    icon: IconGitHub,
  },
  {
    name: "LinkedIn",
    href: "https://www.linkedin.com/in/anasehab/",
    linkTitle: `${SITE.title} on LinkedIn`,
    icon: IconLinkedin,
  },
  {
    name: "Mail",
    href: "mailto:kayra@novaden.dev",
    linkTitle: `Send an email to ${SITE.title}`,
    icon: IconMail,
  },
] as const;

export const SHARE_LINKS: Social[] = [
  {
    name: "WhatsApp",
    href: "https://wa.me/?text=",
    linkTitle: `Share this post via WhatsApp`,
    icon: IconWhatsapp,
  },
  {
    name: "Facebook",
    href: "https://www.facebook.com/sharer.php?u=",
    linkTitle: `Share this post on Facebook`,
    icon: IconFacebook,
  },
  {
    name: "X",
    href: "https://x.com/intent/post?url=",
    linkTitle: `Share this post on X`,
    icon: IconBrandX,
  },
  {
    name: "Telegram",
    href: "https://t.me/share/url?url=",
    linkTitle: `Share this post via Telegram`,
    icon: IconTelegram,
  },
  {
    name: "Pinterest",
    href: "https://pinterest.com/pin/create/button/?url=",
    linkTitle: `Share this post on Pinterest`,
    icon: IconPinterest,
  },
  {
    name: "Mail",
    href: "mailto:?subject=See%20this%20post&body=",
    linkTitle: `Share this post via email`,
    icon: IconMail,
  },
] as const;

// The OSCP vault is a separate repo (Quartz) on its own subdomain, so its
// numbers can't be counted at build time. Bump them when the vault grows.
// The blog that came before this one. Most of it was migrated here; the cert
// reviews and Proving Grounds writeups still only exist there.
export const GITBOOK = "https://kayra.gitbook.io/hackerkayra";

export const OSCP = {
  url: "https://oscp.novaden.dev/",
  notes: 160,
  labs: 68,
  techniques: 59,
  tools: 27,
} as const;

// The "right now" card on the landing page. Three lines, present tense.
// Edit these when the work changes; the date stamp comes from the newest post.
export const NOW = [
  {
    label: "OSCP prep",
    text: `PEN-200 labs, ${OSCP.labs} machines written up so far.`,
  },
  {
    label: "Homelab v2",
    text: "Rebuilding the whole thing as one reviewed repo.",
  },
  {
    label: "Secure code review",
    text: "Turning the OWASP guide into something I can actually work from.",
  },
] as const;

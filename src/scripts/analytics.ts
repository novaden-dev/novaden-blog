// Custom Umami events. The tracker itself is not part of this repo: the
// production nginx injects <script src="/script.js" data-website-id=...> into
// every page and proxies it same-origin. Locally (astro dev) window.umami does
// not exist, so every call below is a no-op.
//
// Events sent:
//   outbound-link  { url, page }      click on a link to another host
//   tag-click      { tag, page }      click on any /tags/<tag>/ link
//   copy-code      { page }           click on a code block's Copy button
//   read-depth     { post, depth }    25 / 50 / 75 / 100 % of a post's or a
//                                     collection note's body scrolled past,
//                                     each sent once per view

type Umami = {
  track: (event: string, data?: Record<string, string | number>) => void;
};

function track(event: string, data: Record<string, string | number>) {
  const umami = (window as unknown as { umami?: Umami }).umami;
  if (!umami) return;
  try {
    umami.track(event, data);
  } catch {
    // Analytics must never break the page.
  }
}

// One delegated listener on document. This module runs once, and the
// document survives ClientRouter page swaps, so the listener covers every
// page and every element added later (the copy buttons are created at runtime).
document.addEventListener(
  "click",
  event => {
    const target = event.target as Element | null;
    if (!target) return;
    const page = location.pathname;

    if (target.closest("button.copy-code")) {
      track("copy-code", { page });
      return;
    }

    const link = target.closest("a[href]") as HTMLAnchorElement | null;
    if (!link) return;
    const url = new URL(link.href, location.href);

    if (url.protocol.startsWith("http") && url.host !== location.host) {
      track("outbound-link", { url: url.href, page });
      return;
    }

    const tag = url.pathname.match(/^\/tags\/([^/]+)\/?$/);
    if (url.host === location.host && tag) {
      track("tag-click", { tag: decodeURIComponent(tag[1]), page });
    }
  },
  { capture: true }
);

// Read depth is measured against the text body, not the whole page, so the
// footer and related-posts block do not count as reading. Posts render into
// #article (PostDetails); collection notes into main.handbook-doc
// (HandbookLayout), whose index pages are excluded by the path check.
const MILESTONES = [25, 50, 75, 100];
let stopReadDepth: (() => void) | null = null;

function startReadDepth() {
  stopReadDepth?.();
  stopReadDepth = null;

  const path = location.pathname;
  const article =
    (path.startsWith("/posts/") && document.getElementById("article")) ||
    (/^\/collections\/[^/]+\/[^/]+\/?$/.test(path) &&
      document.querySelector<HTMLElement>("main.handbook-doc"));
  if (!article) return;

  const post = location.pathname;
  const sent = new Set<number>();
  let scheduled = false;

  const measure = () => {
    scheduled = false;
    const rect = article.getBoundingClientRect();
    if (rect.height <= 0) return;
    // 2px of slack: when the body ends exactly at the page bottom, sub-pixel
    // heights leave the last measurement at 99.99% and 100 never fires.
    const seen = (window.innerHeight + 2 - rect.top) / rect.height;
    const percent = Math.min(100, Math.max(0, seen * 100));
    for (const m of MILESTONES) {
      if (percent >= m && !sent.has(m)) {
        sent.add(m);
        track("read-depth", { post, depth: m });
      }
    }
    if (sent.size === MILESTONES.length) stopReadDepth?.();
  };

  const onScroll = () => {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(measure);
  };

  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", onScroll, { passive: true });
  stopReadDepth = () => {
    window.removeEventListener("scroll", onScroll);
    window.removeEventListener("resize", onScroll);
  };

  // A short post can be fully visible without scrolling. Wait for the
  // deferred tracker to load before the first measurement.
  setTimeout(measure, 1500);
}

document.addEventListener("astro:page-load", startReadDepth);

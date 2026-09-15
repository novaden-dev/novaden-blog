import { FORMATS } from "./formats";

// The tag registry: the only place a tag can come from.
//
// A tag names a subject a post is substantially about, and nothing else. How
// a post is read is its category, its shape is its format, and its place in a
// series is a collection placement. How many posts use a tag plays no part: a
// correct tag on one post is still correct.
//
// Each key is the canonical name. Aliases catch the other spellings that
// source notes arrive with, and the build points at the canonical tag rather
// than accepting them, so two names for one subject never coexist. The domain
// groups subjects (technical, career, life) so that split is never repeated on
// posts. A parent lets a broader tag's page include its descendants later,
// which is why a post never carries both.

export const DOMAINS = ["technical", "career", "life"] as const;

type TagDefinition = {
  domain: (typeof DOMAINS)[number];
  aliases?: string[];
  parent?: string;
};

export const TAGS: Record<string, TagDefinition> = {
  // Infrastructure and homelab.
  docker: { domain: "technical" },
  git: { domain: "technical" },
  gitops: { domain: "technical" },
  kubernetes: { domain: "technical", aliases: ["k3s", "k8s"] },
  linux: { domain: "technical" },
  networking: { domain: "technical" },
  selfhosting: { domain: "technical" },
  ssh: { domain: "technical" },

  // Offensive security. Added for the OSCP migration: subjects only, never the
  // certification (that is the OSCP handbook collection) and never an
  // offensive/defensive lens (that is expressed by which collection a note
  // sits in). `parent: "web"` lets a future web-security page aggregate its
  // descendants; a post still carries only the narrowest tag, never both.
  "active-directory": { domain: "technical", aliases: ["ad"] },
  kerberos: { domain: "technical" },
  windows: { domain: "technical" },
  "privilege-escalation": { domain: "technical", aliases: ["privesc"] },
  enumeration: {
    domain: "technical",
    aliases: ["recon", "reconnaissance", "information-gathering"],
  },
  "lateral-movement": { domain: "technical" },
  persistence: { domain: "technical" },
  credentials: {
    domain: "technical",
    aliases: ["credential-access", "credential-hunting"],
  },
  "password-attacks": {
    domain: "technical",
    aliases: [
      "password-cracking",
      "password-spraying",
      "brute-forcing",
      "brute-force",
    ],
  },
  pivoting: { domain: "technical", aliases: ["tunneling", "port-forwarding"] },
  shells: { domain: "technical", aliases: ["reverse-shells", "reverse-shell"] },
  "file-transfers": { domain: "technical", aliases: ["file-transfer"] },
  "exploit-development": {
    domain: "technical",
    aliases: ["exploit-dev", "public-exploits"],
  },
  encoding: { domain: "technical", aliases: ["encodings", "base64"] },
  databases: { domain: "technical", aliases: ["database"] },

  // Mobile.
  android: { domain: "technical" },

  // Services and protocols worth browsing on their own.
  smb: { domain: "technical" },
  ftp: { domain: "technical" },
  smtp: { domain: "technical" },
  snmp: { domain: "technical" },
  dns: { domain: "technical" },
  rpc: { domain: "technical" },

  // Web application security.
  web: {
    domain: "technical",
    aliases: ["web-security", "webapp", "web-application"],
  },
  "sql-injection": { domain: "technical", aliases: ["sqli"], parent: "web" },
  "command-injection": {
    domain: "technical",
    aliases: ["os-command-injection"],
  },
  "file-upload": { domain: "technical", parent: "web" },
  "file-inclusion": {
    domain: "technical",
    aliases: ["lfi", "rfi"],
    parent: "web",
  },
  "template-injection": {
    domain: "technical",
    aliases: ["ssti"],
    parent: "web",
  },
  "mass-assignment": { domain: "technical", parent: "web" },
  webdav: { domain: "technical", parent: "web" },

  // Certifications and their providers. The reviews are how someone reads a
  // certificate, so the certificate itself is the subject; a provider goes on
  // the post when the review is substantially about them.
  oscp: { domain: "career" },
  ecppt: { domain: "career" },
  ewptx: { domain: "career" },
  ine: { domain: "career" },
  offsec: { domain: "career" },
};

const names = new Set(Object.keys(TAGS));
const formats = new Set<string>(FORMATS);
const aliasOf = new Map<string, string>();

// A broken registry would quietly let bad tags through, so it fails loudly
// instead: an alias that is also a tag, a format word used as a tag, or a
// parent that does not exist.
for (const [name, tag] of Object.entries(TAGS)) {
  if (formats.has(name)) {
    throw new Error(`[tags] "${name}" is a format and cannot be a tag`);
  }
  if (tag.parent && !names.has(tag.parent)) {
    throw new Error(
      `[tags] "${name}" has parent "${tag.parent}", which is not a registered tag`
    );
  }
  for (const alias of tag.aliases ?? []) {
    if (names.has(alias) || formats.has(alias) || aliasOf.has(alias)) {
      throw new Error(
        `[tags] alias "${alias}" of "${name}" is already a tag, a format, or another tag's alias`
      );
    }
    aliasOf.set(alias, name);
  }
}

/**
 * Everything wrong with one post's tags, each message naming the fix. Empty
 * when every tag is canonical.
 */
export function tagProblems(tags: string[]): string[] {
  return tags.flatMap(tag => {
    if (names.has(tag)) return [];
    if (formats.has(tag)) {
      return [
        `"${tag}" is a format, not a tag. Remove it from tags and set \`format: ${tag}\`.`,
      ];
    }
    const canonical = aliasOf.get(tag);
    if (canonical) {
      return [`"${tag}" is an alias. Use the canonical tag "${canonical}".`];
    }
    return [
      `"${tag}" is not a registered tag. Use an existing tag, or add it to src/utils/tags.ts if it is a durable subject.`,
    ];
  });
}

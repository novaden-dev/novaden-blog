---
author: Kayra
pubDatetime: 2026-05-02T00:00:00Z
title: Web Cache Deception
slug: web-cache-deception
featured: false
draft: false
tags: ["security", "web"]
category: notes
description: An overview of Web Cache Deception attacks, detection techniques, and remediation strategies.
---

## Introduction

Web Cache Deception happens when there is a discrepancy between how the web cache and the application handle a request. The attacker targets this discrepancy by tricking a web cache into storing sensitive dynamic content. This is done by persuading a victim to visit a malicious URL, causing the victim's browser to request sensitive content. The cache misinterprets the request and stores the response, allowing the attacker to later request the same URL and retrieve the cached response containing private information.

## How Web Caching Works

A web cache is a system that sits between the origin server and the user. Usually, only static resources are cached. When a user requests a resource, the cache is checked first. If the resource exists there, the user receives it directly without hitting the origin server. If it does not exist, the origin server is queried and the response is sent to the cache before being delivered to the user.

### Cache Rules

Cache rules determine what can be cached and for how long. These rules can be customized as needed. For example, a system might cache:

- Specific directories such as `/assets/` or `/static/`
- Specific extensions such as `.css`, `.js`, or `.ico`
- Specific files such as `robots.txt` or `index.html`

## Detecting Cached Responses

To detect whether a response is served from the cache, examine the response headers:

- **X-Cache**:

| Value | Meaning |
|-------|---------|
| `hit` | The request was served from the cache |
| `miss` | The response came from the origin server |
| `dynamic` | The content is dynamically generated and not suitable for caching |
| `refresh` | The content is outdated and was refreshed from the origin server |

Other headers like `Cache-Control` and `max-age` can also be checked, but these are not always accurate as they may be overwritten by the cache configuration.

Response times can also be compared for the same request. If it is delivered significantly faster, it is likely being served from the cache.

## Performing a Web Cache Deception Attack

### Step 1: Identify a Sensitive Dynamic Endpoint

Find an endpoint that returns dynamic content containing sensitive information (e.g., `/my-profile` with an exposed API key). Review the response to ensure the sensitive data is visible on the rendered page. Focus on **GET** endpoints, as POST, PUT, and other action-based requests are usually not cached.

### Step 2: Find a Parsing Discrepancy

Identify a discrepancy in how the cache and origin server parse the URL path. Differences can exist in:

- How they map URLs to resources
- How they process delimiter characters
- How they normalize paths

### Step 3: Craft the Payload

Construct a malicious URL that exploits the discrepancy to trick the cache into storing a dynamic response. Persuade the victim to visit the URL. Once the victim's browser requests it, the response will be stored in the cache. The attacker then requests the same URL to retrieve the victim's cached response.

> **Testing Tip:** Ensure each test request has a different cache key (e.g., different URL paths or query parameters) so you do not get served cached responses during testing. This process can be automated using extensions like **Param Miner**.

## Types of Discrepancies

### Path Mapping Discrepancies

One clear example of path mapping discrepancies is the difference between traditional URL mapping and REST-style URLs.

- **Traditional URL:** `http://example.com/path/in/filesystem/resource.html`
- **REST-style URL:** `http://example.com/path/resource/param1/param2`

This difference can be exploited. For example:

```text
http://example.com/user/123/profile/test.css
```

The cache server may interpret this as a request for `test.css`, while the origin server (using REST-style routing) treats the additional segment as an ignored parameter, returning `/123/profile`. As a result, the sensitive profile data is cached under the path `/123/profile/test.css`.

**Testing approach:**

1. Find the target URL and append a random path segment.
2. Check if the response still contains the sensitive data. If it does, the origin server ignored the extra segment.
3. Test the cache server to determine how it identifies resources to cache (e.g., does it cache `.js` files?).
4. If so, append `.js` to the random path. The payload is now ready.

Make sure to try different extensions such as `.ico`, `.css`, `.js`, etc.

### Delimiter Discrepancies

Delimiters specify boundaries between different items in a URL. For example, `?` separates the path from the query string. In Java, `;` is used to add parameters. An attacker might use:

```text
/profile;random.css
```

The Spring server interprets this as `/profile`, while the cache server sees `random.css`.

The same technique applies to any character handled inconsistently between the cache and the origin framework.

The null character (`%00`) can also be utilized. Some applications respond with an error, while others ignore everything after the null byte. Some caches process it normally and cache the full path. For example:

```text
/profile%00random.js
```

The origin server may see `/profile`, while the cache server sees `/profile%00random.js`.

**Testing approach:**

1. Find the target resource (e.g., `/my-profile`).
2. Append random text to the end and try different delimiters between the original path and the random string.
3. After identifying which delimiters the origin server accepts, observe how the cache server handles them.

> **Note:** Some delimiter characters may be processed by the victim's browser before the request reaches the cache. Browsers URL-encode characters like `{`, `}`, `<`, and `>`, and use `#` to truncate the path. If the cache or origin server decodes these characters, it may be possible to use an encoded version in an exploit.

### Static Directory Cache Rules

Sometimes caching is configured only for specific directories such as `/static` or `/assets`. Path traversal can be used to exploit this.

**Example:**

```text
/static/..%2fprofile
```

- The origin server decodes the slash characters and resolves `../`, resulting in `/profile`.
- The cache does not resolve dot segments or decode the slashes, treating the path as `/static/..%2fprofile`.

**Testing approach:**

1. Modify the target path (e.g., `/profile`) to `/randomstring/..%2fprofile`.
2. If you receive the profile data, the server decoded and resolved the dot segment.
3. If you receive a 404, the server does not decode or resolve it.

When testing for normalization, start by encoding only the second slash in the dot segment. This is important because some CDNs match the slash following the static directory prefix.

## Chaining Techniques

It may be necessary to chain multiple exploitation techniques to achieve the desired result. For example, combining dot-segment decoding discrepancies with delimiter discrepancies:

```text
/my-account;%2f%2e%2e%2frobots.txt?wcd
```

- `;` is the first delimiter.
- `?` is the second delimiter.
- `%2f%2e%2e%2f` represents the path traversal sequence.

## Remediation

Preventing web cache deception requires addressing discrepancies between how the cache and the origin server interpret requests, and ensuring dynamic content is never stored in caches.

- Always use Cache-Control headers to mark dynamic resources, set with the directives `no-store` and `private`.
- Configure your CDN settings so that your caching rules don't override the Cache-Control header.
- Activate any protection that your CDN has against web cache deception attacks. Many CDNs enable you to set a cache rule that verifies that the response Content-Type matches the request's URL file extension. For example, Cloudflare's Cache Deception Armor.
- Verify that there aren't any discrepancies between how the origin server and the cache interpret URL paths.

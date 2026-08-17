---
author: Kayra
pubDatetime: 2026-08-04T00:00:00Z
title: "HTTP Security Headers: Web, APIs, and Mobile"
slug: http-security-headers
featured: false
draft: false
tags: ["security", "web", "api", "mobile"]
category: notes
description: "Which HTTP security headers matter for browser pages, JSON APIs, and native mobile apps, including why CSP is usually not needed on a JSON-only response."
---

## Introduction

An API returning JSON is still using HTTP. It is not returning HTML.

That distinction answers most questions about security headers. Some headers protect the HTTP
connection or the response itself. Others are instructions for a browser rendering a document.
The second group can be important on a web page and do nothing on the same server's JSON endpoint.

There is no useful rule that says every response must contain the same list of security headers.
The right question is: **which client consumes this response, and what will that client do with
it?**

## Applicability at a Glance

In this table, "mobile" means a native iOS or Android HTTP client. A mobile app built with a
WebView should be treated like a web application for any content rendered inside that WebView.

| Header or control                         | Browser web page                   | JSON API                          | Native mobile client                 |
| ----------------------------------------- | ---------------------------------- | --------------------------------- | ------------------------------------ |
| HTTPS                                     | Required                           | Required                          | Required                             |
| `Strict-Transport-Security`               | Yes                                | Yes for browser clients           | Client-dependent                     |
| `Content-Type`                            | Yes                                | Yes                               | Yes                                  |
| `X-Content-Type-Options`                  | Yes                                | Recommended if browser-accessible | Usually no effect                    |
| `Content-Security-Policy`                 | Yes                                | Usually no                        | Only for WebView content             |
| CSP `frame-ancestors` / `X-Frame-Options` | Yes                                | Usually no                        | Only for WebView content             |
| `Referrer-Policy`                         | Yes                                | Usually no                        | No                                   |
| `Permissions-Policy`                      | When browser features need control | No                                | No                                   |
| CORS headers                              | When calling another origin        | When browser clients call the API | No                                   |
| `Cache-Control`                           | Yes, based on data sensitivity     | Yes, based on data sensitivity    | Useful, but client-dependent         |
| Cookie security attributes                | When cookies are used              | When cookies are used             | When a cookie jar or WebView is used |
| COOP, COEP, and CORP                      | Conditional                        | Usually no                        | No                                   |
| `WWW-Authenticate`                        | When HTTP authentication is used   | Yes for `401` responses           | Yes for `401` responses              |

"No" does not mean that sending the header breaks the response. It means that the header normally
adds no security for that client and should not become a meaningless compliance finding.

## Headers That Protect Browser Documents

These headers exist because a browser can render HTML, run JavaScript, embed documents, navigate
between origins, and expose powerful device features. A command-line client or native HTTP library
does not normally implement those browser behaviors.

### Content-Security-Policy

CSP controls what a browser document may load or execute. A strict policy reduces the impact of
cross-site scripting by restricting scripts, styles, frames, connections, and other resources.

```http
Content-Security-Policy: default-src 'self'; script-src 'self' 'nonce-r4nd0m'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'
```

CSP belongs on HTML pages and on other content that a browser will treat as an active document. It
also belongs on HTML documentation, login pages, OAuth screens, and error pages hosted beside an
API.

### Framing protection

The CSP directive `frame-ancestors` controls which sites may embed a page. It is the modern control
for clickjacking. `X-Frame-Options` is the older alternative.

```http
Content-Security-Policy: frame-ancestors 'none'
X-Frame-Options: DENY
```

A JSON response has no buttons for a victim to click, so framing it does not normally create a
clickjacking risk. Adding these headers to JSON is harmless hardening, but their absence alone is
not a useful finding.

### Referrer-Policy and Permissions-Policy

`Referrer-Policy` controls how much of a page URL the browser sends in the `Referer` header during
later navigation and resource requests.

```http
Referrer-Policy: strict-origin-when-cross-origin
```

`Permissions-Policy` controls browser features such as the camera, microphone, and geolocation for
the page and its frames.

```http
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

Both describe browser document behavior. They do not tell a native mobile app whether it may use
the camera or location. Android and iOS permissions, entitlements, and runtime permission checks
do that.

### Cross-origin isolation headers

`Cross-Origin-Opener-Policy`, `Cross-Origin-Embedder-Policy`, and
`Cross-Origin-Resource-Policy` control how browser documents and resources interact across
origins. They are useful when an application needs cross-origin isolation or wants to restrict
which sites can load a resource. They are not a default requirement for a JSON-only API or a
native mobile client.

## Headers That Still Matter to an API

API responses are not exempt from HTTP controls. They need headers whose behavior matches the API's
data and consumers.

### Correct content type and no sniffing

A JSON endpoint should declare JSON. `nosniff` tells a browser not to reinterpret the response as
another media type.

```http
Content-Type: application/json; charset=utf-8
X-Content-Type-Options: nosniff
```

This pair matters most when an endpoint is reachable from a browser, contains user-controlled
data, or might otherwise be interpreted as active content. Native JSON parsers generally use the
application's code rather than browser MIME sniffing, but a correct `Content-Type` is still part of
the API contract.

### Cache control

Authenticated or sensitive responses should state their caching requirements explicitly.

```http
Cache-Control: no-store
```

Use `no-store` when the response must not be stored. `no-cache` is different: it permits storage
but requires revalidation before reuse. Public, versioned, non-sensitive responses can use caching
deliberately instead of disabling it everywhere.

Browsers and shared HTTP caches understand these directives. Native mobile networking libraries
may also honor them, but an app can copy a response into its own database or file storage anyway.
Server headers do not replace secure client-side storage.

### HSTS and HTTPS

HSTS tells a supporting user agent to use HTTPS for future connections to a host.

```http
Strict-Transport-Security: max-age=31536000; includeSubDomains
```

It is useful for a web origin and for APIs called by browsers. Native mobile behavior depends on
the networking stack, so the app must also enforce HTTPS itself. Android Network Security
Configuration and iOS App Transport Security are client controls. HSTS is not a substitute for
either one.

`includeSubDomains` should be added only when every subdomain is ready for permanent HTTPS. Preload
should be a deliberate operational decision, not a value copied from a scanner recommendation.

### CORS

CORS controls whether JavaScript running on one browser origin may read a response from another
origin. It is a browser read control, not a firewall and not an API authorization mechanism.

This means a request sent with `Origin: https://evil.example` may still receive a normal `200`
response. The server does not have to reject the request. The browser decides whether JavaScript
from that origin may read the response by inspecting the CORS headers.

`curl`, Burp Suite, a native mobile app, and another server do not enforce CORS. They will display
the response even when a browser would hide it from JavaScript. A CORS finding therefore needs to
be proven in a browser or evaluated using the browser's exact rules.

### No Access-Control-Allow-Origin header

Suppose the request contains an untrusted origin:

```http
Origin: https://evil.example
```

The API processes it and returns JSON, but sends no `Access-Control-Allow-Origin` header:

```http
HTTP/1.1 200 OK
Content-Type: application/json

{"account":"kayra"}
```

This is normally safe from a CORS perspective. An attacker's page may be able to send the request,
but the browser will not expose the response body to that page's JavaScript. Seeing the body in
Burp does not change that.

The fact that the request was sent can still matter. Browsers send some cross-origin requests,
known as simple requests, without a preflight. If a request changes state, CORS does not prevent
cross-site request forgery. Cookie attributes, CSRF tokens, and server-side request validation
handle that separate problem.

### Wildcard origin

This response allows JavaScript on any origin to read it when the request is not credentialed:

```http
Access-Control-Allow-Origin: *
```

This is valid for a deliberately public API, public metadata, fonts, and other resources intended
for everyone. It is wrong when the response contains data that arbitrary websites should not be
able to read.

The wildcard cannot authorize a credentialed browser read. If JavaScript uses
`credentials: "include"`, the browser requires both an explicit allowed origin and
`Access-Control-Allow-Credentials: true`. This combination is invalid and the browser blocks the
response:

```http
Access-Control-Allow-Origin: *
Access-Control-Allow-Credentials: true
```

That invalid pair is often a configuration bug, but it does not by itself let the attacker's page
read a cookie-authenticated response. The browser rejects it because `*` cannot be used for a
credentialed CORS request.

### Explicit and reflected origins

An API with one trusted web frontend can return that exact origin:

```http
Access-Control-Allow-Origin: https://app.example.com
Vary: Origin
```

When several frontends are trusted, the server can compare the request's `Origin` against an
allowlist and return the matching value. It must not copy every supplied origin without checking
it. This is vulnerable when cookies or other ambient credentials can accompany the request:

```http
Origin: https://evil.example

Access-Control-Allow-Origin: https://evil.example
Access-Control-Allow-Credentials: true
```

Here the browser is explicitly told that the attacker's page may read the credentialed response.
That is the classic exploitable CORS misconfiguration.

Origin validation must compare parsed, complete origins. Substring or suffix checks can
accidentally trust values such as `https://app.example.com.evil.example`. Trusting the special
`null` origin is also dangerous unless the application has a narrow, understood reason for it.

### What Vary: Origin means

`Vary: Origin` is a cache instruction. It says that the response may change according to the
request's `Origin`, so a cache must not reuse a response created for one origin as though it were
created for another.

It is needed when the server dynamically returns one explicit origin from an allowlist:

```http
Access-Control-Allow-Origin: https://app.example.com
Vary: Origin
```

With a constant `Access-Control-Allow-Origin: *`, the response does not vary by origin, so
`Vary: Origin` is unnecessary. Sending both is redundant, not an exploitable vulnerability.
`Vary: Origin` also does not make a wildcard safer and does not prove that an allowlist exists.

### Preflight requests

For methods or headers outside the simple-request rules, the browser first sends an `OPTIONS`
request:

```http
OPTIONS /api/users/42 HTTP/1.1
Origin: https://app.example.com
Access-Control-Request-Method: PUT
Access-Control-Request-Headers: authorization, content-type
```

The API can allow the origin, method, and headers in the preflight response:

```http
HTTP/1.1 204 No Content
Access-Control-Allow-Origin: https://app.example.com
Access-Control-Allow-Methods: PUT
Access-Control-Allow-Headers: Authorization, Content-Type
Vary: Origin
```

Passing a preflight only allows the browser to send the real request. The real response must also
contain a valid `Access-Control-Allow-Origin` value before JavaScript can read it. Conversely, a
failed preflight is not an authorization control because a non-browser client can send the real
request directly.

### Judging common results

| Observed response to `Origin: https://evil.example` | Browser result                             | Assessment                                          |
| --------------------------------------------------- | ------------------------------------------ | --------------------------------------------------- |
| No ACAO header                                      | Response hidden from attacker's JavaScript | Normally safe from cross-origin reading             |
| `ACAO: *`, no credentials                           | Any origin can read it                     | Fine only for intentionally public responses        |
| `ACAO: *` plus `ACAC: true`                         | Credentialed response is blocked           | Invalid configuration, but not directly exploitable |
| `ACAO: https://evil.example`, no credentials        | Attacker can read the response             | A problem if the response is not public             |
| `ACAO: https://evil.example` plus `ACAC: true`      | Attacker can read a credentialed response  | Usually exploitable and serious                     |
| Trusted origin plus `Vary: Origin`                  | Only that allowed origin can read          | Correct when backed by an exact allowlist           |

`ACAO` means `Access-Control-Allow-Origin`. `ACAC` means
`Access-Control-Allow-Credentials`.

The two observations in the original example cannot describe the same final response: it either
has no ACAO header or it has `Access-Control-Allow-Origin: *`. If the behavior changes between
requests, compare the exact URL, method, request headers, response status, redirects, preflight,
and final response. Middleware often adds CORS headers only to certain routes or status codes.

CORS matters on an API when a browser frontend calls it. A native mobile app, server-to-server
client, or command-line tool is not stopped by CORS. An attacker can also call the API directly,
so authentication and authorization must never depend on the `Origin` header.

A public API may intentionally use `Access-Control-Allow-Origin: *`. An authenticated API should
allow only the origins that need browser access, especially when cookies or other browser-managed
credentials are involved.

### Cookies and authentication challenges

If an API authenticates with cookies, the normal cookie attributes still apply:

```http
Set-Cookie: session=abc123; Secure; HttpOnly; SameSite=Lax; Path=/
```

They also matter to a mobile WebView or native cookie jar. They do not apply to a bearer token that
the native app stores and adds to an `Authorization` header itself.

For HTTP authentication schemes, a `401 Unauthorized` response should include the challenge that
the client needs:

```http
WWW-Authenticate: Bearer realm="api", error="invalid_token"
```

## CSP on JSON Responses

A full CSP is usually unnecessary on an endpoint that always returns correctly typed JSON and is
never rendered as a browser document. CSP is enforced by a browser against the resource that
carries the policy. It does not travel through a `fetch()` call and protect the frontend page that
consumes the JSON.

For example, adding this to `/api/users/42` does not set the policy for `https://app.example.com`:

```http
Content-Security-Policy: default-src 'none'
```

The frontend's HTML response needs its own CSP. For the API response, the more relevant controls
are usually:

- `Content-Type: application/json; charset=utf-8`
- `X-Content-Type-Options: nosniff`
- suitable `Cache-Control`
- HSTS at the HTTPS host level for supporting clients
- a narrowly configured CORS policy if browsers consume the API
- correct authentication and authorization

CSP becomes relevant when the "API" also returns HTML, including Swagger UI, GraphQL explorers,
login or consent pages, file previews, debug pages, and framework-generated error responses. Apply
the right policy to those HTML responses. Another valid defense-in-depth choice is
`Content-Security-Policy: default-src 'none'; frame-ancestors 'none'` on JSON responses, but its
absence should not be reported as if it exposed the API to XSS.

> **Testing Tip:** Change the method, path, `Accept` header, and error conditions. A normal request
> may return JSON while a `404`, `500`, authentication redirect, or documentation route returns
> HTML. Judge headers per response type, not only per hostname.

## Mobile Is Two Different Cases

A native mobile app and a WebView have different security models.

- **Native HTTP client**: HTTPS, certificate validation, API authentication, authorization, cache
  behavior, and secure local storage matter. Browser document headers are usually ignored.
- **WebView**: CSP, framing rules, CORS, cookie attributes, referrer policy, and other browser
  controls may apply to the content rendered in the WebView. The app must also configure the
  WebView safely.
- **API shared by web and mobile**: configure headers for the strictest real consumer. CORS may be
  required for the web client even though the mobile client ignores it. Correct MIME types and
  caching rules benefit both.

The server cannot force a native app to store tokens safely, reject screenshots, disable backups,
or validate certificates correctly through response headers. Those are mobile application
controls.

## Testing Without Checklist Findings

When a scanner reports missing headers, test the response in context:

1. Identify the response media type and verify it matches the body.
2. Identify every real consumer: browser page, browser JavaScript, WebView, native app, another
   server, or all of them.
3. Decide what behavior the missing header would change in that consumer.
4. Prove a security impact or record the item as hardening, not as a vulnerability.
5. Check HTML pages and JSON endpoints separately, including redirects and error responses.

A missing CSP on a JSON response is not equivalent to a missing CSP on an authenticated HTML
application. Likewise, permissive CORS does not affect a mobile-only client, but it becomes
important the moment a browser can send credentials and read sensitive responses.

## Remediation

Apply headers by response behavior and client type instead of copying one header bundle onto every
route.

- Serve every web page and API endpoint over HTTPS, and use HSTS where the clients and domain
  design support it.
- Send an accurate `Content-Type` on every response and add
  `X-Content-Type-Options: nosniff` to browser-reachable content.
- Put a tested CSP on every HTML document, including documentation, authentication, and error
  pages. Do not treat full CSP as mandatory on pure JSON responses.
- Protect interactive HTML from framing with CSP `frame-ancestors`, with `X-Frame-Options` only
  where legacy coverage is required.
- Set explicit caching rules. Use `Cache-Control: no-store` for responses that must not be stored.
- Configure CORS only for browser origins that need to read the API. Never use CORS as
  authentication or authorization.
- Add `Secure`, `HttpOnly`, and an appropriate `SameSite` value to security-sensitive cookies.
- Enforce mobile transport, certificate, permission, WebView, and local-storage controls in the
  mobile application because browser response headers cannot provide them.

> **References:** [OWASP HTTP Headers Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Headers_Cheat_Sheet.html), [OWASP REST Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html), and [MDN Content Security Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CSP).

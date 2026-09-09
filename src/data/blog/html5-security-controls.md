---
author: Kayra
pubDatetime: 2026-06-14T00:00:00Z
title: HTML5 Security Controls
slug: html5-security-controls
featured: false
draft: false
tags: ["security", "web"]
category: notes
description: What "implement HTML5 security controls" actually means, covering Web Storage, CORS, postMessage, sandboxed iframes, WebSockets, and CSP, with how to test each.
---

## Introduction

"HTML5" is not a single feature. It is an umbrella for a set of browser capabilities and JavaScript APIs that turned the browser from a document viewer into an application platform: client-side storage, cross-origin requests, cross-window messaging, raw sockets, and more. Each of these added real attack surface. So when a security checklist says "ensure the application implements HTML5 security controls," it is shorthand for a category, not one switch. It means: for every modern browser feature the app uses, confirm it is configured so it cannot be abused.

This post walks through the features that show up most often in a client-side review (OWASP WSTG-CLNT and the HTML5 Security Cheat Sheet), what can go wrong with each, and how to test it. A blanket "yes, controls are implemented" is not meaningful unless you enumerate which features the app actually uses and check each one.

## Web Storage

`localStorage` and `sessionStorage` give a page a key/value store on the client. `localStorage` persists until explicitly cleared; `sessionStorage` lasts for the tab's lifetime. Both are plaintext and readable by any JavaScript running on the origin. There is no `HttpOnly` equivalent and no built-in expiry.

That last point is the whole risk. A cookie can be marked `HttpOnly` so that script cannot read it, which contains the damage from a cross-site scripting (XSS) bug. Anything in Web Storage has no such protection: a single XSS means every token and every piece of data in storage is readable by the attacker's injected script.

```javascript
// Risky: a stolen session now lives somewhere script can read
localStorage.setItem("jwt", token);
```

Session identifiers, JWTs, API keys, and personal data belong in a cookie with `HttpOnly`, `Secure`, and `SameSite` set, not in Web Storage.

> **Testing Tip:** Open DevTools, go to Application, then Storage, and read what is there. Then grep the client source for `localStorage` and `sessionStorage` and judge whether anything sensitive is being written.

## Cross-Origin Resource Sharing (CORS)

The Same-Origin Policy stops a page on one origin from reading responses from another. CORS is the controlled exception: a server opts in to cross-origin reads by returning `Access-Control-Allow-Origin` (ACAO) and related headers. Misconfigure it and an attacker-controlled site can read authenticated responses from the target.

The two configurations to flag:

| Configuration | Why it is dangerous |
|---|---|
| `Access-Control-Allow-Origin: *` on authenticated endpoints | Any origin can read the response |
| Reflecting the request's `Origin` header back in ACAO | Effectively a wildcard that also passes credential checks |
| ACAO reflected or `*` combined with `Access-Control-Allow-Credentials: true` | The worst case: any site can make credentialed reads |

The combination of a reflected or wildcard origin with `Access-Control-Allow-Credentials: true` is the high-severity case, because it lets a malicious site issue requests with the victim's cookies and read the results.

> **Testing Tip:** Replay a request with a forged `Origin` header and inspect the response. If the server echoes your origin back in `Access-Control-Allow-Origin`, especially alongside `Access-Control-Allow-Credentials: true`, you have a finding.

```bash
curl -s -I -H "Origin: https://evil.example.com" https://target.example.com/api/account
```

## Cross-Document Messaging (postMessage)

The Same-Origin Policy also stops two windows on different origins from talking to each other, even when one is an iframe inside the other. `postMessage` is the sanctioned channel through that wall: one `window` sends data to another across origins.

```javascript
// Sender: name the exact origin allowed to receive this
iframe.contentWindow.postMessage({ type: "setTheme", value: "dark" }, "https://widget.example.com");

// Receiver
window.addEventListener("message", (event) => {
  // event.origin is who sent it, event.data is the payload
});
```

Two bug classes account for most postMessage findings.

### Receiver does not validate the sender

If a `message` handler acts on `event.data` without checking `event.origin`, any website can open or embed the app and send it messages. When the handler trusts that data, the attacker controls it. Passing it into a sink like `innerHTML` or `eval` turns this into DOM-based XSS.

```javascript
// Vulnerable: no origin check, and data flows into a dangerous sink
window.addEventListener("message", (event) => {
  document.getElementById("output").innerHTML = event.data;
});
```

The fix is to check the origin against an allowlist and still treat the data as untrusted input:

```javascript
window.addEventListener("message", (event) => {
  if (event.origin !== "https://trusted.example.com") return;
  // validate event.data before using it
});
```

### Sender uses a wildcard target origin

Passing `"*"` as the target origin tells the browser to deliver the message to whatever origin currently occupies that window. If the destination window was navigated to an attacker's page, the data is handed to the attacker.

```javascript
// Vulnerable: secret delivered to whoever holds that window
otherWindow.postMessage(secretToken, "*");
```

Always name the exact destination origin instead of `"*"`.

> **Testing Tip:** Grep the client source for `addEventListener('message'` and `.postMessage(`. For every receiver, confirm there is an `event.origin` allowlist check and that the data is validated. For every sender, confirm the target origin is a real origin and not `"*"`. Burp Suite's DOM Invader automates finding both.

## Sandboxed iframes

A normal iframe runs embedded content with most of its native abilities: it can run scripts, submit forms, open popups, and navigate the top window. When you embed untrusted or third-party content, that is too much trust. The `sandbox` attribute strips the frame down to a minimal-privilege state, and you re-grant only what is needed.

```html
<!-- Maximum lockdown: no scripts, no forms, treated as a unique null origin -->
<iframe src="https://untrusted.example.com" sandbox></iframe>

<!-- Selectively re-enable specific capabilities -->
<iframe src="..." sandbox="allow-scripts allow-forms"></iframe>
```

The classic finding is one specific combination:

```html
<iframe sandbox="allow-scripts allow-same-origin" src="https://untrusted.example.com"></iframe>
```

`allow-same-origin` keeps the frame in its real origin and `allow-scripts` lets it run JavaScript. Together, the framed content can reach into its own DOM and remove the `sandbox` attribute from itself, escaping the sandbox entirely. Granting both at once usually defeats the purpose.

> **Testing Tip:** Grep for `<iframe` and note which frames load untrusted or third-party content. Flag any that have no `sandbox` attribute, and any that pair `allow-scripts` with `allow-same-origin`.

## WebSockets

WebSockets give a page a persistent, two-way connection to a server. Three things matter for security.

The first is transport. The scheme tells you whether traffic is encrypted, exactly like HTTP: `ws://` is plaintext and `wss://` is TLS. Plaintext WebSockets are a finding on their own.

The second is origin validation. WebSockets are not covered by the Same-Origin Policy or by CORS, so the browser will let any page open a connection to the server. The server must validate the `Origin` header itself. If it does not, an attacker's page can open an authenticated socket on the victim's behalf, a flaw known as Cross-Site WebSocket Hijacking.

The third is authentication. Confirm that messages require a valid session or token, not merely an open socket.

> **Testing Tip:** Open DevTools, go to the Network tab, and filter by WS. Use the app so a socket opens, then read the connection URL. If it starts with `ws://`, the channel is unencrypted. You can also grep the source:

```bash
grep -rniE "new WebSocket\(|wss?://" ./src
```

## Content Security Policy (CSP)

CSP is the browser-level mitigation that limits where scripts, styles, and other resources may load from. Its main job in this category is to act as a second line of defense against XSS: even if an attacker injects markup, a strict policy stops injected scripts from executing.

In practice, most CSPs you will test contain `'unsafe-inline'` and `'unsafe-eval'` in `script-src`. This is common because a strict policy is genuinely hard to retrofit. `'unsafe-inline'` re-allows inline `<script>` blocks and `onclick`-style handlers that legacy code, analytics snippets, and tag managers depend on. `'unsafe-eval'` re-allows `eval`, `new Function`, and string-based `setTimeout` that some libraries need. Teams add them to make the app work, which quietly removes most of CSP's value.

So is it still worth reporting? Yes, but calibrate the severity rather than flagging the keyword:

- `'unsafe-inline'` in `script-src` re-allows exactly the injected inline scripts CSP is meant to block, so the policy provides almost no XSS protection. This is the more serious of the two.
- `'unsafe-eval'` is lower severity. It only matters once an attacker can reach an `eval`-like sink; it is not an injection vector by itself.
- Impact is conditional. On its own, a weak CSP grants an attacker nothing, so report it as a defense-in-depth or hardening finding, typically Low and sometimes Medium. If you also found an actual XSS, the weak CSP becomes an aggravating factor because it failed to contain it, and the combined story is more serious.
- Context sets the level. A weak CSP on a static page with no user input is barely a Low; the same policy on an authenticated app handling sensitive data is a meaningful Medium.

The modern fix is a nonce-based (or hash-based) policy, which lets you drop `'unsafe-inline'` entirely. The server generates a fresh random nonce per response, and only scripts carrying that nonce execute.

```html
<!-- Server emits a fresh nonce per response: script-src 'nonce-r4nd0m123' -->
<script nonce="r4nd0m123">/* runs */</script>
<script>/* injected by an attacker, no nonce, blocked */</script>
```

An attacker injecting markup cannot guess the nonce, so injected scripts are blocked even though inline scripts are technically permitted.

## Other Features Worth Checking

A few smaller items round out a client-side review:

- **Reverse tabnabbing:** a link with `target="_blank"` gives the opened page a reference to the opener via `window.opener`, which it can use to navigate the original tab to a phishing page. Add `rel="noopener noreferrer"`. Most modern browsers default to this, but do not rely on it.
- **Powerful permission APIs:** geolocation, camera, microphone, and notifications should only be requested when actually needed and only over HTTPS.
- **Deprecated AppCache:** the old Application Cache is removed from browsers. If it is still present, it is a finding. Offline behavior should use a correctly scoped Service Worker served over HTTPS.
- **Client-side validation is not a control:** HTML5 form attributes like `required` and `type="email"` improve the user experience but are trivially bypassed. Server-side validation must still exist.

## Remediation

Securing HTML5 features comes down to using each one with least privilege and never trusting data that crossed an origin boundary. For every modern browser feature the application uses:

- Keep session tokens, JWTs, API keys, and personal data out of `localStorage` and `sessionStorage`. Use cookies with `HttpOnly`, `Secure`, and `SameSite`.
- Restrict `Access-Control-Allow-Origin` to a specific allowlist of trusted origins. Never use `*` or reflect the `Origin` header on authenticated endpoints, and never combine either with `Access-Control-Allow-Credentials: true`.
- In every `postMessage` receiver, validate `event.origin` against an allowlist and still treat `event.data` as untrusted input. In every sender, specify the exact target origin instead of `"*"`.
- Sandbox iframes that load untrusted content and grant only the capabilities required. Do not combine `allow-scripts` with `allow-same-origin`.
- Use `wss://` for all WebSocket connections, validate the `Origin` header server-side, and authenticate every message rather than trusting an open socket.
- Deploy a strict, nonce-based or hash-based CSP and remove `'unsafe-inline'` and `'unsafe-eval'` from `script-src`.
- Add `rel="noopener noreferrer"` to links using `target="_blank"`, request powerful permission APIs only when needed and over HTTPS, and always validate input server-side regardless of client-side checks.

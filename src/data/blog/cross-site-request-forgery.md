---
author: Kayra
pubDatetime: 2026-06-13T00:00:00Z
title: Cross-Site Request Forgery (CSRF)
slug: cross-site-request-forgery
featured: false
draft: true
tags: ["security", "web"]
category: notes
description: How CSRF works, why anti-CSRF tokens and the SameSite attribute stop it, how tokens actually reach the frontend, and how to test for it.
---

## Introduction

Cross-Site Request Forgery (CSRF) tricks a logged-in user's browser into sending a state-changing request to an application the user is authenticated to, without the user's intent. The attacker never sees the response or steals the session; they simply ride on the user's existing authentication to make the application perform an action.

The whole attack rests on one browser behavior: when the browser sends a request to a site, it **automatically attaches that site's cookies** — including the session cookie — regardless of which page triggered the request. This is called *ambient authority*, and it is what CSRF abuses.

## How CSRF Works

Consider a banking app with an endpoint that changes the account email:

```text
POST /change-email
Content-Type: application/x-www-form-urlencoded

email=new@bank.com
```

The only thing the server uses to decide *who* is making this request is the session cookie. Now an attacker hosts a page on an unrelated site:

```html
<form id="x" method="POST" action="https://bank.com/change-email">
  <input name="email" value="attacker@evil.com">
</form>
<script>document.getElementById('x').submit();</script>
```

When a victim who is logged into the bank visits this page, the form auto-submits to `bank.com`. The browser attaches the victim's bank session cookie, the server sees a valid session, and the email is changed to one the attacker controls — a foothold for an account takeover.

## Why This Works

The request is *forged* but indistinguishable from a real one, because:

- The browser sends the session cookie automatically (ambient authority).
- The server authenticates on the cookie alone and has no way to tell that the request originated from a different site.

CSRF is therefore only relevant when the application relies on an **automatically-sent credential** — a cookie. APIs that authenticate with an `Authorization: Bearer <token>` header are generally not exposed, because the browser does **not** automatically attach that header to a cross-site request; the attacker's page cannot read or set it.

## The Anti-CSRF Token

The standard defense is a secret the attacker cannot know: a random, unpredictable **anti-CSRF token** that must accompany every state-changing request. The flow confuses people, so here it is step by step. The key point: **the backend generates and validates the token; the frontend only relays it.** The frontend never invents it.

1. The **backend generates** a random token and **remembers the expected value** (in the server-side session, or cryptographically bound to a cookie).
2. The **backend hands the token to the frontend.**
3. The **frontend includes the token** in the next state-changing request.
4. The **backend compares** the submitted token against the expected value. Match → allow. Missing or wrong → reject.

It works because the Same-Origin Policy stops the attacker's page from **reading** the victim's token, so a forged cross-site request cannot include a valid one.

### How the token reaches the frontend

This depends on the architecture, which is the part that trips people up.

| Architecture | How the token is delivered | How it is sent back |
|---|---|---|
| Server-rendered (MVC, Django, Rails) | Backend renders it into a hidden form field | In the form body |
| SPA + API (React/Angular/Vue) | Backend sets it in a readable cookie, or serves it from an endpoint | The JS reads it and adds it as a header (e.g. `X-XSRF-TOKEN`) |

In both cases the **backend originates** the token; the SPA simply reads what the backend provided and echoes it back in a header.

### Synchronizer token vs. double-submit cookie

- **Synchronizer token**: the server stores the expected token in the session and compares the submitted value against it. Stateful.
- **Double-submit cookie**: the server sets the token in a cookie; client-side JS copies it into a request header; the server checks that the cookie value and the header value match. No server-side storage is needed. It is safe because an attacker's cross-site script cannot read the victim's cookie to copy it into the header.

## The SameSite Cookie Attribute

A second, browser-enforced defense is the `SameSite` attribute on the session cookie. It controls whether the cookie is sent on cross-site requests:

| Value | Behavior |
|---|---|
| `Strict` | Never sent on any cross-site request, even when following a link from another site. Strongest, but a user arriving from an external link appears logged out. |
| `Lax` | Sent on safe top-level navigations (e.g. clicking a link), but **not** on cross-site POST, form, AJAX, or iframe requests. This blocks the typical CSRF vector while preserving normal navigation. It is the modern browser default. |
| `None` | Sent on all cross-site requests. Requires the `Secure` flag. Offers no CSRF protection on its own. |

`SameSite=Lax` and the anti-CSRF token are **independent** defenses: one lives on the cookie and is enforced by the browser, the other is an application-level secret. Robust applications use both, and disabling SameSite (setting it to `None`) to "allow cross-origin requests" removes a layer of protection that should instead be handled with a proper CORS policy and bearer-token authentication.

## A Note on State-Changing GET Requests

`SameSite=Lax` still allows cookies on top-level GET navigations. If an application performs a state change via a GET request — for example `GET /transfer?to=x&amount=100` — an attacker can trigger it with a simple top-level navigation or auto-submitting GET form, and Lax will **not** stop it. State-changing actions must always use POST/PUT/DELETE, never GET.

## Testing for CSRF

1. Identify **state-changing** requests (change email/password, transfer funds, change roles).
2. Check whether the request carries a **unique, unpredictable anti-CSRF token**. Remove it or alter it and resend — if the request still succeeds, the token is not validated.
3. Inspect the session cookie's **`SameSite`** attribute in `Set-Cookie` (or the browser dev tools cookie panel).
4. In Burp Suite, right-click the request → **Engagement tools → Generate CSRF PoC**. This builds an HTML page that auto-submits the same request cross-site. Host it, open it while authenticated as the victim, and confirm whether the action executes.
5. Also try a different user's token, an empty token, and an omitted token to probe weak validation.

If a state-changing request executes from the generated PoC with no valid token required, the endpoint is vulnerable.

## Remediation

- Validate a synchronizer or double-submit anti-CSRF token on **every** state-changing request.
- Set session cookies to `SameSite=Lax` (or `Strict`) with the `Secure` flag.
- Never perform state changes via GET.
- For cross-origin APIs, use an explicit CORS allow-list and bearer-token authentication rather than disabling CSRF defenses.
- Re-authenticate or require step-up verification for the most sensitive actions.

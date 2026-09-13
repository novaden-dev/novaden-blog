---
author: Kayra
pubDatetime: 2026-08-04T00:00:00Z
title: "HTTP Request Smuggling"
slug: http-request-smuggling
featured: false
draft: true
tags: ["security", "web"]
category: notes
description: "Why front end and back end disagree about where a request ends, the desync classes (CL.TE, TE.CL, TE.TE, H2.CL, H2.TE, CL.0), how to drive Burp's HTTP Request Smuggler extension, and what to actually check on an API."
---

## Introduction

HTTP request smuggling is a parsing disagreement, not an injection bug. Two servers sit in a chain, a front end (CDN, load balancer, API gateway, reverse proxy) and a back end, and they read the same bytes as a different number of requests. When the front end thinks it forwarded one request and the back end thinks it received one and a half, the leftover half sits in the back end's buffer waiting to be glued onto whatever arrives next on that connection. That next thing is usually another user's request.

That is the whole vulnerability. Everything else (the header tricks, the timing probes, the HTTP/2 variants) is just different ways of producing the disagreement.

Two preconditions have to hold, and if either is missing you can stop testing:

- **There is a front end and a back end.** A single server talking to itself cannot disagree with itself. No intermediary means no smuggling.
- **The back-end connection is reused.** Front ends pool connections to the back end for performance, so requests from many different users travel down the same TCP connection one after another. That reuse is what turns your leftover bytes into someone else's problem. If the front end opens a fresh connection per request, the leftover is discarded harmlessly.

APIs meet both conditions almost by default, which is why this is worth a pass on an API test even though the finding rate is low. An API sits behind a gateway, and the gateway is usually where authentication, rate limiting and routing are enforced. A smuggled request skips that layer entirely.

## Why HTTP/1.1 Allows the Disagreement

On a keep-alive connection, requests arrive as one continuous byte stream. The receiver has to work out where each request ends, and HTTP/1.1 gives it two different ways to do that.

**Content-Length**: the body is exactly this many bytes.

```http
POST /api/search HTTP/1.1
Host: api.target.com
Content-Type: application/json
Content-Length: 26

{"query":"smuggling test"}
```

**Transfer-Encoding: chunked**: the body arrives as a series of chunks. Each chunk is preceded by its own length in hex on its own line, and a chunk of length zero ends the body.

```http
POST /api/search HTTP/1.1
Host: api.target.com
Content-Type: application/json
Transfer-Encoding: chunked

1a
{"query":"smuggling test"}
0

```

The `1a` is hex for 26, the length of the chunk that follows. The `0` plus a blank line is the terminator. Miss the terminator and the server keeps waiting for more body.

The spec is clear that if both headers are present, `Transfer-Encoding` wins and `Content-Length` is ignored. In practice, servers disagree: some prefer `Content-Length`, some choke on a slightly malformed `Transfer-Encoding` and silently fall back, some reject the request. Put a server that prefers one in front of a server that prefers the other and you have a desync.

> **Note:** the ambiguity is a property of HTTP/1.1 only. HTTP/2 carries an explicit length in its frame layer, so there is nothing to disagree about. The modern variants exist because front ends still translate HTTP/2 down to HTTP/1.1 before talking to the back end, and reintroduce the ambiguity while doing it.

## The Desync Classes

Naming convention: the first term is what the **front end** uses to measure the body, the second is what the **back end** uses. `CL.TE` means the front end honours `Content-Length` and the back end honours `Transfer-Encoding`.

| Class | Front end uses | Back end uses | Where you still find it |
|---|---|---|---|
| `CL.TE` | Content-Length | Transfer-Encoding | Older stacks, custom proxies |
| `TE.CL` | Transfer-Encoding | Content-Length | Older stacks |
| `TE.TE` | Transfer-Encoding | Transfer-Encoding, but one side can be tricked into ignoring it | Anywhere header parsing is sloppy |
| `H2.CL` | HTTP/2 frame length | Content-Length copied from the h2 request | Very common precondition today |
| `H2.TE` | HTTP/2 frame length | Transfer-Encoding copied from the h2 request | Same |
| `CL.0` | Content-Length | Nothing, the body is ignored entirely | Static paths, redirects, error handlers |

### CL.TE

The front end reads `Content-Length: 6` and forwards exactly six body bytes (`0`, CR, LF, CR, LF, `X`). The back end reads `Transfer-Encoding`, sees the zero-length chunk, and decides the body ended after five bytes. The `X` is left over.

```http
POST /api/status HTTP/1.1
Host: api.target.com
Content-Length: 6
Transfer-Encoding: chunked

0

X
```

Whatever request comes down that connection next gets `X` bolted onto its front, so the back end sees `XPOST /api/... HTTP/1.1` and the victim gets an error. Replace `X` with a well-formed request prefix instead of a single letter and you control what that user's request becomes.

### TE.CL

The mirror image. The front end honours the chunked encoding and forwards the whole thing. The back end reads `Content-Length: 4` and stops after four bytes, leaving the rest of the chunk data in the buffer as the start of the next request.

```http
POST /api/status HTTP/1.1
Host: api.target.com
Content-Length: 4
Transfer-Encoding: chunked

5c
GPOST /admin HTTP/1.1
Host: api.target.com
Content-Length: 15

x=1
0

```

### TE.TE

Both servers support chunked encoding, so you cannot split them with the header as-is. Instead you obfuscate the header so that exactly one of them stops recognising it and falls back to `Content-Length`. Which one falls back determines whether you end up with a CL.TE or a TE.CL.

```http
Transfer-Encoding: xchunked
Transfer-Encoding : chunked
Transfer-Encoding: chunked
Transfer-Encoding: x
Transfer-Encoding:[tab]chunked
[space]Transfer-Encoding: chunked
X: X[\n]Transfer-Encoding: chunked
Transfer-Encoding
 : chunked
```

This is exactly the kind of permutation you do not want to grind through by hand, and it is the main thing the extension automates.

### H2.CL and H2.TE

These are the ones that matter now. The front end accepts HTTP/2 from you, then rewrites the request as HTTP/1.1 for the back end. Doing that correctly means recomputing the body length from the actual data received. Doing it lazily means copying a `content-length` or `transfer-encoding` header that you supplied inside the HTTP/2 request straight into the rewritten HTTP/1.1 request.

HTTP/2 will happily carry a `content-length` header that disagrees with the real frame length, because the frame length is authoritative at that layer. The front end validates against the frame, everything looks fine, and then it hands the back end an HTTP/1.1 request whose `Content-Length` is a lie.

There is a second, nastier HTTP/2 trick. HTTP/2 header values are binary strings, so a CR or LF inside a value is legal at the HTTP/2 layer. If the front end writes that value into an HTTP/1.1 request without escaping it, you have injected a line break into the HTTP/1.1 message and can append arbitrary headers, or an entire second request, from inside one header value. The same applies to the `:path` and `:method` pseudo-headers.

> **Testing Tip:** always test the same endpoint over both protocols. Burp defaults to HTTP/2 where the server supports it, and an HTTP/1.1-only test will miss the entire H2 family. Enable **Settings, Network, HTTP, "Allow HTTP/2 ALPN override"** so you can force the protocol per request from the Inspector.

### CL.0 and client-side desync

Some endpoints ignore request bodies completely: static files, redirects, some error handlers, endpoints that only read the query string. If the back end ignores your body but the front end forwarded it as body bytes, the back end treats those bytes as the start of the next request. That is `CL.0`, the front end counted a body and the back end counted zero.

This class matters because it does not need a hop-by-hop header trick at all, just a normal request with a normal `Content-Length`. That means a *browser* can be made to send it, which is the basis of client-side desync: the victim's own browser poisons its own connection to the site, and no shared back-end connection is required. Recent research has extended the family further (0.CL, and variants driven by `Expect: 100-continue` handling), and current versions of the extension probe for them.

## Detection: What a Result Actually Means

### Timing probes

The classic technique, and the one to understand before you trust any tool output. You deliberately construct a request that leaves one of the two servers waiting for bytes that will never arrive, and you measure the delay.

CL.TE probe. The front end forwards only four bytes (`1`, CR, LF, `A`), the back end reads chunked, receives a chunk announcing more data, and waits for a terminator that the front end never sends:

```http
POST /api/status HTTP/1.1
Host: api.target.com
Transfer-Encoding: chunked
Content-Length: 4

1
A
0
```

TE.CL probe. The front end honours the terminating zero chunk and forwards five bytes, the back end wants six and waits for the last one:

```http
POST /api/status HTTP/1.1
Host: api.target.com
Transfer-Encoding: chunked
Content-Length: 6

0

X
```

A hang on the first and not the second points at CL.TE, and the reverse points at TE.CL.

> **Danger:** timing probes work by making a back-end connection sit and wait. Every probe holds a connection open in the pool. Run enough of them against a production API and you are running a small denial of service, not a test. This is the single most important reason to prefer the extension's differential techniques and to keep the timeout options conservative.

### Differential responses

The reliable confirmation. Smuggle a prefix that produces an obviously different response, then send a second, normal request down the same connection and watch it come back wrong. A `404` for a path that exists, a `405` because your prefix changed the method, or a response that is clearly the answer to a question you did not ask on that request. That is proof. A timeout on its own is not: gateways time out for a hundred boring reasons.

### Out-of-band

Smuggle a prefix whose path or `Host` points at Burp Collaborator. A pingback proves the back end processed a request you never fully sent. This is the cleanest evidence to paste into a report.

## Using the HTTP Request Smuggler Extension

The extension is **HTTP Request Smuggler** by PortSwigger Research, from the BApp Store. It bundles the probe permutations, the timing analysis and the exploit launcher. It leans on **Turbo Intruder** for the attack phase, so install that too if Burp prompts. Burp Pro is what you want, the scanner integration is Pro-only.

### The workflow

1. **Get real traffic into Burp first.** Run the API collection through the proxy so requests land in the history with correct auth headers, content types and bodies. The extension mutates a request you give it, so a request that already returns a normal `200` gives much cleaner results than a hand-typed one that returns `400`.
2. **Pick one request per host.** Desync is a property of the connection chain, not of the route. Probing forty endpoints on the same hostname mostly tests the same gateway forty times. One good request per hostname, plus extra passes for any host that clearly sits on a different edge.
3. **Right-click the request, Extensions, HTTP Request Smuggler, "Smuggle probe".** A configuration dialog opens before it runs.
4. **Read the options in the dialog rather than accepting defaults blindly.** They change between versions, but the ones that matter fall into three groups: which desync classes to try (the HTTP/2 downgrade probes, the chunk-truncation and method-override tricks), what proof-of-concept to smuggle when something looks promising (the `poc` setting, where a Collaborator-based option is the safest and a header or body concatenation is the loudest), and how aggressive to be about timeouts and retries. On a production API, turn the aggression down.
5. **Read results in Dashboard, Issue activity.** Extension-generated issues appear there with the probe request and response attached. Everything the extension reports is a *lead*, not a finding.
6. **Confirm manually before you write it up.** See the Repeater section below.
7. **"Smuggle attack (CL.TE)" and "Smuggle attack (TE.CL)"** open Turbo Intruder pre-loaded with a script that repeatedly smuggles your prefix. Use these to confirm and to demonstrate impact. They fire a lot of traffic, so treat them as an authorised, scheduled action rather than something you run while poking around.
8. **The scan checks** register with Burp's scanner, so an active scan on the host includes desync checks without you doing anything else. Handy for coverage, but the manual probe on a well-chosen request is what actually finds things.

### Confirming by hand in Repeater

Automation gets you a lead. This gets you a finding.

- **Turn off "Update Content-Length"** in the Repeater menu, otherwise Burp helpfully rewrites the header you are deliberately lying about.
- **Group your tabs and use "Send group in sequence (single connection)".** Put the attack request in the first tab and a plain request to a known-good path in the second. One connection, sent back to back, is the only way to see the leftover prefix hit the follow-up request. If tab two comes back wrong, you have a desync.
- **Force the protocol from the Inspector** (with ALPN override enabled) so you can run the same test as HTTP/1.1 and as HTTP/2 and compare.
- **Watch for connection closes.** A front end that drops the connection on a malformed request is behaving correctly and is telling you the chain is probably safe.

> **Watch out:** desync tests are stateful and the state lives in a TCP connection. If Burp opens a new connection between your two requests, a real vulnerability shows up as nothing at all. Any negative result from a test that did not use a single connection is meaningless, not a pass.

## What to Check on an API

A practical order of work for an API collection, from cheapest to most expensive.

1. **Confirm there is an intermediary at all.** Look at the response headers for `Via`, `X-Cache`, `CF-Ray`, `X-Amz-Cf-Id`, `X-Amzn-Trace-Id`, `X-Azure-Ref`, `X-Envoy-Upstream-Service-Time`, `Server: awselb`, or an Akamai header. No front end, no smuggling, and you can note the precondition as absent and move on.
2. **Enumerate distinct hosts, not endpoints.** Group the collection by hostname and port. Each distinct chain gets its own probe. Do not forget the hosts that are in the collection but not in the main app: staging, an admin host, a partner or webhook host, a versioned `v1` host that predates the current gateway.
3. **Check whether HTTP/2 is offered.** If it is, the H2 downgrade classes are the highest-probability finding and should be probed first. Also check whether the same host behaves differently when you force HTTP/1.1.
4. **Choose the probe request carefully.** A method that accepts a body, an endpoint with no side effects (search, health, a status or profile read), and a response that is stable and distinctive enough that you will notice when it changes. Never point a smuggling probe at an endpoint that writes data. A desync can corrupt a live user's request into your prefix, and against `POST /orders` that means creating real records under someone else's session.
5. **Run the probe, then confirm on a single connection.** Timeout alone is not a finding.
6. **Prove impact with the minimum necessary.** In order of preference: reach a path the front end is supposed to block (an internal or admin route), show that a front-end-added header (the authenticated user identity the gateway injects, for example) can be overridden by your smuggled request, or capture a request you sent yourself from a second browser profile. Capturing real users' requests and tokens works and is devastating, and on a live system it is also exfiltrating third-party data. Agree that step in writing beforehand or do it against a test account you control.
7. **Note the chained impact where it applies.** A desync plus a cache in front of it is cache poisoning at a much better success rate than the usual keyed-input games. See [Web Cache Deception](/posts/web-cache-deception) for the cache side of that, and [API Pentest: Methodology and Checklist](/posts/api-pentest-methodology) for where this sits in an API engagement.

### Reporting shape

- **PASS**: front end and back end agree on message length, `Transfer-Encoding` is handled consistently or rejected, and HTTP/2 is either not downgraded or downgraded with the length recomputed and CRLF rejected.
- **FAIL**: a confirmed desync, with the probe, the poisoned follow-up response, and the class (`CL.TE`, `H2.TE`, and so on).
- **Evidence**: the raw request bytes (a screenshot of Repeater is worth more than a pasted request here, because whitespace and line endings are the bug), the follow-up response showing the poisoning, and any Collaborator interaction.

## Remediation

Fixing a desync means removing the ambiguity rather than filtering the requests that exploit it. A WAF in front of the chain does not help: it becomes another parser in the chain, and therefore another chance to disagree.

- Use HTTP/2 end to end and disable downgrading to HTTP/1.1 for back-end connections. This removes the ambiguity at the source and is the only structural fix.
- Where downgrading is unavoidable, recompute `Content-Length` from the bytes actually received, and reject any HTTP/2 request that carries a `content-length` disagreeing with the frame length, a `transfer-encoding` header, or a CR or LF in any header name, header value, or pseudo-header.
- Reject ambiguous HTTP/1.1 requests outright instead of normalising them. Any request with both `Content-Length` and `Transfer-Encoding`, a duplicate `Content-Length`, or a malformed `Transfer-Encoding` value should get a `400`, not a best guess.
- Close the connection on any parse error rather than trying to resynchronise on the next request boundary. Resynchronising is how a rejected request still poisons the connection.
- Make the front end and back end use the same HTTP parser and the same version where you can, and keep both patched. Most desyncs are two implementations, not two configurations.
- Disable back-end connection reuse, or use a dedicated connection per client connection, if the performance cost is acceptable. This removes the cross-user impact even when a parsing disagreement remains.
- Do not rely on request filtering or WAF signatures as the fix. The exploit is well-formed HTTP by design.

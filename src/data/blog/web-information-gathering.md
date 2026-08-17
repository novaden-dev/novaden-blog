---
author: Kayra
pubDatetime: 2024-08-20T07:36:44Z
modDatetime: 2025-04-02T18:10:28Z
title: "Web Information Gathering"
slug: web-information-gathering
featured: false
draft: false
tags: ["security", "web"]
category: notes
description: "The techniques for reconnaissance against a web target: WHOIS, DNS and subdomains, zone transfers, virtual hosts, certificate transparency, fingerprinting, crawling, and the files servers leak about themselves."
---

## Introduction

Web reconnaissance is about learning everything you can about a web target before you attack it. The techniques split into two modes, and the distinction matters because one is detectable and one is not:

- **Passive**: you gather information without ever touching the target's infrastructure. You query third parties (registrars, public logs, search engines, archives) that already hold data about the target.
- **Active**: you interact with the target directly, requesting pages, brute-forcing virtual hosts, fingerprinting responses. This is faster and more thorough, but it shows up in their logs.

Start passive, then go active once you know what you are looking at.

## WHOIS

WHOIS looks up the registration record for a domain: who registered it, when it was created, when it expires, and which name servers it points to.

```bash
whois example.com
```

Registrant names and emails are often hidden behind privacy services now, but the creation/expiry dates and name servers are still useful, and an unredacted record occasionally hands you a contact email or an internal hostname.

## DNS

DNS resolves a domain name like `www.example.com` to an IP address. A few concepts are worth being precise about, because recon leans on them:

- **DNS zone**: the slice of the namespace one entity administers. `example.com` and its subdomains usually live in the same zone.
- **Zone file**: the text file on the name server that lists the records for a zone (A/AAAA addresses, MX mail servers, NS name servers, and more).
- **Hosts file**: a local override that maps hostnames to IPs before DNS is consulted. It lives at `/etc/hosts` on Linux and macOS, and `C:\Windows\System32\drivers\etc\hosts` on Windows. You will edit it constantly to reach virtual hosts.

Plenty of tools do DNS recon: `dig`, `nslookup`, `host`, `dnsenum`, and `dnsrecon`. The everyday one is `dig`:

```bash
# Query specific record types
dig example.com A
dig example.com MX
dig example.com NS
```

### Subdomains

Subdomain enumeration is the process of finding the subdomains under a domain. You can do it passively (search-engine dorks, certificate transparency) or actively (brute-forcing names against the DNS server). Subdomains show up as A or AAAA records, and a `CNAME` record points one name at another as an alias.

### Zone Transfers

A zone transfer (AXFR) is a full copy of every record in a zone, meant for replicating data to a secondary name server. Misconfigured, it is a goldmine: a single request dumps the entire zone. Modern servers restrict transfers to trusted secondaries, but it is always worth trying.

```bash
dig axfr @ns1.example.com example.com
```

> **Note:** if a zone transfer succeeds against a server that should not allow it, that is itself a finding worth reporting.

### Virtual Hosts

A single web server can host many sites on one IP address, and it tells them apart using the HTTP `Host` header in each request. That is a virtual host.

The difference from a subdomain: a subdomain has its own DNS record pointing somewhere; a virtual host is a server-side configuration that may not appear in DNS at all. That is why vhosts are interesting, they can expose internal or hidden sites that no DNS lookup would reveal. To reach one whose name does not resolve publicly, add it to your local hosts file, or brute-force the `Host` header:

```bash
gobuster vhost -u http://10.10.10.10 -w /opt/SecLists/Discovery/DNS/subdomains-top1million-20000.txt --append-domain
```

## Certificate Transparency Logs

Certificate Transparency (CT) logs are public, append-only records of every SSL/TLS certificate a CA issues. Because certificates name the hosts they cover, the logs leak subdomains for free, no contact with the target required. Query them with crt.sh or Censys:

```bash
# Subdomains from crt.sh, filtered for a keyword
curl -s "https://crt.sh/?q=example.com&output=json" | jq -r '.[] | select(.name_value | contains("dev")) | .name_value' | sort -u
```

## Fingerprinting

Fingerprinting works out the technologies behind a site: the web server, framework, CMS, and their versions. You do it by reading HTTP headers, grabbing banners, probing for tell-tale responses, and analyzing page content. Tools include Wappalyzer, BuiltWith, WhatWeb, Nikto, and wafw00f (for detecting a web application firewall).

```bash
# Identify technologies, then run a light Nikto scan
whatweb https://example.com
nikto -h https://example.com -Tuning b
```

## Crawling

Crawling (or spidering) is the automated walk through a site, following links from page to page to build a map of its content and find endpoints you would never reach by hand. Burp Suite Spider, OWASP ZAP, Scrapy, and Apache Nutch all do this.

## robots.txt

`robots.txt` sits in the web root (`example.com/robots.txt`) and tells well-behaved bots which paths they may and may not crawl. Each record pairs a `User-agent` line (which bot the rule targets, `*` for all) with directives. The useful part for recon: the `Disallow` entries often point straight at the directories the owner did not want indexed, which are exactly the ones worth a look.

## .well-known

The `.well-known` directory is a standardized location under the web root (`example.com/.well-known/`) for a site's metadata: configuration files and information about its services, protocols, and security mechanisms (for example `/.well-known/security.txt`). Fuzzing for `.well-known` URLs can surface new attack vectors.

## Search Engines

Search engines are a strong passive source, especially with Google dorks: search operators that narrow results to exactly what you want.

```text
site:example.com (inurl:login OR inurl:admin)
```

## Web Archives

The Wayback Machine archives snapshots of sites over time. It lets you see how a target looked in the past, which can surface endpoints, parameters, and assets that were exposed once and never fully removed.

## Automating Recon

Once you know the individual techniques, several tools chain them together: FinalRecon, Recon-ng, theHarvester, SpiderFoot, and AutoRecon. They are convenient, but run them understanding what each step does, not as a black box.

---
title: "Virtual Hosts"
slug: virtual-hosts
category: notes
handbook: oscp
tags: ["web", "enumeration"]
draft: false
pubDatetime: 2026-07-19T23:38:46+03:00
modDatetime: 2026-09-13T20:51:50+03:00
description: "One IP can serve many sites."
---
One IP can serve many sites. The web server picks which one by the `Host` header of the request, so `http://192.168.x.y/` and `http://loly.lc/` can return completely different content from the same box. Two things follow for enumeration: a hostname a site references must be made to resolve, and hostnames that are never referenced still have to be guessed.

## Adding a Referenced Host

When an app links to, redirects to, or renders a hostname (in page content, a `Location` header, a status bar, JavaScript, or an email), that name usually does not resolve on the network. The browser cannot reach it, links break, and any content gated behind that `Host` header is invisible. Map the name to the target IP in `/etc/hosts`:

```bash
echo "TARGET  loly.lc" | sudo tee -a /etc/hosts
```

`/etc/hosts` is checked before DNS, so this makes `loly.lc` point at the target for every tool (browser, `curl`, `wpscan`, `ffuf`). Add every name and subdomain the app mentions.

```bash
# multiple names for one IP
TARGET  loly.lc www.loly.lc admin.loly.lc
```

On Loly the WordPress site referenced `http://loly.lc/wordpress/...`; without the hosts entry its links and admin pages did not resolve. Adding it was required before anything else worked.

### Confirm which host a server expects

`curl` with an explicit `Host` header tests a name without touching `/etc/hosts`, useful to confirm a guess before committing it:

```bash
curl -s -H "Host: loly.lc" http://TARGET/ | head
```

If the response differs from the default, that hostname selects a real vhost.

## Discovering Unreferenced Hosts

When nothing on the site names a vhost but different content might be served under one, fuzz the `Host` header and filter out the default response by size:

```bash
# first learn the default response size
ffuf -u http://TARGET/ -H "Host: FUZZ.loly.lc" \
  -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt

# then hide the default with -fs <size>
ffuf -u http://TARGET/ -H "Host: FUZZ.loly.lc" \
  -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt -fs 612
```

A hit is a `Host` value that returns something other than the default page. Add that name to `/etc/hosts` and enumerate it as its own site. Broader content-discovery workflow in [Web Content Discovery](/collections/oscp/web-content-discovery).

## Checklist

- App references a hostname → add it to `/etc/hosts` and re-browse.
- Redirects to a name that will not load → same fix.
- Site looks identical on IP and hostname but more content is suspected → fuzz the `Host` header.
- Always point the new name at the **target** IP, not localhost.

---
title: "Web Content Discovery"
slug: web-content-discovery
category: notes
handbook: oscp
tags: ["web", "enumeration"]
draft: false
pubDatetime: 2026-07-18T17:48:53+03:00
modDatetime: 2026-09-13T19:42:38+03:00
description: "Web servers rarely link to everything they host."
---
Web servers rarely link to everything they host. Directory and file brute forcing requests paths from a wordlist and keeps the ones that exist, surfacing admin panels, backups, config files, old pages, and whole applications that are not linked anywhere. On Pebbles the entire foothold, a ZoneMinder install under `/zm`, only turned up this way after automated recon missed it.

## What to Look For

- **Directories and files**: the default use, one path per wordlist line.
- **Extensions**: the same wordlist with `.php`, `.txt`, `.bak`, `.zip` appended, since a name without the right extension returns nothing.
- **Backups and source**: `.bak`, `~`, `.old`, `index.php.bak`, and whole archives under `/backup/`, `/backups/`, `/old/`. A `backup.zip` in the web root usually unpacks to the running application's source, which turns every later step from guessing into reading. MZEEAV's upload filter was only solvable that way.
- **Version control**: `.git/`, `.svn/`, `.DS_Store`. A `403` on `.git/` is only the directory listing being denied and the repository is usually still downloadable, see [git-dumper](/collections/oscp/git-dumper).
- **Shipped documentation**: `/docs/`, `/README.md`, `/CHANGELOG`, `/install/`. Written by the vendor, not the deployment, so it names the product, its default credentials, and its file layout. On Jordak `/docs/install/README.md` was the only thing that identified the application at all.
- **Files the application publishes about itself**: `robots.txt`, `sitemap.xml`, `.well-known/`. Free, and generated rather than written, so they describe the deployment. `robots.txt` lists the paths worth hiding; a sitemap's absolute URLs come from the app's configured base URL, which is the internal address whenever a proxy is in front. On Wombo `/sitemap.xml` pointed at `http://localhost:4567/` and named the port NodeBB actually listened on.
- **Virtual hosts**: different sites served on one IP, selected by the `Host` header.
- **Parameters**: hidden GET or POST parameters on a known endpoint.

## Identify the Application From Its Own Output

Finding the path is half of it, naming the product and version is what turns into a CVE. `whatweb URL` and the response headers come first, but a CMS that hides its identity from both usually still prints it into the page it renders:

```bash
curl -s http://TARGET/app/ | grep -iE "version|generator|powered by"
```

Common places, in order of how often they pay:

- A `<meta name="generator">` tag, written by the application at render time.
- An HTML comment at the very bottom of the body, below `</html>`, which is where several PHP applications put their build line. On ZenPhoto every page ended with `<!-- zenphoto version 1.4.1.4 [8157] (Official Build) ... -->`, and the same comment listed the loaded plugins, which is the next lead when the core version turns out to be patched.
- A "Powered by" footer, sometimes with the version stripped and the product name left.
- Asset paths and query strings, such as `/wp-content/plugins/<name>/js/x.js?ver=1.2.3`.

`Ctrl+U` shows the same thing in the browser, and a Burp response with the version selected is the cleaner screenshot for notes.

## Reading Results

Status codes guide triage, but none is reliable on its own:

- `200` exists. `301` or `302` redirect, often a directory. `403` exists but is forbidden. `401` needs auth.
- Filter by response size or word count. Many apps return `200` for everything including a soft 404, so a wall of same-size `200`s is a custom not-found page to filter out.

A `301` on a bare word is usually Apache redirecting a directory to itself with a trailing slash, so the path is a directory and the slash belongs on the end of it from then on. It matters past the browser, which follows the redirect silently: an exploit or script that takes the install path as an argument and does not follow redirects gets the redirect body instead of the application, and fails with no explanation. On ZenPhoto the same public exploit failed against `/test` and worked against `/test/`.

`401` and `403` on a page that wants credentials need telling apart, because they decide whether a found password is worth spending. A `401` carries `WWW-Authenticate` and means the server asked for a credential, so a failure is a wrong credential and another one is worth trying. A `403` on the same page means something rejected the request before authentication ran, usually a source-address filter, and the credential was never presented at all. Tomcat makes this explicit: `/manager/html` returning 403 with "the Manager is only accessible from a browser running on the same machine as Tomcat" is `RemoteAddrValve`, and no password reaches it until the request originates on the target. On Sorcerer that retired a `manager-gui` credential in one page-read instead of a round of guessing, and reframed it as something to use after a foothold rather than before one. A `401` that survives the cheap paths is the case for [Brute Forcing Logins](/collections/oscp/brute-forcing-logins).

A `404` is the answer from one server, not a statement about the host. Apache prints its own address and port in the error body (`<address>Apache/2.4.58 (Ubuntu) Server at 10.0.0.1 Port 80</address>`), which is the reminder that the response came from whatever is listening on that port and knows only its own docroot. When a path arrives from somewhere other than fuzzing, a log file, a backup archive, leaked source, replay it against every HTTP port before discarding it. On Sea a path leaked in an FTP log 404'd twice on port 80 and returned cleartext SSH credentials on 55743, because the two ports were unrelated applications with separate docroots.

### Matchers and filters

`[ffuf](/collections/oscp/ffuf)` matches a default set of status codes and shows everything else as noise. Every matcher (`-m*`, a whitelist that keeps) has a mirrored filter (`-f*`, a blacklist that hides) across the same dimensions:

- `-mc` / `-fc`: status code. `-mc 200,301,403` keeps only those, `-fc 302` hides every `302`.
- `-ms` / `-fs`: response size in bytes.
- `-mw` / `-fw`: word count.
- `-ml` / `-fl`: line count.
- `-mt` / `-ft`: response time in ms.
- `-mr` / `-fr`: regex against the response body.

All of them take comma lists and ranges, so `-fc 403,404` and `-fs 100-200` are valid. `-mc all -fc 404` is a useful pair: it shows everything except real 404s, catching odd status codes the default matcher would otherwise drop.

### When every path returns the same redirect

Some apps `302` every request to a login page or front controller, so an unfiltered run is a solid wall of identical `302`s and nothing stands out. This happened on Hawat, where port 50080 redirected everything with `Size: 0`.

The reflex is `-fc 302`, and it works when the interesting paths return a different code (on Hawat, `/cloud` and other real paths came back as `301`/`403` once the `302`s were gone). The risk is that the real hit is also a `302` to a different place, which a blanket `-fc 302` would hide too. When that is a concern, filter on what actually differs instead: response size, words, or lines (`-fs`, `-fw`, `-fl`). Run once unfiltered to read the baseline `Size`/`Words`/`Lines` of the junk `302`s, then filter that value out. Prefer words or lines over size when the app reflects the requested path back in the response, since the byte size drifts with the path length while the word and line counts usually hold steady.

### Autocalibration

Instead of reading the baseline by hand, `-ac` measures it. `ffuf` requests a few random paths, learns the catch-all response, and filters anything that matches it:

```bash
ffuf -u http://TARGET/FUZZ -w LIST -ac
```

`-acc "string"` feeds it a known false positive. Autocalibration is the fast way to clear wildcard noise, though reading the baseline once still shows what the app is actually doing.

## Tools

`gobuster`, `ffuf`, and `feroxbuster` all do the core job quickly. They differ in flexibility.

### gobuster

Simple and fast, good for straightforward directory, DNS, and vhost work:

```bash
gobuster dir -u http://TARGET/ -w /usr/share/seclists/Discovery/Web-Content/raft-large-directories.txt -x php,txt,html
```

### ffuf

`[ffuf](/collections/oscp/ffuf)` is more flexible. A `FUZZ` keyword can go anywhere in the request, which makes it the tool for parameters, headers, POST bodies, and vhosts, with precise response filtering:

```bash
# known high value paths first, seconds to run
ffuf -u http://TARGET/FUZZ -w /usr/share/seclists/Discovery/Web-Content/quickhits.txt

# directories, with extensions
ffuf -u http://TARGET/FUZZ -w /usr/share/seclists/Discovery/Web-Content/raft-large-directories.txt -e .php,.txt

# filter out a soft 404 by response size
ffuf -u http://TARGET/FUZZ -w LIST -fs 4242

# hide a blanket redirect by status code
ffuf -u http://TARGET/FUZZ -w LIST -fc 302

# or match only the codes worth seeing
ffuf -u http://TARGET/FUZZ -w LIST -mc 200,301,403

# virtual hosts
ffuf -u http://TARGET/ -H "Host: FUZZ.target" -w subdomains.txt -fs 4242

# hidden GET parameters
ffuf -u "http://TARGET/page?FUZZ=1" -w params.txt -fs 4242
```

### feroxbuster

Recursive by default and very fast, so it walks a tree without re-running by hand:

```bash
feroxbuster -u http://TARGET/ -w /usr/share/seclists/Discovery/Web-Content/raft-large-directories.txt -x php,txt
```

### Which one

For plain directory busting any of the tools is fine, and the wordlist matters more than the tool. `[ffuf](/collections/oscp/ffuf)` is the most capable because of the `FUZZ` keyword and its filtering, so it is the better default once a target needs parameter or vhost fuzzing, which `gobuster` does not do as flexibly. `[feroxbuster](/collections/oscp/feroxbuster)` is the easiest way to get recursion. Learning `ffuf` well covers the most ground.

## Wordlists

The tool finds nothing that is not in the list, so the list is the real variable. Paths below are under `/usr/share/seclists/` from the `seclists` package (`sudo apt install seclists`) unless noted.

### Directories and files

A ladder, moving to the next rung only when the current one stops returning anything new:

```
/usr/share/seclists/Discovery/Web-Content/quickhits.txt                                    ~2.5k
/usr/share/seclists/Discovery/Web-Content/common.txt                                       ~4.7k
/usr/share/seclists/Discovery/Web-Content/raft-large-directories.txt                        ~62k
/usr/share/seclists/Discovery/Web-Content/DirBuster-2007_directory-list-2.3-medium.txt      ~220k
/usr/share/seclists/Discovery/Web-Content/DirBuster-2007_directory-list-lowercase-2.3-big.txt ~1.2M
```

- `quickhits.txt`: curated high value paths, dotfiles first. Seconds to run.
- `common.txt`: the standard first pass. `/usr/share/wordlists/dirb/common.txt` from the `dirb` package is the same idea.
- `raft-large-directories.txt`: pair with `raft-large-files.txt` for files, or `raft-large-words.txt` to cover both.
- `DirBuster-2007_directory-list-2.3-medium.txt`: also at `/usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt` from the `dirbuster` package, identical file.
- `DirBuster-2007_directory-list-lowercase-2.3-big.txt`: minutes rather than seconds, so it runs in a spare terminal while other enumeration continues.

Kali's `dirbuster` package only ships the `small` and `medium` variants. Both `big` lists come from `seclists`, under the `DirBuster-2007_` prefix. When a writeup names a bare `directory-list-*` filename, find the local copy with `ls /usr/share/seclists/Discovery/Web-Content/ | grep -i directory-list`.

Lists differ in kind, not only in size, and the two families above are built from different corpora. The raft lists are ranked by how often a name appeared across a sample of real sites, so genuine hits surface early and the tail thins out fast. The DirBuster 2.3 lists come from a 2007 crawl and run deep into a long tail of names raft never recorded. Escalating from `raft-large` to `directory-list-2.3` changes the source material, so it is the step that pays when a modern list has already come up empty. On SpiderSociety the only application directory on the box, `/libspider`, did not come out of the lists above it and turned up on `directory-list-2.3-medium`, one rung in. Changing corpus is worth doing before reaching for the million-line list, which costs ten times the runtime for the same first hit.

The same holds for coverage of a whole class of path. `dirb/big.txt` has no dotfile entries, so `.git`, `.env`, and `.htpasswd` are invisible to it no matter how long it runs, while `quickhits.txt` leads with them. On bullyBox a clean `big.txt` run mapped the whole application and read like the surface was exhausted; `quickhits.txt` immediately returned `.git/HEAD` and `.git/config`, which was the box. A run that finds nothing new is a reason to change list before it is a reason to move on. And run this against every web port, not just port 80, which is the mistake Pebbles punished.

### Case and comments

`directory-list-lowercase-2.3-*` is the same corpus folded to lowercase and deduplicated, around 7% shorter. IIS and Windows paths are case-insensitive, so the mixed case list only spends extra requests there and the lowercase one is strictly better. Apache and nginx on Linux are case-sensitive, and a `CamelCase` path exists only in the mixed case list, which is the reason to keep that one in reserve rather than deleting it. Every raft list has the same `-lowercase` twin.

The DirBuster lists open with a block of `#` comment lines, and `ffuf` requests those as paths unless given `-ic`. The result is a dozen junk hits at the top of every run, all reporting the same status and size:

```
# This work is licensed under the Creative Commons [Status: 200, Size: 4317, ...]
# Copyright 2007 James Fisher                      [Status: 200, Size: 4317, ...]
                                                   [Status: 200, Size: 4317, ...]
```

They are identical because `ffuf` does not URL-encode the wordlist entry. The raw line goes into the request as `GET /# This work is licensed...`, the `#` starts a fragment, and the server sees a plain `GET /` and returns the index page. The blank lines in the same header do the same thing. Filtering that size out would work but also hides any real page of the same length, so drop the lines instead:

```bash
ffuf -ic -ac -u http://TARGET/FUZZ -w /usr/share/seclists/Discovery/Web-Content/DirBuster-2007_directory-list-lowercase-2.3-big.txt
```

Other tools vary in whether they skip comments, so `grep -v '^#' list.txt > clean.txt` settles it for anything that is not `ffuf`.

### Extensions

`Discovery/Web-Content/web-extensions.txt` is a short set for `-e` (ffuf) or `-x` (gobuster, feroxbuster), `raft-large-extensions.txt` the long one. Extensions multiply the length of the run, so take them from what the server already admits rather than guessing blind: `.php` once anything on the site is `.php`, `.asp` and `.aspx` on IIS, plus `.txt`, `.bak`, `.old`, `.zip` for the backup case.

### Parameters and applications

- `Discovery/Web-Content/burp-parameter-names.txt` for hidden GET and POST parameters.
- `Discovery/Web-Content/CMS/` for per-product lists once the application is identified. [WPScan](/collections/oscp/wpscan) handles the WordPress case better than any generic list.
- `Discovery/Web-Content/api/` for a target that answers JSON.
- `Discovery/DNS/` for subdomains and vhosts, see [Virtual Hosts](/collections/oscp/virtual-hosts).

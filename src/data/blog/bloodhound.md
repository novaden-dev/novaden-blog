---
title: "BloodHound"
slug: bloodhound
category: notes
handbook: oscp
tags: ["active-directory"]
draft: false
pubDatetime: 2026-08-01T10:35:17+03:00
modDatetime: 2026-09-13T20:51:50+03:00
description: "BloodHound ingests AD data and renders it as a graph of objects and the control relationships between them, then answers attack-path questions like 'shortest path to Domain Admin' directly."
---
BloodHound ingests AD data and renders it as a graph of objects and the control relationships between them, then answers attack-path questions like "shortest path to Domain Admin" directly. It is the automated half of [Active Directory Enumeration](/collections/oscp/active-directory-enumeration). Two pieces: a collector (SharpHound or `bloodhound-ce-python`) that gathers the data into a zip, and the BloodHound app that analyses it.

Current Kali ships BloodHound Community Edition (CE), which replaced the legacy 4.x Electron app. CE runs as a local web app backed by Neo4j and PostgreSQL. The older `neo4j start` then `bloodhound` GUI flow from the course text is legacy and no longer how the packaged tool starts.

## Install and start (Kali CE)

```bash
sudo apt update && sudo apt install -y bloodhound
sudo bloodhound-setup      # first run: starts Neo4j + PostgreSQL, then the Neo4j password step
sudo bloodhound-start      # starts the BloodHound app once setup is done
```

Setup on the Kali package is a few manual steps, not one command:

1. `bloodhound-setup` starts PostgreSQL and Neo4j, then prompts to change Neo4j's default password. Open `http://localhost:7474`, log in `neo4j` / `neo4j`, and set a new one. Neo4j forces this on first login and will not serve until the change is done.
2. Put that new Neo4j password into `/etc/bhapi/bhapi.json` so the BloodHound API can reach the database. A mismatch here is what makes `bloodhound-start` hang forever printing dots.
3. `sudo bloodhound-start`. The app comes up at `http://localhost:8080`.
4. Log into 8080 with the default `admin` / `admin`.

The two logins are separate, and only Neo4j's password changes during setup: Neo4j starts at `neo4j` / `neo4j` and must be changed on first login (the new value goes into `bhapi.json`), while the 8080 app stays at its `admin` / `admin` default. `sudo bloodhound-stop` shuts it all down.

8080 is also Burp's default proxy port and, when ligolo's WebUI is enabled, ligolo's web API port, and only one process can hold it. Two edits move the BloodHound app to a free port, and both are needed:

1. The config: add `"bind_addr": "127.0.0.1:9090",` as the first line of `/etc/bhapi/bhapi.json` (the file ships without it, so bhapi would otherwise default to 8080).
2. The wrapper: `bloodhound-start` runs its own hardcoded 8080 pre-check and refuses to start while anything holds the port, no matter what `bhapi.json` says. `grep -n 8080 $(which bloodhound-start)`, edit that check to the new port (or comment the block out), then `sudo bloodhound-start`.

Data and the ingested graph survive the restart.

The `http://localhost:7474` page is the Neo4j browser, the raw graph database behind BloodHound, not the tool's interface. It asks for a `neo4j` login rather than `admin`, and is only useful for custom Cypher queries. All normal analysis happens in the app on 8080.

Data is loaded through the UI: **Administration -> File Ingest** (or drag the zip onto the window). CE accepts the collector's zip directly.

## Collect with SharpHound (on a domain host)

SharpHound is the Windows collector, run on a domain-joined host in the current user's context (the alternative to the Kali-side `bloodhound-ce-python` below). It is not on Kali by default, and the CE app's collector-download menu moves between versions, so the reliable source is the SpecterOps release. Grab the production build and keep it with the transfer tools:

```bash
mkdir -p ~/OSCP/tools && cd ~/OSCP/tools
curl -s https://api.github.com/repos/SpecterOps/SharpHound/releases/latest \
  | grep browser_download_url | grep -iE 'SharpHound_v[0-9.]+_windows' | grep -vi debug \
  | cut -d'"' -f4 | head -1 | xargs -r wget -q
unzip -o SharpHound_v*_windows_x86.zip -d sharphound
```

CE's collector is `SharpHound.exe`; the zip carries no `.ps1`. The legacy `SharpHound.ps1` / `Invoke-BloodHound` belongs to BloodHound 4.x and emits the old JSON format that will not ingest into CE, so use the exe on CE. Transfer it to the target ([File Transfers](/collections/oscp/file-transfers)) and run it there:

```powershell
.\SharpHound.exe -c All -d corp.com          # writes a timestamped *_BloodHound.zip
```

`-c All` (CollectionMethod All) gathers group membership, sessions, ACLs, trusts, SPNs, and more. Transfer the resulting zip to Kali and ingest it; the cache file it leaves behind can be deleted. `--loop` re-runs collection over a period to catch sessions that appear later.

## Collect from Kali with credentials

When a route to the DC exists (directly or through [Tunneling and Pivoting](/collections/oscp/tunneling-and-pivoting)) and domain credentials are in hand, collect remotely with no file on the target. The CE collector is `bloodhound-ce-python` (the older `bloodhound-python` targets legacy BloodHound and its zip will not ingest into CE):

```bash
sudo apt install -y bloodhound-ce-python
bloodhound-ce-python -d corp.com -u stephanie -p 'password' -ns <DC_IP> -c All --zip
```

- `-ns` is the DNS server, normally the DC IP, needed to resolve domain hostnames from Kali.
- `-c All` runs every collection method (group memberships, ACLs, sessions, local-admin rights, trusts, SPNs), so the graph carries every edge type an attack path can chain through; a narrower method is faster but can hide a path. `-c DCOnly` is the quiet LDAP-only alternative that skips per-host session and local-admin collection.
- `--zip` bundles the per-object-type JSON files the collector writes into one archive that CE ingests directly.

`nxc` (NetExec) also has a `--bloodhound` option for an all-in-one collect when credentials are already known.

In a multi-domain forest the collector gathers one domain per run, so run it once per domain (`-d each.domain`) and ingest every zip into the same instance. BloodHound merges them into a single graph, which is what lets it show cross-domain paths such as child-domain to forest-root escalation. One credential usually collects the whole forest, since the trust lets an account in one domain read the others. Point `-ns` at each domain's own DC, its authoritative DNS server: the collector needs SRV records to find the DC and GC, which `/etc/hosts` cannot supply, so resolving one domain through another domain's DC can time the lookup out.

## Analyse

- Set node labels to always display (Settings), so names show without hovering.
- Run **Mark User/Computer as Owned** on every object already controlled (the current user, any compromised host). The "from Owned Principals" queries only return paths once owned nodes exist.
- Prebuilt queries under **Analysis** cover the common goals: *Find all Domain Admins*, *Shortest Path to Domain Admins*, *Shortest Paths to Domain Admins from Owned Principals*.
- On any edge, right-click and read the **Help / Abuse** tab: it gives the exact technique and command to exploit that relationship, cross-referencing the attacks in [Active Directory](/collections/oscp/active-directory).

Collection generates noticeable network traffic and is easy for defenders to spot. Fine for OSCP; weigh it on a real engagement.

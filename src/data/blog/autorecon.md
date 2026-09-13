---
title: "AutoRecon"
slug: autorecon
category: notes
handbook: oscp
tags: ["enumeration"]
draft: false
pubDatetime: 2026-07-18T17:48:53+03:00
modDatetime: 2026-09-13T20:51:50+03:00
description: "AutoRecon runs port scans and starts additional enumeration based on the services it finds."
---
AutoRecon runs port scans and starts additional enumeration based on the services it finds. It is useful as a background scan alongside manual enumeration.

## Install

Install the supporting tools:

```bash
sudo apt update
sudo apt install -y pipx python3-venv seclists curl dnsrecon enum4linux \
  feroxbuster gobuster impacket-scripts nbtscan nikto nmap onesixtyone \
  oscanner redis-tools smbclient smbmap snmp sslscan sipvicious \
  tnscmd10g whatweb
```

Install AutoRecon:

```bash
pipx ensurepath
pipx install git+https://github.com/AutoRecon/AutoRecon.git
```

Open a new terminal and confirm that it works:

```bash
autorecon --version
```

## Common Usage

### Scan one target

```bash
sudo env "PATH=$PATH" autorecon 192.168.X.X
```

`sudo` allows AutoRecon to use SYN and UDP scans. Results are saved under `results/`.

### Set the output directory

```bash
sudo env "PATH=$PATH" autorecon 192.168.X.X -o autorecon
```

### Read targets from a file

```bash
sudo env "PATH=$PATH" autorecon -t targets.txt -o autorecon
```

Every target in the file must be in scope.

### Limit the runtime

```bash
sudo env "PATH=$PATH" autorecon 192.168.X.X --timeout 60
```

The timeout is given in minutes.

### Update

```bash
pipx upgrade autorecon
```

## Output

The default structure is:

```text
results/
└── TARGET/
    ├── exploit/
    ├── loot/
    ├── report/
    └── scans/
```

Useful locations:

- `scans/`: Output from Nmap and service-specific tools.
- `report/notes.txt`: Findings and suggested manual commands.
- `report/local.txt` and `report/proof.txt`: empty placeholders for the OSCP local and proof flags.

Failed commands are worth checking. A missing dependency or failed plugin may leave a service only partially enumerated.

The `scans/` folder fills in as each scan finishes, so a partial folder is not the final port list. Early on it can be missing services that a later full scan finds. On Nickel the `8089` dashboard and the `33333` dev-api behind it were absent from `scans/` when first checked, which made the box look like it had no web surface and sent time down the wrong path. Confirm the port set against a completed `nmap -p-` before deciding a box has nothing there.

## Workflow

1. Start AutoRecon.
2. Run the initial Nmap scans manually.
3. Begin enumerating the discovered services.
4. Review AutoRecon's results.
5. Reproduce useful findings manually.
6. Move reusable commands and observations into the relevant methodology note.

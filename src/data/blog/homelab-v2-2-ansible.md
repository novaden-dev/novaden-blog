---
author: Kayra
pubDatetime: 2026-09-25T12:00:00Z
title: "Homelab v2.2 – Applying the Network with Ansible"
slug: homelab-v2-2-ansible
featured: false
draft: false
tags: ["selfhosting"]
category: journal
format: writeup
description: "After writing the network layer down in v2.1, the next step was making those files apply themselves: an Ansible playbook that applies the network configs to the host, validates each one, and reloads services only when something changed."
---

The network post ended with a file list: five configs that define how the lab talks to the internet and to itself. Writing them down was the first half. The second half I ran into the next time I touched the firewall: I had to edit the file, log in and copy it to the host by hand, reload the service, and if I had made the fix on the host instead, remember to copy it back. Three steps that are easy to get half wrong and impossible to verify. A configuration record you cannot execute is a document, and documents drift from reality.

So I made the repo executable. The tool for that is Ansible.

## What Ansible is

Ansible runs on one machine (mine) and manages other machines over SSH. There is no agent to install on the target: it connects, runs a module, and disconnects. A playbook lists the hosts and the roles to apply; a role is a folder of tasks that bring one layer of the system to a described state.

I can run the same playbook again and again, and it only acts when something differs from the repo. Each task describes an end state: "this file exists with this content and these permissions". When the file already matches, Ansible reports `ok` and skips it. When it differs, it reports `changed` and writes the file. A second run of the same playbook reports zero changes, which Ansible calls idempotence. My first dry run against the host found one real difference, a leftover blank line in the dnsmasq config from an earlier edit. After applying, the next run reported `changed=0`. From then on, `changed=0` means the host matches the repo.

## How the setup works

The layout inside the repo:

```text
novaden-infra/ansible/
├── ansible.cfg
├── inventory/hosts        # the host list: pve
├── playbook.yml           # applies one role to pve
└── roles/pve-network/
    ├── tasks/main.yml     # copies the five files
    ├── handlers/main.yml  # the reload/restart actions
    ├── files/             # the five config files themselves
    └── README.md
```

The tasks do not contain any configuration. They copy files the repo tracks:

```yaml
- name: Copy dnsmasq homelab configuration
  ansible.builtin.copy:
    src: dnsmasq-homelab.conf
    dest: /etc/dnsmasq.d/homelab.conf
    owner: root
    group: root
    mode: "0644"
    validate: /usr/sbin/dnsmasq --test --conf-file=%s
  notify: Restart dnsmasq
```

Each file lives in the role's `files/` directory, as Ansible convention expects. The `validate` line runs a syntax check on the staged file before it is installed: `nft -c` for the firewall, `dnsmasq --test` for the DNS config, `sshd -t` for the SSH drop-in, `visudo -c` for the sudoers rule. A broken file fails the task instead of reaching the host.

The `notify` line connects the task to a handler. Handlers are actions like "reload nftables" or "restart dnsmasq" that run only when a file actually changed, and once per play even if several tasks request the same one. A run that changes nothing therefore restarts nothing.

The role handles two files differently:

- `/etc/network/interfaces` gets its own handler. When the file changes, the playbook runs `ifreload -a` detached from the connection. Proxmox uses ifupdown2, whose reload applies only the changed parts of the configuration, so unchanged interfaces stay up. If the change itself touches the wifi uplink that the connection runs over, the connection blips for a moment and the reload still completes.
- `/etc/wpa_supplicant/wpa_supplicant-wlp4s0.conf` is not managed at all, because it holds the wifi password and the repo does not track secrets. It changes rarely; editing it on the host is fine.

## The workflow now

```bash
ansible-playbook playbook.yml --check --diff   # preview: shows what would change, applies nothing
ansible-playbook playbook.yml                  # apply
```

`--check --diff` reports the changes a run would make, file by file, and applies nothing. Edit the repo file, preview the diff, apply, then run the check again: `changed=0` means the host matches the repo and the work is done.

The same stretch of work taught one dnsmasq rule: it loads every file in `/etc/dnsmasq.d/`, including backups left there "temporarily". A backup file with duplicate entries stopped the service from starting until I moved it to `/root/`. Backups now go to `/root/`, and nothing extra lives in a config directory that a daemon reads wholesale.

## What I did not automate

Everything except the network layer stays manual for now: guests, app compose stacks, and backups. The network went first because it is the foundation the rest stands on. Expanding the playbook to guests and apps is the next step.

The rebuild has three parts: Ansible for the network files, compose files for the applications, and restic for the data. The configs are written down, validated before they load, and re-runnable until they report zero changes.

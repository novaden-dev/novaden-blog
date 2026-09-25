---
author: Kayra
pubDatetime: 2026-09-25T12:00:00Z
title: Ansible Foundations
slug: ansible-foundations
featured: false
draft: false
tags: ["ansible"]
category: notes
description: What Ansible is, how playbooks, inventory, and roles fit together, what idempotence and handlers mean, and how check mode makes changes safe to preview.
---

## Introduction

Ansible manages other machines over SSH. You run it from one machine (the **control node**) and it configures a list of target machines (the **inventory**) by connecting, running small units of work, and disconnecting. There is no agent to install on the targets: the requirements are SSH access and Python on the target machine.

The core idea is that you describe the **end state** you want ("this file exists with this content") rather than the steps to get there ("edit this file"). Ansible compares the described state with reality and does only what is missing. This property is called **idempotence**, and it is why the same playbook can be run repeatedly: a run that finds everything already correct reports `changed=0` and touches nothing.

## Inventory: the list of machines

The inventory answers "which machines exist and how do I reach them". The default location is `/etc/ansible/hosts`, but most projects ship their own file and point the config at it:

```ini
[webservers]
web1 ansible_user=root
web2 ansible_user=root

[databases]
db1
```

- `[webservers]` starts a **group**. Playbooks target machines by group name.
- Each line is a hostname or IP. Anything after it (`ansible_user=root`) is an inline variable for that host.
- `ansible_user=root` says "connect as root" instead of your local username. Other common inline variables: `ansible_host` (the actual address when the name differs), `ansible_port`.

## Playbook and play

A **playbook** is a YAML file containing one or more **plays**. A play binds a set of hosts to a set of things to do:

```yaml
---
- name: Configure webservers
  hosts: webservers
  gather_facts: true
  roles:
    - nginx
```

- `name`: a label, shown in the run output.
- `hosts`: which inventory group this play applies to.
- `gather_facts`: before the play, Ansible runs a fact-collection task (OS version, IP addresses, disk space). These become variables available to tasks. Setting `false` skips it, which speeds up plays that do not need facts.
- `roles`: the roles to apply, in order.

Run it with:

```bash
ansible-playbook -i inventory/hosts playbook.yml            # apply
ansible-playbook -i inventory/hosts playbook.yml --check --diff   # preview
ansible-playbook -i inventory/hosts playbook.yml --limit web1     # one host only
```

`--check` runs every task in simulation: it reports what would change without changing anything. `--diff` shows the exact file differences that would result. The pair is how you review a change before it lands, and a second `--check` run reporting `changed=0` after an apply is the confirmation that the machines match the playbook.

Without a playbook, the same binary runs single modules against a group:

```bash
ansible webservers -i inventory/hosts -m ping                      # reachability
ansible webservers -i inventory/hosts -m command -a "uptime"       # one command
ansible webservers -i inventory/hosts -m service -a "name=nginx state=restarted"
```

## Roles: reusable units

A **role** is a directory that packages one layer of configuration. The names of the subdirectories are fixed by convention:

```text
roles/nginx/
├── tasks/main.yml      # the steps to run
├── handlers/main.yml   # service restarts triggered by tasks
├── files/              # static files to copy to targets
├── templates/          # files with variables, rendered before copying
├── defaults/main.yml   # variables with lowest precedence
└── vars/main.yml       # variables with high precedence
```

A task is a single module call. **Modules** are the built-in units of work: `copy` puts a file on the target, `service` manages a daemon, `package` installs software, `command` runs a command, and there are hundreds more. Each module is idempotent where the concept applies: `copy` checks content and permissions and does nothing if they already match.

```yaml
- name: Copy the nginx site config
  ansible.builtin.copy:
    src: site.conf          # from roles/nginx/files/
    dest: /etc/nginx/sites-available/site.conf
    owner: root
    group: root
    mode: "0644"
    validate: nginx -t -c %s
  notify: Reload nginx
```

Use the `validate` option for anything that controls a running service. It runs the given command against the staged file (`%s` is the path) before installing it. A broken config fails the task instead of reaching the machine, which prevents the failure mode where a syntax error takes down a service on reload.

## Handlers: changes trigger actions

A **handler** is an action that runs only when a task reports a change, and only once per play even if several tasks notify it:

```yaml
# handlers/main.yml
- name: Reload nginx
  ansible.builtin.service:
    name: nginx
    state: reloaded
```

Tasks "notify" handlers by name. A run where nothing changed fires no handlers, so services are not restarted without a reason. This is the mechanism that makes configuration runs safe to repeat on production machines.

Two details complete the picture:

- Collapsing is per handler name. A play that notifies both "reload nginx" and "restart dnsmasq" runs both handlers once each.
- Handlers run at the end of the play by default. When a later task depends on the new configuration already being active, insert `ansible.builtin.meta: flush_handlers` at that point: it runs every handler notified so far, then the play continues.

## Config: ansible.cfg

`ansible.cfg` in the project directory sets where Ansible looks for things, and Ansible picks it up automatically from the working directory:

```ini
[defaults]
inventory = inventory/hosts       # where the host list lives
interpreter_python = auto_silent  # auto-discover Python on targets, quietly
```

Without this file, Ansible falls back to system defaults such as `/etc/ansible/hosts`, which is why projects that ship their own inventory need it.

## How it fits together

1. `ansible.cfg` says where the inventory is.
2. The inventory lists the machines and how to connect.
3. The playbook maps groups of machines to roles.
4. Each role's tasks describe end states, module by module.
5. Changed tasks notify handlers, which reload the affected services.
6. `--check --diff` previews everything without touching the targets.

The mental shift from shell scripts: a script records actions and assumes the starting point. A playbook records end states and measures the distance to them, which is what makes the same file useful for applying a change, checking a machine, and rebuilding from scratch.

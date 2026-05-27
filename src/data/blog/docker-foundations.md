---
author: Kayra
pubDatetime: 2026-05-27T00:00:00Z
title: Docker Foundations
slug: docker-foundations
featured: false
draft: false
tags:
  - containers
  - docker
  - notes
description: The mental model behind Docker. What containers actually are, how they differ from VMs, image layers, the Dockerfile, networking, volumes, and registries.
---

## Introduction

Docker is the tool most people meet first when they start working with containers. The thing to understand up front is that "Docker" and "containers" are not the same thing. Containers are a set of Linux kernel features. Docker is a convenient way to drive them.

## Containers vs Virtual Machines

A virtual machine virtualizes the **hardware**. The hypervisor pretends to be a CPU, disk, and network card. On top of that, a full guest operating system boots, with its own kernel.

A container virtualizes the **operating system**. There is no guest kernel. The container shares the host's kernel and uses kernel features to fence off its own view of processes, network, filesystem, and users.

| | Virtual Machine | Container |
| --- | --- | --- |
| Isolation boundary | Hardware | Kernel namespaces |
| Guest kernel | Yes | No (shares host) |
| Boot time | Seconds to minutes | Milliseconds |
| Disk footprint | Gigabytes (full OS) | Megabytes (app + libs) |
| Density per host | Tens | Hundreds to thousands |

That's why containers feel fast and cheap. There is no second kernel and no virtual hardware between you and the host.

## How Containers Actually Work

Containers are built from three kernel features:

- **Namespaces**: give a process its own private view of system resources. Separate namespaces exist for PIDs, the network stack, mounts (the filesystem), users, IPC, and the hostname. Inside the container, the entrypoint is PID 1, even though on the host it has some larger PID.
- **Control groups (cgroups)**: limit how much CPU, memory, and I/O a group of processes can use. This is how Docker enforces `--memory` and `--cpus` limits.
- **Union filesystems (overlayfs)**: stack read-only image layers under a thin writable layer per container. Multiple containers built from the same image share those underlying layers on disk.

Docker is, in essence, a daemon that wires those features together and gives you a CLI for it.

## Images and Containers

This is the relationship people stumble over:

- An **image** is an immutable, read-only template. It's a stack of filesystem layers plus some metadata (the default command, environment variables, exposed ports).
- A **container** is a running (or stopped) instance of an image. It gets its own writable layer on top, its own namespaces, and its own lifecycle.

Class versus instance. One image, many containers.

```bash
docker run nginx
```

That single command pulls the `nginx` image if it isn't already local, creates a container from it, and starts the container's entrypoint.

## Image Layers and Build Cache

Each instruction in a Dockerfile produces a new read-only layer. Layers are content-addressed and cached: if the inputs to a layer haven't changed, Docker reuses the cached version instead of rebuilding it.

That's why Dockerfile *order* matters. Put the things that change least at the top, and the things that change most at the bottom:

```dockerfile
FROM python:3.12-slim
WORKDIR /app

# Dependencies change rarely, copy and install first
COPY requirements.txt .
RUN pip install -r requirements.txt

# Source code changes constantly, copy last
COPY . .

CMD ["python", "main.py"]
```

### A Scenario

Take the Dockerfile above. The first build runs all six layers end to end. The `pip install` step takes ~45 seconds because it's downloading and compiling packages. Total: ~50 seconds.

Now you fix a typo in `main.py` and rebuild. Docker walks the Dockerfile top-down and checks each layer's inputs:

- `FROM python:3.12-slim`: base image unchanged. **Cache hit**.
- `WORKDIR /app`: instruction unchanged. **Cache hit**.
- `COPY requirements.txt .`: the file is byte-identical. **Cache hit**.
- `RUN pip install -r requirements.txt`: previous layer was a hit and the command is the same. **Cache hit**. The 45-second install is skipped entirely.
- `COPY . .`: one of the files (`main.py`) changed. **Cache miss**, rebuild.
- `CMD [...]`: rebuild.

Total: about 2 seconds.

Now picture the same Dockerfile with the order wrong:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . .                              # copies main.py too
RUN pip install -r requirements.txt
CMD ["python", "main.py"]
```

You fix the same typo. `COPY . .` is now a cache miss because `main.py` changed, and every layer below it inherits that miss, including the pip install. You pay the full 45 seconds again.

Same instructions, different order, 20x slower rebuild. That's why "least-changing on top" matters.

## The Dockerfile

A Dockerfile is a declarative recipe for building an image. The instructions you'll see most:

| Instruction | Purpose |
| --- | --- |
| `FROM` | Base image to build on. |
| `WORKDIR` | Set the working directory for the instructions that follow. |
| `COPY` | Copy files from the build context into the image. |
| `RUN` | Execute a command at build time and commit the result as a new layer. |
| `ENV` | Set an environment variable that persists into the running container. |
| `EXPOSE` | Document which ports the container listens on (does not publish them). |
| `CMD` | Default command, easy to override at `docker run` time. |
| `ENTRYPOINT` | Default command, harder to override. The container effectively becomes that program. |

> **Gotcha:** `EXPOSE` is documentation only. It does not publish a port to the host. That's what `-p 8080:80` does at `docker run` time.

### Multi-stage Builds

A multi-stage build uses one image to compile or assemble your app and a second, much smaller image to actually run it. The build tools never ship to production.

```dockerfile
FROM golang:1.22 AS build
WORKDIR /src
COPY . .
RUN go build -o /out/app ./cmd/app

FROM gcr.io/distroless/static
COPY --from=build /out/app /app
ENTRYPOINT ["/app"]
```

The final image contains just the binary, not the Go toolchain. This is usually the difference between a 900 MB image and a 15 MB one.

## Networking

By default, Docker creates a few networks for you. The three you'll see most:

- **bridge** (the default): each container gets its own IP on a private virtual network. Containers on the same bridge can reach each other. The outside world reaches them only through published ports (`-p`).
- **host**: the container shares the host's network stack directly. No isolation, but also no NAT. Good for performance-sensitive workloads, bad for security.
- **none**: no networking at all. Useful for batch jobs that only process local files.

For multi-container apps, you'll usually create your own user-defined bridge network. On a user-defined network, containers can resolve each other by name (`postgres:5432` instead of `172.17.0.3:5432`). That name-based discovery is the foundation of how Compose links services.

## Volumes and Bind Mounts

A container's writable layer disappears when the container is removed. For anything you want to keep, you need persistent storage. Two options:

- **Volumes**: managed by Docker, stored under `/var/lib/docker/volumes/` on the host. Portable, and the recommended default.
- **Bind mounts**: mount any host path into the container. Useful for local development (live-editing source from the host), but tied to the host's filesystem layout.

```bash
# Named volume (Docker manages the location)
docker run -v pgdata:/var/lib/postgresql/data postgres

# Bind mount (you pick the host path)
docker run -v $(pwd):/app node
```

> **Note:** Bind mounts shadow whatever was at that path inside the image. If `/app` had files in the image and you bind-mount an empty directory over it, the image's files become invisible.

## Docker Compose

Once an app has more than one container (a web service, a database, a cache, a worker), the raw `docker run` commands get long fast. You're juggling networks, volumes, environment variables, port mappings, and the order things start in, all on the CLI. Forget one flag and the next person to clone the repo can't reproduce your setup.

**Compose** is the fix. It's a tool that reads a single YAML file (`compose.yml`) describing every container the app needs, plus the networks and volumes that glue them together, and brings the whole thing up with one command.

A minimal example:

```yaml
services:
  web:
    build: .
    ports:
      - "8080:80"
    depends_on:
      - db
    environment:
      DATABASE_URL: postgres://app:secret@db:5432/app

  db:
    image: postgres:16.3
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: secret
      POSTGRES_DB: app
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

`docker compose up -d` and the whole stack is running. A few things Compose did for you automatically:

- Created a **user-defined network** for the project so `web` can reach `db` by name (note the `db` in the `DATABASE_URL`).
- Created the `pgdata` **named volume** so Postgres data survives `down` and restarts.
- Picked a **project name** (defaults to the directory name) and prefixed everything with it: containers, networks, and volumes all become `myapp_web`, `myapp_db`, `myapp_pgdata`. That keeps two projects on the same host from colliding.
- Pulled or built images as needed, then started services in dependency order.

The mental model is: the YAML file is the source of truth. Anything you'd otherwise type into `docker run`, `docker network create`, or `docker volume create` belongs in `compose.yml`. The commands in the cheat sheet (`up`, `down`, `logs`, `exec`) are all variations on "do this to the stack defined in the file."

> **Gotcha:** Compose is a **single-host** tool. It runs your stack on one machine. Scaling across many machines is a different problem solved by Kubernetes or Swarm, not Compose.

## Registries

A registry is where images live. The default is **Docker Hub** (`docker.io`). Other common registries are **GitHub Container Registry** (`ghcr.io`), **Quay** (`quay.io`), and the cloud-provider registries (AWS ECR, Google Artifact Registry, Azure Container Registry).

Image names in the wild are `[registry/]namespace/name[:tag]`:

- `nginx` resolves to `docker.io/library/nginx:latest`
- `ghcr.io/novaden/novaden-blog:main` is explicit about registry, owner, name, and tag

`:latest` is a tag like any other. It is not "the newest version", it's whatever was last pushed with that label. Pin to a real version (`postgres:16.3`) in anything production-shaped.

## Daemon and Rootless Mode

Classic Docker runs a privileged daemon (`dockerd`) as root. The CLI talks to it over a Unix socket. Anyone in the `docker` group can talk to the daemon, and anyone who can talk to the daemon can effectively become root on the host. Mount `/` from the host into a container and you're done.

**Rootless mode** runs the daemon as your own user, using user-namespace remapping. You trade some functionality (binding to ports below 1024 needs extra setup, performance is slightly lower) for a much smaller blast radius if a container is compromised.

> **Quick reference:** the actual commands for building, running, inspecting, and cleaning up containers live in the [Docker Cheat Sheet](/posts/docker-cheatsheet).

---
author: Kayra
pubDatetime: 2026-05-27T00:00:00Z
title: Docker Cheat Sheet
slug: docker-cheatsheet
featured: false
draft: false
tags: ["containers", "cheatsheet"]
category: notes
description: A growing quick-reference of the Docker commands I actually reach for, from running containers and building images to networks, volumes, Compose, and cleanup.
---

A living quick-reference for the Docker commands I actually use. Each section pairs commands with the moment you'd reach for them. For the model behind any of this, see [Docker Foundations](/posts/docker-foundations).

## Getting Help

```bash
# Top-level help
docker --help

# Help for a subcommand
docker run --help

# Version of client and daemon
docker version

# Daemon info: storage driver, root dir, runtime
docker info
```

## Running Containers

```bash
# Run in foreground, remove when it exits
docker run --rm -it ubuntu bash

# Run detached, name it, publish a port
docker run -d --name web -p 8080:80 nginx

# Set an environment variable
docker run -e POSTGRES_PASSWORD=secret postgres

# Mount a named volume
docker run -v pgdata:/var/lib/postgresql/data postgres

# Mount the current directory as a bind mount
docker run -v "$(pwd)":/app node

# Limit CPU and memory
docker run --cpus="1.5" --memory="512m" myapp

# Auto-restart on failure or reboot
docker run -d --restart=unless-stopped --name api myapp
```

> **Note:** `-it` is two flags glued together. `-i` keeps STDIN open, `-t` allocates a pseudo-TTY. You almost always want both for an interactive shell.

## Listing and Inspecting

```bash
# Running containers
docker ps

# All containers, including stopped
docker ps -a

# Just IDs (useful for piping)
docker ps -q

# Full details (JSON)
docker inspect web

# Pull one field out with a Go template
docker inspect -f '{{.NetworkSettings.IPAddress}}' web

# Live CPU, memory, network, I/O
docker stats

# Snapshot of stats (one read, no streaming)
docker stats --no-stream
```

## Logs

```bash
# Dump all logs
docker logs web

# Follow (like tail -f)
docker logs -f web

# Last 100 lines, with timestamps
docker logs --tail 100 -t web

# Since a relative time
docker logs --since 10m web
```

## Exec and Shell Access

```bash
# Open an interactive shell in a running container
docker exec -it web bash
docker exec -it web sh             # for alpine / distroless-ish images

# Run a one-off command without a shell
docker exec web ls /etc/nginx

# Run as a specific user
docker exec -u root -it web bash
```

> **Gotcha:** `docker exec` requires the container to be running. To poke inside a stopped one, start it first or `docker run` a fresh shell against the same image.

## Lifecycle

```bash
# Start, stop, restart by name or ID
docker start web
docker stop web
docker restart web

# Pause / unpause (freezes processes via cgroups freezer)
docker pause web
docker unpause web

# Remove a stopped container
docker rm web

# Force-remove a running container
docker rm -f web

# Rename
docker rename old-name new-name
```

## Building Images

```bash
# Build from current directory, tag the result
docker build -t myapp:1.0 .

# Use a non-default Dockerfile
docker build -f Dockerfile.dev -t myapp:dev .

# Build without using the cache
docker build --no-cache -t myapp:1.0 .

# Pass a build argument
docker build --build-arg VERSION=1.2.3 -t myapp:1.2.3 .

# Target a specific stage in a multi-stage build
docker build --target build -t myapp:build .

# Build for a different platform (needs buildx)
docker buildx build --platform linux/amd64,linux/arm64 -t me/app:1.0 --push .
```

## Images

```bash
# List local images
docker images

# Pull a specific tag
docker pull postgres:16.3

# Tag an existing image
docker tag myapp:1.0 ghcr.io/me/myapp:1.0

# Remove an image
docker rmi myapp:old

# Show the layer history of an image
docker history nginx

# Save an image to a tarball (for air-gapped transfer)
docker save -o nginx.tar nginx:latest

# Load an image from a tarball
docker load -i nginx.tar
```

## Registry

```bash
# Log in (Docker Hub by default)
docker login

# Log in to a specific registry
docker login ghcr.io
docker login -u USERNAME ghcr.io      # prompts for password / token

# Push an image
docker push ghcr.io/me/myapp:1.0

# Log out
docker logout ghcr.io
```

## Networking

```bash
# List networks
docker network ls

# Create a user-defined bridge network
docker network create appnet

# Run a container on a specific network
docker run -d --name db --network appnet postgres

# Attach an existing container to another network
docker network connect appnet web

# Detach
docker network disconnect appnet web

# Inspect (shows connected containers and their IPs)
docker network inspect appnet

# Remove
docker network rm appnet
```

> **Note:** On a user-defined network, containers resolve each other by name. From `web` you can reach `db` as `db:5432`, no IP juggling.

## Volumes

```bash
# List volumes
docker volume ls

# Create a named volume
docker volume create pgdata

# Inspect (shows the mountpoint on the host)
docker volume inspect pgdata

# Remove
docker volume rm pgdata

# Remove all unused volumes
docker volume prune
```

## Copying Files

```bash
# Copy from container to host
docker cp web:/etc/nginx/nginx.conf ./nginx.conf

# Copy from host to container
docker cp ./nginx.conf web:/etc/nginx/nginx.conf
```

## Docker Compose

```bash
# Bring the stack up in the background
docker compose up -d

# Bring it up and rebuild changed images
docker compose up -d --build

# Tail logs from all services
docker compose logs -f

# Tail logs from one service
docker compose logs -f api

# List services in this project
docker compose ps

# Run a one-off command in a service container
docker compose run --rm api python manage.py migrate

# Exec into a running service
docker compose exec api bash

# Restart a single service
docker compose restart api

# Tear it all down (containers + networks)
docker compose down

# Tear it down and delete named volumes too
docker compose down -v
```

> **Danger:** `docker compose down -v` removes named volumes for the project. Postgres data, Redis snapshots, anything you put in a volume, all gone. Use plain `down` if you want to keep state across restarts.

## Cleanup

```bash
# Remove stopped containers, dangling images, unused networks, and build cache
docker system prune

# Same, but also remove unused images (not just dangling)
docker system prune -a

# Add unused volumes to the sweep
docker system prune -a --volumes

# Disk usage breakdown
docker system df

# Targeted prunes
docker container prune
docker image prune
docker network prune
docker volume prune
```

> **Danger:** `docker system prune -a --volumes` deletes any volume that isn't currently attached to a container. Stop a Postgres container to upgrade it, run this, lose your data.

## Quick Debug Recipes

```bash
# What's eating disk?
docker system df -v

# Why did this container exit?
docker inspect -f '{{.State.ExitCode}} {{.State.Error}}' CONTAINER

# Get a shell in a broken image without running its entrypoint
docker run --rm -it --entrypoint sh myapp:broken

# See what ports a container actually published
docker port web

# Diff: what files has the container changed vs the image?
docker diff web
```

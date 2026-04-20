# novaden-blog

Source for [novaden.dev](https://novaden.dev). Forked from [AstroPaper](https://github.com/satnaing/astro-paper).

On push to `main`, GitHub Actions builds a container image and publishes it to
`ghcr.io/novaden-dev/novaden-blog:latest`. A webhook on my homelab pulls the new
image and recreates the blog container.

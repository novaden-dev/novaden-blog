# Base stage for building the static files
FROM node:lts AS base
WORKDIR /app

# Install pnpm (pinned to match CI)
RUN corepack enable && corepack prepare pnpm@10.11.1 --activate

COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .
RUN pnpm run build

# Runtime stage for serving the application
FROM nginx:mainline-alpine-slim AS runtime
COPY --from=base /app/dist /usr/share/nginx/html
EXPOSE 80

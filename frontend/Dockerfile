# ---------------------------------------------------------------------------
# Frontend image, built in two stages:
#   1) "build": Node compiles the React/TypeScript app into static files (dist/)
#   2) final:   Caddy serves those files, proxies /api to the backend, does HTTPS
# The final image contains no Node.js and no source code - just ~1 MB of files.
# ---------------------------------------------------------------------------
FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci                      # exact versions from package-lock.json
COPY . .
RUN npm run build               # type-check + bundle -> /app/dist

FROM caddy:2-alpine
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv
EXPOSE 80 443

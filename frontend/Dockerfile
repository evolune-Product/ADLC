# syntax=docker/dockerfile:1
FROM node:22-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

# Vite inlines VITE_* at build time, so the API URL is a build arg, not runtime env.
ARG VITE_API_URL=http://localhost:8000
ARG VITE_SOCKET_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL VITE_SOCKET_URL=$VITE_SOCKET_URL

COPY . .
RUN npm run build

# ── Runtime ───────────────────────────────────────────────────────────────────
FROM nginx:1.27-alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

# 127.0.0.1, not localhost: busybox wget on Alpine resolves "localhost" to
# ::1 first, and nginx's "listen 80" here binds IPv4 only — that mismatch
# makes the healthcheck fail with "Connection refused" even though the
# server is up and reachable from outside the container.
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD wget -qO- http://127.0.0.1/ >/dev/null || exit 1

CMD ["nginx", "-g", "daemon off;"]

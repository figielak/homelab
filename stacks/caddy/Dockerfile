# Caddy z pluginem DNS Cloudflare.
#
# Oficjalny obraz Caddy nie zawiera pluginow DNS, a gotowy obraz
# ghcr.io/caddy-dns/cloudflare jest wylacznie amd64 — na ARM64 odpada.
# Dlatego budujemy wlasny, dwuetapowo.
#
# OBIE wersje sa pinowane. Aktualizacja = swiadoma zmiana ARG + rebuild.

ARG CADDY_VERSION=2.11.4

FROM caddy:${CADDY_VERSION}-builder AS builder

ARG CLOUDFLARE_PLUGIN_VERSION=v0.2.4
RUN xcaddy build \
      --with github.com/caddy-dns/cloudflare@${CLOUDFLARE_PLUGIN_VERSION}

ARG CADDY_VERSION
FROM caddy:${CADDY_VERSION}-alpine

COPY --from=builder /usr/bin/caddy /usr/bin/caddy

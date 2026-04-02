# https://developers.home-assistant.io/docs/apps/configuration#app-dockerfile
# Official Home Assistant Python base (Alpine + bashio + s6-overlay).
ARG BUILD_FROM=ghcr.io/home-assistant/base-python:3.13-alpine3.23
FROM ${BUILD_FROM}

ARG BUILD_ARCH=amd64

WORKDIR /app

# Säkerställ POSIX-shell och bash (finns i HA base, men explicit om något bygglager avviker).
RUN apk add --no-cache bash

ARG CLOUDFLARED_VERSION=2026.3.0
RUN set -eux; \
    apk add --no-cache ca-certificates curl; \
    case "${BUILD_ARCH}" in \
        amd64) CF_ARCH=amd64 ;; \
        aarch64) CF_ARCH=arm64 ;; \
        armv7|armhf) CF_ARCH=arm ;; \
        i386) CF_ARCH=386 ;; \
        *) echo "Unsupported BUILD_ARCH=${BUILD_ARCH}" >&2; exit 1 ;; \
    esac; \
    curl -fsSL \
      "https://github.com/cloudflare/cloudflared/releases/download/${CLOUDFLARED_VERSION}/cloudflared-linux-${CF_ARCH}" \
      -o /usr/local/bin/cloudflared; \
    chmod +x /usr/local/bin/cloudflared

COPY requirements.txt /app/requirements.txt
RUN python -m pip install --no-cache-dir -r /app/requirements.txt

COPY src /app/src

# s6-overlay: start web server via services.d (samma mönster som home-assistant/apps-example).
COPY rootfs /
RUN find /etc/services.d -name run -type f -exec chmod a+x {} +

LABEL \
  io.hass.version="0.1.4" \
  io.hass.type="addon" \
  io.hass.arch="armhf|aarch64|i386|amd64|armv7"

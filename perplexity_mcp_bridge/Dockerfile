# https://developers.home-assistant.io/docs/apps/configuration#app-dockerfile
# base-python: Alpine + s6. Startfil skapas HÄR med LF (undviker Windows CRLF → "unable to spawn ./run").
ARG BUILD_FROM=ghcr.io/home-assistant/base-python:3.13-alpine3.23
FROM ${BUILD_FROM}

ARG BUILD_ARCH=amd64

WORKDIR /app

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

# Skapa s6 longrun INUTI imagen — aldrig COPY av run från Git på Windows (CRLF ger ENOENT på shebang).
RUN install -d /etc/services.d/perplexity-mcp-bridge && { \
    echo '#!/bin/sh'; \
    echo 'set -eu'; \
    echo 'export PYTHONUNBUFFERED=1'; \
    echo 'export PATH="/usr/local/bin:/usr/bin:/bin:${PATH:-}"'; \
    echo 'cd /app || exit 1'; \
    echo 'echo "[perplexity-mcp-bridge] Starting uvicorn on 0.0.0.0:8099"'; \
    echo "exec /usr/local/bin/python -m uvicorn src.main:app --host 0.0.0.0 --port 8099 --proxy-headers --forwarded-allow-ips='*'"; \
    } > /etc/services.d/perplexity-mcp-bridge/run \
    && chmod 0755 /etc/services.d/perplexity-mcp-bridge/run \
    && test -s /etc/services.d/perplexity-mcp-bridge/run \
    && test "$(head -1 /etc/services.d/perplexity-mcp-bridge/run | tr -d '\r')" = '#!/bin/sh'

LABEL \
  io.hass.version="0.1.6" \
  io.hass.type="addon" \
  io.hass.arch="armhf|aarch64|i386|amd64|armv7"

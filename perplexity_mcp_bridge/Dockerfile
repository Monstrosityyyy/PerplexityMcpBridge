# https://developers.home-assistant.io/docs/apps/configuration#app-dockerfile
# Official Home Assistant Python base (Alpine + bashio + s6); do not use random third-party tags.
ARG BUILD_FROM=ghcr.io/home-assistant/base-python:3.13-alpine3.23
FROM ${BUILD_FROM}

# Supervisor provides this during add-on builds (amd64, aarch64, armv7, armhf, i386).
ARG BUILD_ARCH=amd64

WORKDIR /app

# cloudflared: not reliably available in Alpine repos across versions — use Cloudflare release binaries.
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
COPY run.sh /run.sh
RUN chmod a+x /run.sh

LABEL \
  io.hass.version="0.1.0" \
  io.hass.type="addon" \
  io.hass.arch="armhf|aarch64|i386|amd64|armv7"

CMD [ "/run.sh" ]

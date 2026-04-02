from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger("perplexity_mcp_bridge.ha")

# Resolved internal API base (cached; Supervisor vs homeassistant hostname differs by install).
_resolved_ha_base: str | None = None


def reset_ha_resolution_cache() -> None:
    global _resolved_ha_base
    _resolved_ha_base = None


def _load_supervisor_options() -> dict[str, Any]:
    """Options from add-on configuration (HA UI → add-on → Configuration)."""
    p = Path("/data/options.json")
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _candidate_ha_bases() -> list[str]:
    env = (os.getenv("HA_URL") or "").strip().rstrip("/")
    bases: list[str] = []
    if env:
        bases.append(env)
    # Order matters: try Supervisor proxy first, then direct homeassistant service on Docker network.
    for b in (
        "http://supervisor/core",
        "http://homeassistant/core",
        "http://homeassistant:8123",
    ):
        if b not in bases:
            bases.append(b)
    return bases


class HomeAssistantClient:
    """Talks to Home Assistant REST API using Supervisor token and/or a long-lived token."""

    def __init__(self, long_lived_token_from_secrets: str | None = None):
        self.supervisor_token = os.getenv("SUPERVISOR_TOKEN")
        opts = _load_supervisor_options()
        opt_token = (opts.get("homeassistant_long_lived_token") or "").strip()
        sec_token = (long_lived_token_from_secrets or "").strip()
        self.long_lived_token = opt_token or sec_token or None

    def _auth_headers(self) -> dict[str, str]:
        if self.long_lived_token:
            return {"Authorization": f"Bearer {self.long_lived_token}"}
        if self.supervisor_token:
            return {"Authorization": f"Bearer {self.supervisor_token}"}
        return {}

    def connection_mode(self) -> str:
        if self.long_lived_token:
            return "long_lived_token"
        if self.supervisor_token:
            return "supervisor"
        return "none"

    async def _ensure_base(self) -> str:
        global _resolved_ha_base
        if _resolved_ha_base:
            return _resolved_ha_base
        headers = self._auth_headers()
        if not headers:
            raise RuntimeError(
                "No Home Assistant credentials: need SUPERVISOR_TOKEN from Supervisor "
                "or a Long-Lived Access Token (add-on options or wizard)."
            )
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            last_err: Exception | None = None
            for base in _candidate_ha_bases():
                try:
                    url = f"{base}/api/"
                    resp = await client.get(url, headers=headers)
                    if resp.status_code == 200:
                        _resolved_ha_base = base
                        logger.info("Home Assistant API base resolved to %s", base)
                        return base
                    logger.debug("HA probe %s -> %s", url, resp.status_code)
                except Exception as e:
                    last_err = e
                    logger.debug("HA probe failed for %s: %s", base, e)
                    continue
        raise RuntimeError(
            f"Cannot reach Home Assistant API (tried supervisor + homeassistant). Last error: {last_err!r}"
        )

    async def health(self) -> bool:
        try:
            await self._ensure_base()
            return True
        except Exception as e:
            logger.warning("HA health check failed: %s", e)
            return False

    async def list_states(self) -> list[dict[str, Any]]:
        base = await self._ensure_base()
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            resp = await client.get(
                f"{base}/api/states",
                headers=self._auth_headers(),
            )
            resp.raise_for_status()
            return resp.json()

    async def call_service(
        self, domain: str, service: str, service_data: dict[str, Any]
    ) -> dict[str, Any]:
        base = await self._ensure_base()
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.post(
                f"{base}/api/services/{domain}/{service}",
                headers=self._auth_headers(),
                json=service_data,
            )
            resp.raise_for_status()
            return {"ok": True, "result": resp.json()}

    def resolved_base_public(self) -> str | None:
        return _resolved_ha_base

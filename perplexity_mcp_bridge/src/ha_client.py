from __future__ import annotations

import os
from typing import Any

import httpx


class HomeAssistantClient:
    def __init__(self, long_lived_token: str | None = None):
        self.supervisor_token = os.getenv("SUPERVISOR_TOKEN")
        self.supervisor_url = os.getenv("SUPERVISOR_API", "http://supervisor")
        self.ha_url = os.getenv("HA_URL", "http://supervisor/core")
        self.long_lived_token = long_lived_token

    def _headers(self) -> dict[str, str]:
        if self.long_lived_token:
            return {"Authorization": f"Bearer {self.long_lived_token}"}
        if self.supervisor_token:
            return {"Authorization": f"Bearer {self.supervisor_token}"}
        return {}

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(f"{self.ha_url}/api/", headers=self._headers())
                return resp.status_code == 200
        except Exception:
            return False

    async def list_states(self) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.get(f"{self.ha_url}/api/states", headers=self._headers())
            resp.raise_for_status()
            return resp.json()

    async def call_service(
        self, domain: str, service: str, service_data: dict[str, Any]
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.post(
                f"{self.ha_url}/api/services/{domain}/{service}",
                headers=self._headers(),
                json=service_data,
            )
            resp.raise_for_status()
            return {"ok": True, "result": resp.json()}


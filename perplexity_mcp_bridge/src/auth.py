from __future__ import annotations

import hmac
from fastapi import HTTPException, Request, status

from .models import AddonConfig, AddonSecrets


def _eq(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


async def enforce_auth(
    request: Request, config: AddonConfig, secrets: AddonSecrets
) -> None:
    if config.auth.bearer_token_enabled:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
        provided = auth_header.replace("Bearer ", "", 1).strip()
        expected = secrets.app_bearer_token or ""
        if not expected or not _eq(provided, expected):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    if config.auth.require_cf_access_headers:
        cf_id = request.headers.get("CF-Access-Client-Id", "")
        cf_secret = request.headers.get("CF-Access-Client-Secret", "")
        if not (config.auth.cf_access_client_id and config.auth.cf_access_client_secret):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="CF Access headers required but not configured",
            )
        if not (_eq(cf_id, config.auth.cf_access_client_id) and _eq(cf_secret, config.auth.cf_access_client_secret)):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="CF Access token mismatch",
            )


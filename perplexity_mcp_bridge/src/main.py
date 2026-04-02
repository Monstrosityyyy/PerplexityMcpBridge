from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .auth import enforce_auth
from .cloudflare import CloudflareTunnelManager
from .config_store import load_config, load_secrets, save_config, save_secrets
from .ha_client import HomeAssistantClient
from .logging_utils import mask_secret, setup_logging
from .mcp import call_tool, list_resources, list_tools, read_resource
from .models import AddonConfig, AddonSecrets, EntitySelection, ExposureMode, HealthStatus
from .policy import filtered_entities

setup_logging()
logger = logging.getLogger("perplexity_mcp_bridge")

app = FastAPI(title="Perplexity MCP Bridge")
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")

_cloudflare = CloudflareTunnelManager()
_last_sync: datetime | None = None


class WizardSavePayload(BaseModel):
    exposure_mode: ExposureMode
    selected_entities: list[str]
    cloudflare_enabled: bool
    cloudflare_mode: str = "token"
    cloudflare_tunnel_token: str | None = None
    cloudflare_hostname: str | None = None
    cloudflare_manual_args: str | None = None
    bearer_token: str | None = None
    require_cf_access_headers: bool = False
    cf_access_client_id: str | None = None
    cf_access_client_secret: str | None = None


def _current() -> tuple[AddonConfig, AddonSecrets, HomeAssistantClient]:
    cfg = load_config()
    sec = load_secrets()
    return cfg, sec, HomeAssistantClient(sec.ha_long_lived_token)


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(str(Path(__file__).parent / "static" / "index.html"))


@app.get("/api/health")
async def health() -> HealthStatus:
    cfg, sec, ha = _current()
    states = []
    connected = await ha.health()
    if connected:
        states = await ha.list_states()
    exposed = filtered_entities(cfg, states)
    return HealthStatus(
        ha_connected=connected,
        tunnel_running=_cloudflare.running,
        tunnel_hostname=cfg.cloudflare.hostname,
        auth_configured=bool(sec.app_bearer_token and cfg.auth.bearer_token_enabled),
        exposed_entity_count=len(exposed),
        last_sync=_last_sync,
    )


@app.get("/api/discover")
async def discover_entities() -> dict[str, Any]:
    global _last_sync
    cfg, _, ha = _current()
    states = await ha.list_states()
    _last_sync = datetime.now(timezone.utc)
    supported = [s for s in states if s.get("entity_id", "").split(".", 1)[0] in {"light", "switch", "climate", "cover", "sensor", "binary_sensor", "media_player"}]
    selected = {s.entity_id for s in cfg.policy.selected_entities if s.enabled}
    return {"entities": supported, "selected": list(selected)}


@app.post("/api/wizard/save")
async def wizard_save(payload: WizardSavePayload) -> dict[str, Any]:
    cfg, sec, _ = _current()
    cfg.policy.exposure_mode = payload.exposure_mode
    cfg.policy.selected_entities = [EntitySelection(entity_id=e, enabled=True) for e in payload.selected_entities]
    cfg.cloudflare.enabled = payload.cloudflare_enabled
    cfg.cloudflare.mode = payload.cloudflare_mode  # type: ignore[assignment]
    cfg.cloudflare.tunnel_token = payload.cloudflare_tunnel_token
    cfg.cloudflare.hostname = payload.cloudflare_hostname
    cfg.cloudflare.manual_args = payload.cloudflare_manual_args
    cfg.auth.require_cf_access_headers = payload.require_cf_access_headers
    cfg.auth.cf_access_client_id = payload.cf_access_client_id
    cfg.auth.cf_access_client_secret = payload.cf_access_client_secret
    if payload.bearer_token:
        sec.app_bearer_token = payload.bearer_token
    save_config(cfg)
    save_secrets(sec)
    return {"ok": True, "masked_bearer_token": mask_secret(sec.app_bearer_token)}


@app.post("/api/launch")
async def launch() -> dict[str, Any]:
    cfg, _, _ = _current()
    try:
        await _cloudflare.start(cfg, local_port=8099)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Tunnel failed: {exc}") from exc
    return {"ok": True, "tunnel_running": _cloudflare.running}


async def mcp_auth_dep(request: Request) -> None:
    cfg, sec, _ = _current()
    try:
        await enforce_auth(request, cfg, sec)
        logger.info("AUDIT auth_success source=%s", request.client.host if request.client else "unknown")
    except HTTPException:
        logger.warning("AUDIT auth_failure source=%s", request.client.host if request.client else "unknown")
        raise


@app.post("/mcp")
async def mcp_endpoint(request: Request, _: None = Depends(mcp_auth_dep)) -> dict[str, Any]:
    cfg, _, ha = _current()
    body = await request.json()
    method = body.get("method")
    req_id = body.get("id")
    params = body.get("params", {})
    try:
        if method == "initialize":
            return {"jsonrpc": "2.0", "id": req_id, "result": {"serverInfo": {"name": "perplexity-mcp-bridge", "version": "0.1.0"}}}
        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": list_tools()}}
        if method == "tools/call":
            name = params.get("name")
            args = params.get("arguments", {})
            logger.info("AUDIT tool_call tool=%s entity=%s", name, args.get("entity_id", ""))
            result = await call_tool(name, args, ha, cfg)
            return {"jsonrpc": "2.0", "id": req_id, "result": result}
        if method == "resources/list":
            resources = await list_resources(ha, cfg)
            return {"jsonrpc": "2.0", "id": req_id, "result": {"resources": resources}}
        if method == "resources/read":
            uri = params.get("uri", "")
            result = await read_resource(uri, ha, cfg)
            return {"jsonrpc": "2.0", "id": req_id, "result": {"contents": [{"uri": uri, "mimeType": "application/json", "text": str(result)}]}}
        raise ValueError(f"Unsupported MCP method: {method}")
    except PermissionError as exc:
        logger.warning("AUDIT unauthorized_action error=%s", str(exc))
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32001, "message": str(exc)}}
    except Exception as exc:
        logger.error("AUDIT tool_failure error=%s", str(exc))
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32000, "message": str(exc)}}


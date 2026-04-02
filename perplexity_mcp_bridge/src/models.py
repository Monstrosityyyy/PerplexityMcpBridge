from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


SUPPORTED_DOMAINS = {
    "light",
    "switch",
    "climate",
    "cover",
    "sensor",
    "binary_sensor",
    "media_player",
}


class ExposureMode(str, Enum):
    ALL_SUPPORTED = "all_supported"
    MANUAL = "manual"


class EntitySelection(BaseModel):
    entity_id: str
    enabled: bool = True


class CloudflareMode(str, Enum):
    TOKEN = "token"
    MANUAL = "manual"


class CloudflareConfig(BaseModel):
    enabled: bool = False
    mode: CloudflareMode = CloudflareMode.TOKEN
    tunnel_token: str | None = None
    hostname: str | None = None
    manual_args: str | None = None


class AuthConfig(BaseModel):
    bearer_token_enabled: bool = True
    bearer_token_hint: str = "Set in secrets"
    require_cf_access_headers: bool = False
    cf_access_client_id: str | None = None
    cf_access_client_secret: str | None = None


class PolicyConfig(BaseModel):
    exposure_mode: ExposureMode = ExposureMode.MANUAL
    selected_entities: list[EntitySelection] = Field(default_factory=list)


class AddonConfig(BaseModel):
    policy: PolicyConfig = Field(default_factory=PolicyConfig)
    cloudflare: CloudflareConfig = Field(default_factory=CloudflareConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    refresh_interval_seconds: int = 300


class AddonSecrets(BaseModel):
    app_bearer_token: str | None = None
    ha_long_lived_token: str | None = None

    @staticmethod
    def default_token() -> str:
        now = datetime.now(timezone.utc)
        expiry = now + timedelta(days=3650)
        return f"pmcpb-{expiry:%Y%m%d}-replace-me"


class HealthStatus(BaseModel):
    ha_connected: bool = False
    tunnel_running: bool = False
    tunnel_hostname: str | None = None
    auth_configured: bool = False
    exposed_entity_count: int = 0
    last_sync: datetime | None = None


class MCPToolCall(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


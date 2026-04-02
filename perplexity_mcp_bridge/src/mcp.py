from __future__ import annotations

from typing import Any

from .ha_client import HomeAssistantClient
from .models import AddonConfig
from .policy import filtered_entities, is_action_allowed


def list_tools() -> list[dict[str, Any]]:
    return [
        {"name": "turn_light_on", "description": "Turn on a light", "inputSchema": {"type": "object", "properties": {"entity_id": {"type": "string"}}}},
        {"name": "turn_light_off", "description": "Turn off a light", "inputSchema": {"type": "object", "properties": {"entity_id": {"type": "string"}}}},
        {
            "name": "set_light_brightness",
            "description": "Set brightness 0-255",
            "inputSchema": {"type": "object", "properties": {"entity_id": {"type": "string"}, "brightness": {"type": "integer", "minimum": 0, "maximum": 255}}, "required": ["entity_id", "brightness"]},
        },
        {"name": "toggle_switch", "description": "Toggle switch", "inputSchema": {"type": "object", "properties": {"entity_id": {"type": "string"}}, "required": ["entity_id"]}},
        {
            "name": "set_climate_temperature",
            "description": "Set target temperature",
            "inputSchema": {"type": "object", "properties": {"entity_id": {"type": "string"}, "temperature": {"type": "number"}}, "required": ["entity_id", "temperature"]},
        },
        {"name": "open_cover", "description": "Open cover", "inputSchema": {"type": "object", "properties": {"entity_id": {"type": "string"}}, "required": ["entity_id"]}},
        {"name": "close_cover", "description": "Close cover", "inputSchema": {"type": "object", "properties": {"entity_id": {"type": "string"}}, "required": ["entity_id"]}},
        {"name": "read_entity_state", "description": "Read selected entity state", "inputSchema": {"type": "object", "properties": {"entity_id": {"type": "string"}}, "required": ["entity_id"]}},
    ]


async def list_resources(ha: HomeAssistantClient, cfg: AddonConfig) -> list[dict[str, Any]]:
    states = await ha.list_states()
    allowed = filtered_entities(cfg, states)
    return [{"uri": f"ha://entity/{s['entity_id']}", "name": s["entity_id"], "mimeType": "application/json"} for s in allowed]


async def read_resource(uri: str, ha: HomeAssistantClient, cfg: AddonConfig) -> dict[str, Any]:
    entity_id = uri.replace("ha://entity/", "", 1)
    states = await ha.list_states()
    for state in filtered_entities(cfg, states):
        if state.get("entity_id") == entity_id:
            return state
    raise ValueError("Entity not exposed")


async def call_tool(name: str, arguments: dict[str, Any], ha: HomeAssistantClient, cfg: AddonConfig) -> dict[str, Any]:
    entity_id = arguments.get("entity_id", "")
    if not entity_id:
        raise ValueError("entity_id is required")

    if name == "turn_light_on":
        if not is_action_allowed(cfg, entity_id, "turn_on"):
            raise PermissionError("Action not allowed")
        return await ha.call_service("light", "turn_on", {"entity_id": entity_id})
    if name == "turn_light_off":
        if not is_action_allowed(cfg, entity_id, "turn_off"):
            raise PermissionError("Action not allowed")
        return await ha.call_service("light", "turn_off", {"entity_id": entity_id})
    if name == "set_light_brightness":
        if not is_action_allowed(cfg, entity_id, "set_brightness"):
            raise PermissionError("Action not allowed")
        brightness = int(arguments.get("brightness", -1))
        if brightness < 0 or brightness > 255:
            raise ValueError("brightness must be 0-255")
        return await ha.call_service("light", "turn_on", {"entity_id": entity_id, "brightness": brightness})
    if name == "toggle_switch":
        if not is_action_allowed(cfg, entity_id, "toggle"):
            raise PermissionError("Action not allowed")
        return await ha.call_service("switch", "toggle", {"entity_id": entity_id})
    if name == "set_climate_temperature":
        if not is_action_allowed(cfg, entity_id, "set_temperature"):
            raise PermissionError("Action not allowed")
        temp = float(arguments.get("temperature", 0))
        return await ha.call_service("climate", "set_temperature", {"entity_id": entity_id, "temperature": temp})
    if name == "open_cover":
        if not is_action_allowed(cfg, entity_id, "open"):
            raise PermissionError("Action not allowed")
        return await ha.call_service("cover", "open_cover", {"entity_id": entity_id})
    if name == "close_cover":
        if not is_action_allowed(cfg, entity_id, "close"):
            raise PermissionError("Action not allowed")
        return await ha.call_service("cover", "close_cover", {"entity_id": entity_id})
    if name == "read_entity_state":
        states = await ha.list_states()
        for item in filtered_entities(cfg, states):
            if item.get("entity_id") == entity_id:
                return {"ok": True, "result": item}
        raise PermissionError("Entity not exposed")

    raise ValueError(f"Unknown tool: {name}")


from __future__ import annotations

from typing import Any

from .models import AddonConfig, ExposureMode, SUPPORTED_DOMAINS


DOMAIN_ACTIONS: dict[str, set[str]] = {
    "light": {"turn_on", "turn_off", "set_brightness", "set_color_temp", "set_color"},
    "switch": {"turn_on", "turn_off", "toggle"},
    "climate": {"set_temperature", "set_hvac_mode"},
    "cover": {"open", "close", "stop"},
    "sensor": {"read"},
    "binary_sensor": {"read"},
    "media_player": {"read", "turn_on", "turn_off", "media_play", "media_pause"},
}


def domain_for_entity(entity_id: str) -> str:
    return entity_id.split(".", 1)[0].lower()


def is_supported(entity_id: str) -> bool:
    return domain_for_entity(entity_id) in SUPPORTED_DOMAINS


def is_entity_exposed(config: AddonConfig, entity_id: str) -> bool:
    if not is_supported(entity_id):
        return False
    if config.policy.exposure_mode == ExposureMode.ALL_SUPPORTED:
        return True
    selected = {e.entity_id for e in config.policy.selected_entities if e.enabled}
    return entity_id in selected


def is_action_allowed(config: AddonConfig, entity_id: str, action: str) -> bool:
    if not is_entity_exposed(config, entity_id):
        return False
    domain = domain_for_entity(entity_id)
    return action in DOMAIN_ACTIONS.get(domain, set())


def filtered_entities(config: AddonConfig, states: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in states:
        entity_id = item.get("entity_id", "")
        if is_entity_exposed(config, entity_id):
            out.append(item)
    return out


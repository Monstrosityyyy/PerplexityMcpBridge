from __future__ import annotations

import json
import secrets
from pathlib import Path

from .models import AddonConfig, AddonSecrets


DATA_DIR = Path("/data")
CONFIG_PATH = DATA_DIR / "config.json"
SECRETS_PATH = DATA_DIR / "secrets.json"


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> AddonConfig:
    _ensure_data_dir()
    if not CONFIG_PATH.exists():
        cfg = AddonConfig()
        save_config(cfg)
        return cfg
    return AddonConfig.model_validate_json(CONFIG_PATH.read_text(encoding="utf-8"))


def save_config(config: AddonConfig) -> None:
    _ensure_data_dir()
    CONFIG_PATH.write_text(config.model_dump_json(indent=2), encoding="utf-8")


def load_secrets() -> AddonSecrets:
    _ensure_data_dir()
    if not SECRETS_PATH.exists():
        generated = AddonSecrets(app_bearer_token=secrets.token_urlsafe(48))
        save_secrets(generated)
        return generated
    return AddonSecrets.model_validate_json(SECRETS_PATH.read_text(encoding="utf-8"))


def save_secrets(secret_config: AddonSecrets) -> None:
    _ensure_data_dir()
    SECRETS_PATH.write_text(secret_config.model_dump_json(indent=2), encoding="utf-8")


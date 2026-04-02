from __future__ import annotations

import logging
import re


SECRET_PATTERNS = [
    re.compile(r"(token[\"'\s:=]+)([A-Za-z0-9._\-]+)", re.IGNORECASE),
    re.compile(r"(authorization[\"'\s:=]+Bearer\s+)([A-Za-z0-9._\-]+)", re.IGNORECASE),
]


def mask_secret(value: str | None) -> str:
    if not value:
        return ""
    if len(value) < 6:
        return "***"
    return f"{value[:3]}***{value[-3:]}"


class SecretFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not isinstance(record.msg, str):
            return True
        text = record.msg
        for pattern in SECRET_PATTERNS:
            text = pattern.sub(r"\1***masked***", text)
        record.msg = text
        return True


def setup_logging() -> None:
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if root.handlers:
        for h in root.handlers:
            h.addFilter(SecretFilter())
    else:
        handler = logging.StreamHandler()
        handler.addFilter(SecretFilter())
        root.addHandler(handler)


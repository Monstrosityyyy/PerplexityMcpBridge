from __future__ import annotations

import asyncio
import logging
from asyncio.subprocess import Process

from .models import CloudflareMode, AddonConfig

logger = logging.getLogger(__name__)


class CloudflareTunnelManager:
    def __init__(self) -> None:
        self._proc: Process | None = None

    @property
    def running(self) -> bool:
        return self._proc is not None and self._proc.returncode is None

    async def start(self, config: AddonConfig, local_port: int) -> None:
        if not config.cloudflare.enabled:
            return
        if self.running:
            return

        args = ["cloudflared", "tunnel", "--no-autoupdate", "run"]
        if config.cloudflare.mode == CloudflareMode.TOKEN:
            if not config.cloudflare.tunnel_token:
                raise ValueError("Cloudflare tunnel token is missing")
            args.extend(["--token", config.cloudflare.tunnel_token])
        else:
            if not config.cloudflare.manual_args:
                raise ValueError("Manual cloudflared args are missing")
            args = ["cloudflared"] + config.cloudflare.manual_args.split(" ")

        logger.info("Starting cloudflared tunnel process")
        self._proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        _ = local_port

    async def stop(self) -> None:
        if not self.running:
            return
        assert self._proc is not None
        self._proc.terminate()
        await self._proc.wait()
        self._proc = None


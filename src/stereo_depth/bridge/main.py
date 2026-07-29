"""Run the Viam module, with optional WebRTC UI for browser capture."""

from __future__ import annotations

import asyncio
import logging
import os
import signal

from viam.module.module import Module

from .camera import StereoDepthCamera  # noqa: F401 - EasyResource registers on import
from .capture import CAPTURES
from .server import run_server

LOGGER = logging.getLogger(__name__)


def _webrtc_enabled() -> bool:
    value = os.environ.get("STEREO_DEPTH_WEBRTC", "").strip().lower()
    return value in {"1", "true", "yes", "on"}


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    tasks = [asyncio.create_task(Module.run_from_registry(), name="viam-module")]
    if _webrtc_enabled():
        LOGGER.info("WebRTC UI enabled on :8081 (STEREO_DEPTH_WEBRTC=1)")
        tasks.append(asyncio.create_task(run_server(), name="webrtc-server"))
    else:
        LOGGER.info("Headless USB mode (set STEREO_DEPTH_WEBRTC=1 for browser capture)")

    loop = asyncio.get_running_loop()
    stop = asyncio.Event()

    def _request_stop(*_args):
        stop.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _request_stop)
        except NotImplementedError:
            pass

    waiter = asyncio.create_task(stop.wait(), name="stop")
    done, pending = await asyncio.wait(
        [*tasks, waiter],
        return_when=asyncio.FIRST_COMPLETED,
    )
    for task in pending:
        task.cancel()
    await asyncio.gather(*pending, return_exceptions=True)
    CAPTURES.stop_all()
    for task in done:
        if task is waiter:
            continue
        exc = task.exception()
        if exc is not None:
            raise exc


if __name__ == "__main__":
    asyncio.run(main())

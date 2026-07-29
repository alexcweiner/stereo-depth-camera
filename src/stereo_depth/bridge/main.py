"""Run the Viam module and WebRTC ingress server in one process."""

import asyncio

from viam.module.module import Module

from .camera import StereoDepthCamera  # noqa: F401 - EasyResource registers on import
from .server import run_server


async def main() -> None:
    await asyncio.gather(run_server(), Module.run_from_registry())


if __name__ == "__main__":
    asyncio.run(main())

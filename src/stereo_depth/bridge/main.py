"""Run the stereo-depth Viam module (depth only; capture is stock webcam)."""

import asyncio

from viam.module.module import Module

from .camera import StereoDepthCamera  # noqa: F401 - EasyResource registers on import


async def main() -> None:
    await Module.run_from_registry()


if __name__ == "__main__":
    asyncio.run(main())

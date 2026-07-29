"""Concurrency-safe latest-frame storage shared by WebRTC and Viam."""

import asyncio
from dataclasses import dataclass
import time
from typing import Dict, Mapping, Optional


@dataclass(frozen=True)
class Frame:
    jpeg: bytes
    width: int
    height: int
    received_at: float


class FrameStore:
    def __init__(self) -> None:
        self._frames: Dict[str, Frame] = {}
        self._events: Dict[str, asyncio.Event] = {}

    def put(self, stream_id: str, jpeg: bytes, width: int, height: int) -> None:
        self._frames[stream_id] = Frame(jpeg, width, height, time.monotonic())
        self._events.setdefault(stream_id, asyncio.Event()).set()

    def get(self, stream_id: str) -> Optional[Frame]:
        return self._frames.get(stream_id)

    def snapshot(self) -> Mapping[str, Frame]:
        return dict(self._frames)

    async def wait(self, stream_id: str, timeout: float = 10) -> Frame:
        frame = self.get(stream_id)
        if frame is not None:
            return frame
        event = self._events.setdefault(stream_id, asyncio.Event())
        await asyncio.wait_for(event.wait(), timeout)
        return self._frames[stream_id]


STORE = FrameStore()

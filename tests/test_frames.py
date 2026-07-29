import asyncio
import unittest

from stereo_depth.bridge.frames import FrameStore


class FrameStoreTests(unittest.IsolatedAsyncioTestCase):
    async def test_wait_returns_next_frame(self):
        store = FrameStore()

        async def publish():
            await asyncio.sleep(0)
            store.put("cam", b"jpeg", 2560, 720)

        task = asyncio.create_task(publish())
        frame = await store.wait("cam")
        await task

        self.assertEqual(frame.jpeg, b"jpeg")
        self.assertEqual((frame.width, frame.height), (2560, 720))

    async def test_snapshot_returns_latest_frames(self):
        store = FrameStore()
        store.put("cam", b"cam", 2560, 720)

        self.assertEqual(set(store.snapshot()), {"cam"})

import time
import unittest
from unittest import mock

import numpy as np

from stereo_depth.bridge.capture import (
    CaptureRegistry,
    CaptureSettings,
    UsbCapture,
    encode_bgr_jpeg,
    parse_video_source,
)
from stereo_depth.bridge.frames import STORE

class ParseSourceTests(unittest.TestCase):
    def test_numeric_index(self):
        self.assertEqual(parse_video_source("0"), 0)
        self.assertEqual(parse_video_source("2"), 2)

    def test_device_path(self):
        self.assertEqual(parse_video_source("/dev/video0"), "/dev/video0")


class EncodeTests(unittest.TestCase):
    def test_encode_jpeg(self):
        frame = np.zeros((16, 32, 3), dtype=np.uint8)
        jpeg = encode_bgr_jpeg(frame)
        self.assertTrue(jpeg.startswith(b"\xff\xd8"))


class CaptureRegistryTests(unittest.TestCase):
    def test_upsert_starts_and_remove_stops(self):
        registry = CaptureRegistry()
        fake = mock.Mock(spec=UsbCapture)
        fake.settings = CaptureSettings(video_path="0", stream_id="cam")
        fake.running = True

        with mock.patch("stereo_depth.bridge.capture.UsbCapture", return_value=fake):
            registry.upsert(CaptureSettings(video_path="0", stream_id="cam"))
            fake.start.assert_called_once()
            registry.remove("cam")
            fake.stop.assert_called_once()

    def test_grab_loop_puts_frames(self):
        frame = np.zeros((48, 96, 3), dtype=np.uint8)
        frame[:, :] = (10, 20, 30)
        settings = CaptureSettings(video_path="0", stream_id="test-cam", width=96, height=48)
        capture = UsbCapture(settings)

        class FakeCap:
            def __init__(self):
                self.reads = 0

            def isOpened(self):
                return True

            def set(self, *_args):
                return True

            def get(self, *_args):
                return 96

            def read(self):
                self.reads += 1
                if self.reads > 3:
                    capture._stop.set()
                return True, frame.copy()

            def release(self):
                return None

        with mock.patch.object(capture, "_open", return_value=FakeCap()):
            capture.start()
            deadline = time.time() + 2
            while STORE.get("test-cam") is None and time.time() < deadline:
                time.sleep(0.01)
            capture.stop()

        stored = STORE.get("test-cam")
        self.assertIsNotNone(stored)
        self.assertEqual((stored.width, stored.height), (96, 48))
        self.assertTrue(stored.jpeg.startswith(b"\xff\xd8"))

"""Headless USB capture into the shared frame store."""

from __future__ import annotations

import asyncio
import logging
import platform
import threading
from dataclasses import dataclass
from typing import Dict, Optional, Union

import cv2
import numpy as np

from .frames import STORE

LOGGER = logging.getLogger(__name__)


def parse_video_source(video_path: str) -> Union[int, str]:
    value = video_path.strip()
    if value.isdigit():
        return int(value)
    return value


@dataclass
class CaptureSettings:
    video_path: str
    stream_id: str
    width: int = 2560
    height: int = 720
    fps: int = 30
    rotate_180: bool = False
    jpeg_quality: int = 90


class UsbCapture:
    """Grab side-by-side stereo frames from one UVC device."""

    def __init__(self, settings: CaptureSettings) -> None:
        self.settings = settings
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._cap: Optional[cv2.VideoCapture] = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.running:
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            name=f"usb-capture-{self.settings.stream_id}",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout=5)
        self._thread = None
        self._release()

    def _release(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def _open(self) -> cv2.VideoCapture:
        source = parse_video_source(self.settings.video_path)
        if platform.system() == "Linux":
            cap = cv2.VideoCapture(source, cv2.CAP_V4L2)
        else:
            cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            raise RuntimeError(f"could not open camera: {self.settings.video_path}")

        fourcc = cv2.VideoWriter_fourcc(*"MJPG")
        cap.set(cv2.CAP_PROP_FOURCC, fourcc)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.settings.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.settings.height)
        cap.set(cv2.CAP_PROP_FPS, self.settings.fps)
        return cap

    def _run(self) -> None:
        backoff = 1.0
        while not self._stop.is_set():
            try:
                self._cap = self._open()
                LOGGER.info(
                    "USB capture started stream_id=%s path=%s %sx%s",
                    self.settings.stream_id,
                    self.settings.video_path,
                    int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                    int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                )
                backoff = 1.0
                self._grab_loop()
            except Exception:
                LOGGER.exception(
                    "USB capture failed for %s; retrying in %.1fs",
                    self.settings.video_path,
                    backoff,
                )
                self._release()
                self._stop.wait(backoff)
                backoff = min(backoff * 2, 15.0)
        self._release()

    def _grab_loop(self) -> None:
        assert self._cap is not None
        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), self.settings.jpeg_quality]
        while not self._stop.is_set():
            ok, frame = self._cap.read()
            if not ok or frame is None:
                raise RuntimeError("camera read failed")
            if self.settings.rotate_180:
                frame = cv2.rotate(frame, cv2.ROTATE_180)
            ok, encoded = cv2.imencode(".jpg", frame, encode_params)
            if not ok:
                continue
            height, width = frame.shape[:2]
            STORE.put(self.settings.stream_id, encoded.tobytes(), width, height)


class CaptureRegistry:
    """One USB capture worker per stream_id."""

    def __init__(self) -> None:
        self._captures: Dict[str, UsbCapture] = {}
        self._lock = threading.Lock()

    def upsert(self, settings: CaptureSettings) -> None:
        with self._lock:
            existing = self._captures.get(settings.stream_id)
            if existing is not None:
                same = (
                    existing.settings.video_path == settings.video_path
                    and existing.settings.width == settings.width
                    and existing.settings.height == settings.height
                    and existing.settings.fps == settings.fps
                    and existing.settings.rotate_180 == settings.rotate_180
                    and existing.running
                )
                if same:
                    return
                existing.stop()
            capture = UsbCapture(settings)
            self._captures[settings.stream_id] = capture
            capture.start()

    def remove(self, stream_id: str) -> None:
        with self._lock:
            capture = self._captures.pop(stream_id, None)
        if capture is not None:
            capture.stop()

    def stop_all(self) -> None:
        with self._lock:
            captures = list(self._captures.values())
            self._captures.clear()
        for capture in captures:
            capture.stop()


CAPTURES = CaptureRegistry()


def encode_bgr_jpeg(frame: np.ndarray, quality: int = 90) -> bytes:
    ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        raise RuntimeError("could not encode jpeg")
    return encoded.tobytes()


async def wait_forever() -> None:
    await asyncio.Event().wait()

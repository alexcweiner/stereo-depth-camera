import unittest
from types import SimpleNamespace
from unittest import mock

import cv2
import numpy as np

from stereo_depth.bridge.camera import StereoDepthCamera
from viam.media.video import CameraMimeType, NamedImage
from viam.proto.common import ResourceName, ResponseMetadata
from viam.components.camera import Camera


def stereo_jpeg() -> bytes:
    left = np.zeros((64, 96, 3), dtype=np.uint8)
    cv2.rectangle(left, (35, 15), (70, 50), (255, 255, 255), -1)
    right = np.zeros_like(left)
    cv2.rectangle(right, (27, 15), (62, 50), (255, 255, 255), -1)
    ok, encoded = cv2.imencode(".jpg", np.hstack((left, right)))
    assert ok
    return encoded.tobytes()


def _field_string(value: str):
    return SimpleNamespace(string_value=value)


def _field_number(value: float):
    return SimpleNamespace(number_value=value)


class ValidateConfigTests(unittest.TestCase):
    def test_source_dependency(self):
        config = SimpleNamespace(
            attributes=SimpleNamespace(
                fields={
                    "source": _field_string("rig"),
                    "focal_px": _field_number(700),
                    "baseline_mm": _field_number(60),
                }
            )
        )
        required, optional = StereoDepthCamera.validate_config(config)
        self.assertEqual(required, ["rig"])
        self.assertEqual(optional, [])

    def test_left_right_dependencies(self):
        config = SimpleNamespace(
            attributes=SimpleNamespace(
                fields={
                    "left_camera": _field_string("cam-left"),
                    "right_camera": _field_string("cam-right"),
                }
            )
        )
        required, _optional = StereoDepthCamera.validate_config(config)
        self.assertEqual(required, ["cam-left", "cam-right"])


class DepthCameraTests(unittest.IsolatedAsyncioTestCase):
    async def test_get_images_from_sbs_source(self):
        jpeg = stereo_jpeg()
        source = mock.AsyncMock(spec=Camera)
        source.get_images.return_value = (
            [NamedImage("rig", jpeg, CameraMimeType.JPEG)],
            ResponseMetadata(),
        )

        cam = StereoDepthCamera("cam-depth")
        cam.source_name = "rig"
        cam.source = source
        cam.focal_px = 100
        cam.baseline_mm = 60

        images, _meta = await cam.get_images()
        names = [image.name for image in images]
        self.assertEqual(names, ["color", "depth"])
        self.assertTrue(images[0].data.startswith(b"\xff\xd8"))
        self.assertTrue(images[1].data.startswith(b"\xff\xd8"))

        pcd, mime = await cam.get_point_cloud()
        self.assertTrue(pcd.startswith(b"# .PCD v0.7"))
        self.assertIn("pcd", mime)

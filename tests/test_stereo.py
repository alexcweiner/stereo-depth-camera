import unittest

import cv2
import numpy as np

from stereo_depth.bridge.stereo import depth_preview, point_cloud_pcd, split_stereo


def stereo_jpeg() -> bytes:
    left = np.zeros((64, 96, 3), dtype=np.uint8)
    cv2.rectangle(left, (35, 15), (70, 50), (255, 255, 255), -1)
    right = np.zeros_like(left)
    cv2.rectangle(right, (27, 15), (62, 50), (255, 255, 255), -1)
    ok, encoded = cv2.imencode(".jpg", np.hstack((left, right)))
    assert ok
    return encoded.tobytes()


class StereoTests(unittest.TestCase):
    def test_split_stereo(self) -> None:
        left, right = split_stereo(stereo_jpeg())
        self.assertEqual(left.shape, (64, 96, 3))
        self.assertEqual(right.shape, (64, 96, 3))

    def test_point_cloud_is_pcd(self) -> None:
        pcd = point_cloud_pcd(stereo_jpeg(), focal_px=100, baseline_mm=60, stride=2)
        self.assertTrue(pcd.startswith(b"# .PCD v0.7"))
        self.assertIn(b"DATA ascii\n", pcd)

    def test_depth_preview_is_jpeg(self) -> None:
        preview = depth_preview(stereo_jpeg())
        self.assertTrue(preview.startswith(b"\xff\xd8"))

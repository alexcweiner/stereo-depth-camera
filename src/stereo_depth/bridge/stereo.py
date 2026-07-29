"""Stereo depth from a side-by-side (or left/right) RGB pair."""

from __future__ import annotations

import cv2
import numpy as np


def decode_bgr(jpeg: bytes) -> np.ndarray:
    image = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("could not decode image")
    return image


def split_stereo(jpeg: bytes) -> tuple[np.ndarray, np.ndarray]:
    image = decode_bgr(jpeg)
    if image.shape[1] < 2:
        raise ValueError("stereo frame too narrow to split")
    midpoint = image.shape[1] // 2
    return image[:, :midpoint], image[:, midpoint : midpoint * 2]


def disparity_map(
    left: np.ndarray,
    right: np.ndarray,
    max_eye_width: int = 640,
) -> tuple[np.ndarray, np.ndarray, float]:
    if left.shape[:2] != right.shape[:2]:
        right = cv2.resize(right, (left.shape[1], left.shape[0]), interpolation=cv2.INTER_AREA)
    scale = min(1.0, max_eye_width / left.shape[1])
    if scale < 1.0:
        size = (round(left.shape[1] * scale), round(left.shape[0] * scale))
        left = cv2.resize(left, size, interpolation=cv2.INTER_AREA)
        right = cv2.resize(right, size, interpolation=cv2.INTER_AREA)

    left_gray = cv2.cvtColor(left, cv2.COLOR_BGR2GRAY)
    right_gray = cv2.cvtColor(right, cv2.COLOR_BGR2GRAY)
    num_disparities = max(16, min(128, ((left_gray.shape[1] - 8) // 16) * 16))
    matcher = cv2.StereoSGBM_create(
        minDisparity=0,
        numDisparities=num_disparities,
        blockSize=7,
        P1=8 * 7 * 7,
        P2=32 * 7 * 7,
        disp12MaxDiff=2,
        uniquenessRatio=8,
        speckleWindowSize=80,
        speckleRange=2,
    )
    disparity = matcher.compute(left_gray, right_gray).astype(np.float32) / 16.0
    return left, disparity, scale


def depth_preview_bgr(left: np.ndarray, right: np.ndarray) -> bytes:
    _left, disparity, _scale = disparity_map(left, right)
    valid = disparity > 0
    preview = np.zeros((*disparity.shape, 3), dtype=np.uint8)
    if np.any(valid):
        normalized = np.zeros_like(disparity, dtype=np.uint8)
        normalized[valid] = np.clip(disparity[valid] * 2, 0, 255).astype(np.uint8)
        preview = cv2.applyColorMap(normalized, cv2.COLORMAP_TURBO)
        preview[~valid] = 0
    ok, encoded = cv2.imencode(".jpg", preview, [cv2.IMWRITE_JPEG_QUALITY, 88])
    if not ok:
        raise RuntimeError("could not encode depth preview")
    return encoded.tobytes()


def depth_preview(jpeg: bytes) -> bytes:
    left, right = split_stereo(jpeg)
    return depth_preview_bgr(left, right)


def point_cloud_pcd_bgr(
    left: np.ndarray,
    right: np.ndarray,
    *,
    focal_px: float,
    baseline_mm: float,
    stride: int = 4,
    max_depth_mm: float = 10_000,
) -> bytes:
    _left, disparity, scale = disparity_map(left, right)
    focal = focal_px * scale
    height, width = disparity.shape
    yy, xx = np.mgrid[0:height:stride, 0:width:stride]
    sampled = disparity[::stride, ::stride]
    valid = sampled > 0.5
    z = np.zeros_like(sampled, dtype=np.float32)
    z[valid] = focal * baseline_mm / sampled[valid]
    valid &= (z > 0) & (z <= max_depth_mm)
    z = z[valid]
    x = (xx[valid] - width / 2) * z / focal
    y = (yy[valid] - height / 2) * z / focal
    points = np.column_stack((x, y, z))

    header = (
        "# .PCD v0.7\nVERSION 0.7\nFIELDS x y z\n"
        "SIZE 4 4 4\nTYPE F F F\nCOUNT 1 1 1\n"
        f"WIDTH {len(points)}\nHEIGHT 1\nVIEWPOINT 0 0 0 1 0 0 0\n"
        f"POINTS {len(points)}\nDATA ascii\n"
    )
    body = "".join(f"{x:.3f} {y:.3f} {z:.3f}\n" for x, y, z in points)
    return (header + body).encode("ascii")


def point_cloud_pcd(
    jpeg: bytes,
    *,
    focal_px: float,
    baseline_mm: float,
    stride: int = 4,
    max_depth_mm: float = 10_000,
) -> bytes:
    left, right = split_stereo(jpeg)
    return point_cloud_pcd_bgr(
        left,
        right,
        focal_px=focal_px,
        baseline_mm=baseline_mm,
        stride=stride,
        max_depth_mm=max_depth_mm,
    )

"""Viam camera that estimates depth from a stock SBS webcam (or L/R pair)."""

from __future__ import annotations

from typing import Mapping, Optional, Sequence, Tuple, Union, cast

import cv2
from viam.components.camera import Camera
from viam.media.video import CameraMimeType, NamedImage
from viam.proto.common import ResourceName, ResponseMetadata
from viam.proto.component.camera import GetPropertiesResponse
from viam.resource.base import ResourceBase
from viam.resource.easy_resource import EasyResource
from viam.resource.types import Model, ModelFamily

from .stereo import (
    decode_bgr,
    depth_preview,
    depth_preview_bgr,
    point_cloud_pcd,
    point_cloud_pcd_bgr,
    split_stereo,
)


def _number(fields, key: str, default: float) -> float:
    value = fields.get(key)
    if value is None or value.number_value <= 0:
        return default
    return value.number_value


def _string(fields, key: str) -> str:
    value = fields.get(key)
    if value is None:
        return ""
    return value.string_value.strip()


class StereoDepthCamera(Camera, EasyResource):
    """Depth estimator only. Capture is a normal Viam `webcam` (+ optional crops)."""

    MODEL = Model(ModelFamily("local", "stereo-depth"), "camera")

    def __init__(self, name: str):
        super().__init__(name)
        self.source_name = ""
        self.left_name = ""
        self.right_name = ""
        self.source: Optional[Camera] = None
        self.left: Optional[Camera] = None
        self.right: Optional[Camera] = None
        self.focal_px = 700.0
        self.baseline_mm = 60.0

    @classmethod
    def new(cls, config, dependencies: Mapping[ResourceName, ResourceBase]):
        camera = cls(config.name)
        camera.reconfigure(config, dependencies)
        return camera

    @classmethod
    def validate_config(cls, config):
        fields = config.attributes.fields
        source = _string(fields, "source")
        left = _string(fields, "left_camera")
        right = _string(fields, "right_camera")
        if source:
            return [source], []
        if left and right:
            return [left, right], []
        raise ValueError(
            "set source (SBS webcam) or left_camera + right_camera (two eye cameras)"
        )

    def reconfigure(self, config, dependencies: Mapping[ResourceName, ResourceBase]):
        fields = config.attributes.fields
        self.source_name = _string(fields, "source")
        self.left_name = _string(fields, "left_camera")
        self.right_name = _string(fields, "right_camera")
        self.focal_px = _number(fields, "focal_px", 700.0)
        self.baseline_mm = _number(fields, "baseline_mm", 60.0)

        self.source = None
        self.left = None
        self.right = None
        for resource_name, dep in dependencies.items():
            if resource_name.name == self.source_name:
                self.source = cast(Camera, dep)
            elif resource_name.name == self.left_name:
                self.left = cast(Camera, dep)
            elif resource_name.name == self.right_name:
                self.right = cast(Camera, dep)

        if self.source_name and self.source is None:
            raise ValueError(f"missing dependency: {self.source_name}")
        if self.left_name and self.left is None:
            raise ValueError(f"missing dependency: {self.left_name}")
        if self.right_name and self.right is None:
            raise ValueError(f"missing dependency: {self.right_name}")

    async def _eyes(self) -> tuple[bytes, Optional[bytes]]:
        """Return (color_jpeg, optional separate right jpeg)."""
        if self.source is not None:
            images, _ = await self.source.get_images()
            if not images:
                raise RuntimeError(f"{self.source_name} returned no images")
            return images[0].data, None

        assert self.left is not None and self.right is not None
        left_images, _ = await self.left.get_images()
        right_images, _ = await self.right.get_images()
        if not left_images or not right_images:
            raise RuntimeError("left/right cameras returned no images")
        return left_images[0].data, right_images[0].data

    async def get_images(
        self,
        *,
        filter_source_names: Optional[Sequence[str]] = None,
        extra=None,
        timeout=None,
        **kwargs,
    ) -> Tuple[Sequence[NamedImage], ResponseMetadata]:
        color_jpeg, right_jpeg = await self._eyes()
        if right_jpeg is None:
            depth_jpeg = depth_preview(color_jpeg)
            left, _right = split_stereo(color_jpeg)
            ok, encoded = cv2.imencode(".jpg", left, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
            if not ok:
                raise RuntimeError("could not encode left eye")
            color_out = encoded.tobytes()
        else:
            left = decode_bgr(color_jpeg)
            right = decode_bgr(right_jpeg)
            depth_jpeg = depth_preview_bgr(left, right)
            color_out = color_jpeg

        images = [
            NamedImage("color", color_out, CameraMimeType.JPEG),
            NamedImage("depth", depth_jpeg, CameraMimeType.JPEG),
        ]
        if filter_source_names:
            images = [image for image in images if image.name in filter_source_names]
        return images, ResponseMetadata()

    async def get_properties(self, *, timeout=None, **kwargs) -> GetPropertiesResponse:
        return GetPropertiesResponse(
            supports_pcd=True,
            mime_types=[CameraMimeType.JPEG, CameraMimeType.PCD],
        )

    async def get_point_cloud(
        self, *, extra=None, timeout=None, **kwargs
    ) -> Tuple[Union[bytes, bytearray], str]:
        color_jpeg, right_jpeg = await self._eyes()
        if right_jpeg is None:
            pcd = point_cloud_pcd(
                color_jpeg,
                focal_px=self.focal_px,
                baseline_mm=self.baseline_mm,
            )
        else:
            pcd = point_cloud_pcd_bgr(
                decode_bgr(color_jpeg),
                decode_bgr(right_jpeg),
                focal_px=self.focal_px,
                baseline_mm=self.baseline_mm,
            )
        return pcd, CameraMimeType.PCD

"""Viam camera resource backed by the most recent browser frame."""

from typing import Mapping, Optional, Sequence, Tuple, Union

from viam.components.camera import Camera
from viam.media.video import CameraMimeType, NamedImage
from viam.proto.common import ResponseMetadata
from viam.proto.component.camera import GetPropertiesResponse
from viam.resource.base import ResourceBase
from viam.resource.easy_resource import EasyResource
from viam.resource.types import Model, ModelFamily

from .frames import STORE
from .stereo import depth_preview, point_cloud_pcd


class StereoDepthCamera(Camera, EasyResource):
    MODEL = Model(ModelFamily("local", "stereo-depth"), "camera")

    def __init__(self, name: str):
        super().__init__(name)
        self.stream_id = name
        self.focal_px = 700.0
        self.baseline_mm = 60.0

    @classmethod
    def new(cls, config, dependencies: Mapping[str, ResourceBase]):
        camera = cls(config.name)
        camera.reconfigure(config, dependencies)
        return camera

    @classmethod
    def validate_config(cls, config):
        stream_id = config.attributes.fields.get("stream_id")
        if stream_id is None or not stream_id.string_value:
            raise ValueError("stream_id is required")
        return [], []

    def reconfigure(self, config, dependencies: Mapping[str, ResourceBase]):
        self.stream_id = config.attributes.fields["stream_id"].string_value
        focal = config.attributes.fields.get("focal_px")
        baseline = config.attributes.fields.get("baseline_mm")
        self.focal_px = focal.number_value if focal and focal.number_value > 0 else 700.0
        self.baseline_mm = baseline.number_value if baseline and baseline.number_value > 0 else 60.0

    async def get_images(
        self,
        *,
        filter_source_names: Optional[Sequence[str]] = None,
        extra=None,
        timeout=None,
        **kwargs,
    ) -> Tuple[Sequence[NamedImage], ResponseMetadata]:
        frame = await STORE.wait(self.stream_id)
        images = [
            NamedImage(self.stream_id, frame.jpeg, CameraMimeType.JPEG),
            NamedImage(f"{self.stream_id}-depth", depth_preview(frame.jpeg), CameraMimeType.JPEG),
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
        frame = await STORE.wait(self.stream_id)
        pcd = point_cloud_pcd(
            frame.jpeg,
            focal_px=self.focal_px,
            baseline_mm=self.baseline_mm,
        )
        return pcd, CameraMimeType.PCD

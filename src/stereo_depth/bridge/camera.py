"""Viam camera resource backed by USB capture or browser WebRTC frames."""

from typing import Mapping, Optional, Sequence, Tuple, Union

from viam.components.camera import Camera
from viam.media.video import CameraMimeType, NamedImage
from viam.proto.common import ResponseMetadata
from viam.proto.component.camera import GetPropertiesResponse
from viam.resource.base import ResourceBase
from viam.resource.easy_resource import EasyResource
from viam.resource.types import Model, ModelFamily

from .capture import CAPTURES, CaptureSettings
from .frames import STORE
from .stereo import depth_preview, point_cloud_pcd


def _number(fields, key: str, default: float) -> float:
    value = fields.get(key)
    if value is None or value.number_value <= 0:
        return default
    return value.number_value


def _bool(fields, key: str, default: bool = False) -> bool:
    value = fields.get(key)
    if value is None:
        return default
    return bool(value.bool_value)


class StereoDepthCamera(Camera, EasyResource):
    MODEL = Model(ModelFamily("local", "stereo-depth"), "camera")

    def __init__(self, name: str):
        super().__init__(name)
        self.stream_id = name
        self.video_path = ""
        self.focal_px = 700.0
        self.baseline_mm = 60.0
        self.width_px = 2560
        self.height_px = 720
        self.frame_rate = 30
        self.rotate_180 = False

    @classmethod
    def new(cls, config, dependencies: Mapping[str, ResourceBase]):
        camera = cls(config.name)
        camera.reconfigure(config, dependencies)
        return camera

    @classmethod
    def validate_config(cls, config):
        fields = config.attributes.fields
        stream_id = fields.get("stream_id")
        video_path = fields.get("video_path")
        has_stream = stream_id is not None and bool(stream_id.string_value)
        has_video = video_path is not None and bool(video_path.string_value)
        if not has_stream and not has_video:
            raise ValueError("video_path (headless USB) or stream_id (WebRTC) is required")
        return [], []

    def reconfigure(self, config, dependencies: Mapping[str, ResourceBase]):
        fields = config.attributes.fields
        stream = fields.get("stream_id")
        video = fields.get("video_path")
        self.video_path = video.string_value.strip() if video and video.string_value else ""
        self.stream_id = (
            stream.string_value.strip()
            if stream and stream.string_value
            else (self.video_path and config.name) or config.name
        )
        self.focal_px = _number(fields, "focal_px", 700.0)
        self.baseline_mm = _number(fields, "baseline_mm", 60.0)
        self.width_px = int(_number(fields, "width_px", 2560))
        self.height_px = int(_number(fields, "height_px", 720))
        self.frame_rate = int(_number(fields, "frame_rate", 30))
        self.rotate_180 = _bool(fields, "rotate_180", False)

        if self.video_path:
            CAPTURES.upsert(
                CaptureSettings(
                    video_path=self.video_path,
                    stream_id=self.stream_id,
                    width=self.width_px,
                    height=self.height_px,
                    fps=self.frame_rate,
                    rotate_180=self.rotate_180,
                )
            )
        else:
            CAPTURES.remove(self.stream_id)

    async def close(self):
        if self.video_path:
            CAPTURES.remove(self.stream_id)
        await super().close()

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

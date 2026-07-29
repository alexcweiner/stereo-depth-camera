# stereo-depth-camera

Viam module for one **GXIVISION** dual-lens USB camera (UVC, side-by-side MJPEG ~2560×720).

Opens the device with OpenCV, splits left/right, runs `StereoSGBM`, exposes color + depth preview + PCD on a normal Viam camera. Headless — no browser.

## Hardware

GXIVISION stereo USB module (and identical clones): one `/dev/video*` device, synchronized L|R in a single SBS frame, ~60 mm baseline.

```sh
# Linux / Pi
v4l2-ctl --list-devices
ls /dev/v4l/by-id/

# macOS
uv run python bin/list-cameras
```

## Run

1. Create a machine on [app.viam.com](https://app.viam.com).
2. Paste [`configs/single-camera.json`](configs/single-camera.json); set `video_path` (`0` on Mac, `/dev/video0` or by-id on Pi).
3. Save machine credentials as `local/viam.json`.

**Pi / Linux (Docker):**

```sh
cp .env.example .env   # set CAMERA_DEVICE
docker compose -f compose.yaml -f compose.linux.yaml up --build
```

**macOS (native — Docker won't see the camera):**

```sh
uv sync --extra bridge
# point modules[].executable_path at this repo's bin/run-module
viam-server -config local/viam.json -no-tls
```

CONTROL tab: `cam` (SBS + depth), `cam-left` / `cam-right` (crops).

## Attributes

| attr | default | |
|---|---|---|
| `video_path` | required | `0`, `/dev/video0`, or by-id |
| `width_px` / `height_px` | 2560 / 720 | |
| `frame_rate` | 30 | |
| `baseline_mm` | 60 | |
| `focal_px` | 700 | rough; for PCD scale |
| `rotate_180` | false | |

Depth is uncalibrated software stereo. Fine for near-field demos; not RealSense.

## Dev

```sh
uv sync --extra bridge
uv run python -m unittest discover -s tests -v
```

Optional browser capture: [`configs/single-camera-webrtc.json`](configs/single-camera-webrtc.json) + `STEREO_DEPTH_WEBRTC=1`.

## License

MIT

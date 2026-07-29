# Cheap USB stereo → depth camera for Viam

Turn a ~$40–90 dual-lens USB module into a Viam camera that serves **color, a depth preview, and a point cloud** — no RealSense, no Orbbec SDK, no proprietary driver.

**Default mode is headless USB capture** (works on a Mac or Raspberry Pi with no browser). Optional WebRTC/browser capture remains available when you want it.

<p align="center">
  <img src="docs/assets/hero.jpg" alt="Side-by-side stereo frame and software depth preview" width="900" />
</p>

<p align="center">
  <img src="docs/assets/demo-compare.jpg" alt="Left eye versus software depth colormap" width="900" />
</p>

## Why this exists

Hardware depth cameras are great when you need them — and expensive, power-hungry, or awkward when you don’t. Dual-lens USB modules already ship synchronized stereo in one MJPEG stream. What’s missing is a small, boring bridge into a robot stack.

This repo is that bridge for [Viam](https://www.viam.com): plug in the camera, start the module, and you get `GetImages` + `GetPointCloud` like any other depth camera.

## What you get

| Resource | What it is |
|---|---|
| `cam` | Custom module: color JPEG + depth colormap + PCD |
| `cam-left` / `cam-right` | Built-in Viam `transform` crops of each eye |

```text
USB dual-lens module
        │  side-by-side MJPEG (e.g. 2560×720)
        ▼
 OpenCV capture (headless)  ──►  Python module  ──►  viam-server
        │                              │
   optional Chrome WebRTC      StereoSGBM depth + PCD
```

## Hardware

Any UVC dual-lens module that outputs a **side-by-side** frame works. Tested pattern:

- **GXIVISION** (and clones): MJPEG `2560×720@30`, synchronized left/right in one USB device
- ~60 mm baseline (many boards are adjustable)
- Wide / fisheye lenses are common — depth is approximate until you calibrate

Search terms: `dual lens USB camera 2560x720`, `3D stereo USB module synchronized`.

### Find the camera path

**Raspberry Pi / Linux**

```sh
v4l2-ctl --list-devices
ls /dev/v4l/by-id/
v4l2-ctl --list-formats-ext --device /dev/video0
```

Prefer a stable `/dev/v4l/by-id/...` path in config.

**macOS**

```sh
uv run python bin/list-cameras
system_profiler SPCameraDataType
```

OpenCV usually wants a numeric index (`0`, `1`, …). Grant **Camera** permission to Terminal (or whatever runs the module) under System Settings → Privacy & Security → Camera.

## Quick start (headless)

### 1. Viam machine

1. Create a machine at [app.viam.com](https://app.viam.com).
2. **CONFIGURE → JSON** → paste [`configs/single-camera.json`](configs/single-camera.json).
3. Set `attributes.video_path` to your device (`0` on Mac, or `/dev/video0` / by-id on Pi).
4. Save. Download private credentials to `local/viam.json` (gitignored).

### 2a. Raspberry Pi / Linux (Docker + USB passthrough)

```sh
cp .env.example .env   # set CAMERA_DEVICE if needed
docker compose -f compose.yaml -f compose.linux.yaml up --build
```

No browser. The module opens the USB camera itself.

### 2b. macOS (native — recommended for headless)

Docker Desktop cannot reliably pass Mac cameras through. Run locally:

```sh
# install viam-server once (from the machine setup page / brew tap)
uv sync --extra bridge

# point Viam at this module: executable_path =
#   /ABS/PATH/TO/stereo-depth-camera/bin/run-module
# and ensure that script's python can import stereo_depth (uv run / venv).

viam-server -config local/viam.json -no-tls
```

For a local module path without Docker, change the machine config module block to something like:

```json
"modules": [{
  "name": "stereo-depth",
  "type": "local",
  "executable_path": "/Users/YOU/Projects/stereo-depth-camera/bin/run-module"
}]
```

`bin/run-module` already prefers `uv run` / `.venv` when present.
### 3. Verify

In the machine **CONTROL** tab, open `cam`, then `cam-left` / `cam-right`. Depth + PCD come from `cam`.

## Optional: browser WebRTC capture

Use this if USB open fails on macOS permissions, or you prefer Chrome as the capture process.

1. Paste [`configs/single-camera-webrtc.json`](configs/single-camera-webrtc.json) (sets `STEREO_DEPTH_WEBRTC=1`).
2. `docker compose up --build` (or run the module with that env var).
3. Open [http://localhost:8081](http://localhost:8081), enable the camera, **Start streaming**, leave the tab open.

## Try the depth math without a camera

```sh
uv sync --extra bridge
uv run python -m unittest discover -s tests -v
```

## Module attributes (`local:stereo-depth:camera`)

| Attribute | Default | Meaning |
|---|---|---|
| `video_path` | — | Headless USB source: `0`, `/dev/video0`, or by-id path |
| `stream_id` | camera name | Frame store key (also used by WebRTC) |
| `width_px` / `height_px` | `2560` / `720` | Requested capture size |
| `frame_rate` | `30` | Requested FPS |
| `rotate_180` | `false` | Rotate frames if the mount is upside down |
| `focal_px` | `700` | Approximate focal length for PCD |
| `baseline_mm` | `60` | Stereo baseline in millimeters |

Set **either** `video_path` (headless) **or** omit it and use WebRTC with `stream_id`.

Env:

| Variable | Default | Meaning |
|---|---|---|
| `STEREO_DEPTH_WEBRTC` | `0` | `1` enables the browser UI on port 8081 |

## How depth is computed

1. Grab the latest side-by-side JPEG (USB or WebRTC).
2. Split left/right halves.
3. Downscale and run `cv2.StereoSGBM`.
4. Publish a turbo colormap as `cam-depth`.
5. Reproject disparities with `focal_px` / `baseline_mm` into ASCII PCD.

This is **software stereo**, not ToF / structured light. Near-field (~2–4 m) is the useful range; wide fisheyes without calibration get noisy farther out.

## Honest limitations

- No fisheye rectification yet.
- Depth preview is a colormap JPEG, not a raw depth MIME.
- Docker on macOS is a poor fit for USB cameras — use native headless or WebRTC.
- Not a replacement for calibrated industrial stereo.

## License

MIT — see [LICENSE](LICENSE).

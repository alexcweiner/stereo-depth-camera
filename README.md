# stereo-depth-camera

Software stereo depth for a **GXIVISION** dual-lens USB camera on [Viam](https://www.viam.com).

Stock Viam opens the camera and crops the eyes. This module only estimates depth.

| Component | Model | Role |
|---|---|---|
| `rig` | `webcam` | SBS UVC stream (~2560×720 MJPEG) |
| `cam-left` / `cam-right` | `transform` | eye crops |
| `cam-depth` | `local:stereo-depth:camera` | StereoSGBM → color + depth preview + PCD |

## Run

1. Paste [`configs/single-camera.json`](configs/single-camera.json) into the machine config.
2. Set `rig.attributes.video_path` (`0` on Mac, `/dev/video0` or by-id on Pi).
3. Point `modules[].executable_path` at `bin/run-module` (Docker image already does).
4. Save credentials as `local/viam.json`.

**Pi / Linux**

```sh
cp .env.example .env
docker compose -f compose.yaml -f compose.linux.yaml up --build
```

**macOS** — run `viam-server` natively; Docker won't see the camera. `uv sync --extra module` then set `executable_path` to this repo's `bin/run-module`.

## Module attributes

| attr | |
|---|---|
| `source` | SBS webcam name (preferred for this board — one frame, synced eyes) |
| `left_camera` + `right_camera` | alternative: two eye cameras |
| `focal_px` / `baseline_mm` | PCD scale (defaults 700 / 60) |

Swap StereoSGBM later for an ML depth model in the same camera slot.

## Dev

```sh
uv sync --extra module
uv run python -m unittest discover -s tests -v
```

## License

MIT

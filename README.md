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

## Calibration

Unrectified 180° eyes make StereoSGBM noisy. You need **intrinsics** (each eye) and **extrinsics** (left↔right). Viam can capture frames; the solve is local OpenCV (`cv2.fisheye`).

Most people have an old tablet and no printer. Run a checkerboard server on the
laptop; open the URL on the phone/tablet (same Wi‑Fi):

```sh
uv run python -m stereo_depth.checkerboard
# phone: http://<laptop-lan-ip>:8765/
```

Set squares across/down, go fullscreen, keep it **close**, move it around a lot
so corners reach the outer FOV. Measure one square in **mm** with a ruler after
it’s displayed (don’t trust the on-screen label alone).

**Capture (both eyes must see the whole board every frame)**

| | Target |
|---|---|
| Pairs | **25–40** good detections (shoot ~50; throw away misses) |
| Distance | mostly **0.3–1.0 m**; a few at **~1.5–2 m** |
| Coverage | center, edges, corners; tilt ±30–45°; roll a bit |
| Per pair | one SBS / left+right grab — same instant |

Workflow: intrinsics per eye from that set → stereo extrinsics on the same pairs → `stereoRectify` maps → load into `cam-depth` before matching. Without that, treat depth as a rough near-field demo only.

## Dev

```sh
uv sync --extra module
uv run python -m unittest discover -s tests -v
```

## License

MIT

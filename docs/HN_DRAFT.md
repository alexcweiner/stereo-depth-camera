# Hacker News draft (optional)

**Title ideas**

1. Show HN: Turn a $40 dual-lens USB webcam into a Viam depth camera
2. Show HN: Software stereo depth from a side-by-side UVC camera for robots
3. Cheap USB stereo modules already output synchronized L|R — here's a Viam bridge

**Opening paragraph**

Hardware depth cameras (RealSense, Orbbec, OAK) are excellent and also often overkill.
There is a whole class of ~$40–90 dual-lens USB modules that already ship a synchronized
side-by-side stereo frame as a normal UVC webcam. This project is a small Viam module that
takes that stream (via Chrome WebRTC on macOS-friendly path), runs OpenCV StereoSGBM, and
exposes color + depth preview + point cloud like any other camera component.

**What to emphasize**

- One clone / compose / browser step
- Works with commodity hardware people can buy today
- Honest limits (near-field, approximate, no fisheye calib yet)
- Link the repo and a screenshot of CONTROL / depth preview

**What not to overclaim**

- Not calibrated cm-accurate depth
- Not a 360 stitcher (that's a different problem)

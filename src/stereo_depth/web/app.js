const STREAM_ID = "cam";
const outboundSize = {width: 960, height: 270};

const status = document.querySelector("#status");
const rotate = document.querySelector("#rotate");
const deviceSelect = document.querySelector("#device");
const preview = document.querySelector("#preview");
const eyeLeft = document.querySelector("#eye-left");
const eyeRight = document.querySelector("#eye-right");
const startButton = document.querySelector("#start");
const stopButton = document.querySelector("#stop");

let discoveredDevices = [];
let selectedDeviceId = "";
let previewStream = null;
let outboundStream = null;
let peer = null;
let animationFrame = 0;
let localCanvas = null;

function looksLikeExtraCamera(label) {
  return /facetime|iphone|continuity|desk view|virtual|obs|snap\s*camera|camo|droidcam/i.test(label || "");
}

function preferredDevice(devices) {
  return devices.find(device => !looksLikeExtraCamera(device.label)) || devices[0] || null;
}

function drawEyes(source) {
  const half = Math.floor(source.width / 2);
  const leftCtx = eyeLeft.getContext("2d", {alpha: false});
  const rightCtx = eyeRight.getContext("2d", {alpha: false});
  leftCtx.drawImage(source, 0, 0, half, source.height, 0, 0, eyeLeft.width, eyeLeft.height);
  rightCtx.drawImage(source, half, 0, half, source.height, 0, 0, eyeRight.width, eyeRight.height);
}

function stopPreviewTracks() {
  if (previewStream) {
    previewStream.getTracks().forEach(track => track.stop());
    previewStream = null;
  }
  preview.srcObject = null;
  if (animationFrame) cancelAnimationFrame(animationFrame);
  animationFrame = 0;
  localCanvas = null;
}

async function openPreview(deviceId) {
  stopPreviewTracks();
  if (!deviceId) {
    startButton.disabled = true;
    return;
  }
  previewStream = await navigator.mediaDevices.getUserMedia({
    video: {
      deviceId: {exact: deviceId},
      width: {ideal: 2560},
      height: {ideal: 720},
      frameRate: {ideal: 30},
    },
    audio: false,
  });
  preview.srcObject = previewStream;
  await preview.play();
  if (!preview.videoWidth) {
    await new Promise(resolve => preview.addEventListener("loadedmetadata", resolve, {once: true}));
  }
  localCanvas = document.createElement("canvas");
  localCanvas.width = preview.videoWidth;
  localCanvas.height = preview.videoHeight;
  const context = localCanvas.getContext("2d", {alpha: false});
  const render = () => {
    context.save();
    if (rotate.checked) {
      context.translate(localCanvas.width, localCanvas.height);
      context.rotate(Math.PI);
    }
    context.drawImage(preview, 0, 0, localCanvas.width, localCanvas.height);
    context.restore();
    drawEyes(localCanvas);
    animationFrame = requestAnimationFrame(render);
  };
  render();
  startButton.disabled = false;
  status.textContent = `${preview.videoWidth}×${preview.videoHeight} preview ready.`;
}

function fillDeviceSelect() {
  deviceSelect.replaceChildren(new Option("Select a camera…", ""));
  for (const device of discoveredDevices) {
    deviceSelect.append(new Option(device.label || "Camera", device.deviceId));
  }
  const preferred = preferredDevice(discoveredDevices);
  selectedDeviceId = preferred?.deviceId || "";
  deviceSelect.value = selectedDeviceId;
  deviceSelect.disabled = !discoveredDevices.length;
}

async function refreshDevices() {
  stop();
  stopPreviewTracks();
  const permission = await navigator.mediaDevices.getUserMedia({video: true, audio: false});
  permission.getTracks().forEach(track => track.stop());
  discoveredDevices = (await navigator.mediaDevices.enumerateDevices())
    .filter(device => device.kind === "videoinput")
    .map(device => ({deviceId: device.deviceId, label: device.label || "Camera"}));
  document.querySelector("#refresh").textContent = "Refresh cameras";
  fillDeviceSelect();
  if (!selectedDeviceId) {
    status.textContent = "No video inputs found.";
    return;
  }
  await openPreview(selectedDeviceId);
}

async function waitForIce(connection) {
  if (connection.iceGatheringState === "complete") return;
  await new Promise(resolve => {
    connection.addEventListener("icegatheringstatechange", () => {
      if (connection.iceGatheringState === "complete") resolve();
    });
  });
}

async function startStreaming() {
  if (!previewStream || !localCanvas) {
    throw new Error("Select and preview a camera first");
  }
  if (animationFrame) cancelAnimationFrame(animationFrame);

  const outboundCanvas = document.createElement("canvas");
  outboundCanvas.className = "capture-canvas";
  outboundCanvas.width = outboundSize.width;
  outboundCanvas.height = outboundSize.height;
  document.body.append(outboundCanvas);
  const outboundContext = outboundCanvas.getContext("2d", {alpha: false});
  const localContext = localCanvas.getContext("2d", {alpha: false});

  const draw = () => {
    localContext.save();
    outboundContext.save();
    if (rotate.checked) {
      localContext.translate(localCanvas.width, localCanvas.height);
      localContext.rotate(Math.PI);
      outboundContext.translate(outboundCanvas.width, outboundCanvas.height);
      outboundContext.rotate(Math.PI);
    }
    localContext.drawImage(preview, 0, 0, localCanvas.width, localCanvas.height);
    outboundContext.drawImage(preview, 0, 0, outboundCanvas.width, outboundCanvas.height);
    localContext.restore();
    outboundContext.restore();
    drawEyes(localCanvas);
    animationFrame = requestAnimationFrame(draw);
  };
  draw();

  outboundStream = outboundCanvas.captureStream(30);
  peer = new RTCPeerConnection();
  outboundStream.getTracks().forEach(track => peer.addTrack(track, outboundStream));
  await peer.setLocalDescription(await peer.createOffer());
  await waitForIce(peer);
  const response = await fetch(`/api/offer/${STREAM_ID}`, {
    method: "POST",
    headers: {"content-type": "application/json"},
    body: JSON.stringify(peer.localDescription),
  });
  if (!response.ok) throw new Error(await response.text());
  await peer.setRemoteDescription(await response.json());
  startButton.disabled = true;
  stopButton.disabled = false;
  status.textContent = "Streaming to Viam as stream_id=cam.";
}

function resumeLocalPreview() {
  if (!previewStream || !preview.videoWidth) return;
  if (animationFrame) cancelAnimationFrame(animationFrame);
  if (!localCanvas) {
    localCanvas = document.createElement("canvas");
    localCanvas.width = preview.videoWidth;
    localCanvas.height = preview.videoHeight;
  }
  const context = localCanvas.getContext("2d", {alpha: false});
  const render = () => {
    context.save();
    if (rotate.checked) {
      context.translate(localCanvas.width, localCanvas.height);
      context.rotate(Math.PI);
    }
    context.drawImage(preview, 0, 0, localCanvas.width, localCanvas.height);
    context.restore();
    drawEyes(localCanvas);
    animationFrame = requestAnimationFrame(render);
  };
  render();
}

function stop() {
  if (peer) {
    peer.close();
    peer = null;
  }
  if (outboundStream) {
    outboundStream.getTracks().forEach(track => track.stop());
    outboundStream = null;
  }
  document.querySelectorAll(".capture-canvas").forEach(canvas => canvas.remove());
  resumeLocalPreview();
  startButton.disabled = !selectedDeviceId;
  stopButton.disabled = true;
}

document.querySelector("#refresh").addEventListener("click", () => {
  status.textContent = "Requesting camera permission…";
  refreshDevices().catch(error => {
    status.textContent = `Camera access failed: ${error.message}. Check browser permissions for localhost.`;
  });
});

deviceSelect.addEventListener("change", () => {
  selectedDeviceId = deviceSelect.value;
  openPreview(selectedDeviceId).catch(error => {
    status.textContent = `Could not open camera: ${error.message}`;
    startButton.disabled = true;
  });
});

startButton.addEventListener("click", () => {
  startStreaming().catch(error => {
    stop();
    const hint = error instanceof TypeError
      ? " Start the bridge (docker compose or stereo-depth-web) first."
      : "";
    status.textContent = `Could not start WebRTC: ${error.message}.${hint}`;
  });
});

stopButton.addEventListener("click", () => {
  stop();
  status.textContent = "Streaming stopped.";
});

rotate.addEventListener("change", () => {
  preview.classList.toggle("rotated", rotate.checked);
  status.textContent = rotate.checked ? "Preview rotated 180°." : "Rotation disabled.";
});

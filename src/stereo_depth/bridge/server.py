"""WebRTC signaling server and browser UI."""

import argparse
import asyncio
from io import BytesIO
from pathlib import Path
from typing import Set

from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription

from .frames import STORE

PEERS: Set[RTCPeerConnection] = set()
WEB_ROOT = Path(__file__).resolve().parent.parent / "web"


async def _receive_video(stream_id, track) -> None:
    while True:
        frame = await track.recv()
        image = frame.to_image()
        output = BytesIO()
        image.save(output, format="JPEG", quality=90)
        STORE.put(stream_id, output.getvalue(), image.width, image.height)


async def offer(request: web.Request) -> web.Response:
    stream_id = request.match_info["stream_id"]
    if not stream_id.replace("-", "").isalnum():
        raise web.HTTPBadRequest(text="invalid stream id")
    payload = await request.json()
    peer = RTCPeerConnection()
    PEERS.add(peer)

    @peer.on("track")
    def on_track(track):
        if track.kind == "video":
            asyncio.create_task(_receive_video(stream_id, track))

    @peer.on("connectionstatechange")
    async def on_state_change():
        if peer.connectionState in {"failed", "closed", "disconnected"}:
            await peer.close()
            PEERS.discard(peer)

    await peer.setRemoteDescription(
        RTCSessionDescription(sdp=payload["sdp"], type=payload["type"])
    )
    answer = await peer.createAnswer()
    await peer.setLocalDescription(answer)
    return web.json_response({
        "sdp": peer.localDescription.sdp,
        "type": peer.localDescription.type,
    })


async def status(_request: web.Request) -> web.Response:
    return web.json_response({
        name: {
            "width": frame.width,
            "height": frame.height,
            "age_seconds": round(asyncio.get_running_loop().time() - frame.received_at, 2),
        }
        for name, frame in STORE.snapshot().items()
    })


async def shutdown(_app: web.Application) -> None:
    await asyncio.gather(*(peer.close() for peer in PEERS), return_exceptions=True)
    PEERS.clear()


def create_app() -> web.Application:
    app = web.Application(client_max_size=1_000_000)
    app.router.add_post("/api/offer/{stream_id}", offer)
    app.router.add_get("/api/status", status)
    app.router.add_static("/", WEB_ROOT, show_index=True)
    app.on_shutdown.append(shutdown)
    return app


async def run_server(host: str = "0.0.0.0", port: int = 8081) -> None:
    runner = web.AppRunner(create_app())
    await runner.setup()
    await web.TCPSite(runner, host, port).start()
    await asyncio.Event().wait()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the stereo-depth WebRTC bridge")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8081)
    args = parser.parse_args()
    asyncio.run(run_server(args.host, args.port))


if __name__ == "__main__":
    main()

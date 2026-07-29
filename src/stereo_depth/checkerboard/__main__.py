"""Serve a fullscreen checkerboard on the LAN for phone/tablet calibration."""

from __future__ import annotations

import argparse
import http.server
import socket
import socketserver
from pathlib import Path

WEB_ROOT = Path(__file__).resolve().parent


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_ROOT), **kwargs)

    def log_message(self, fmt: str, *args) -> None:
        print(f"[checkerboard] {self.address_string()} {fmt % args}")


def lan_ips() -> list[str]:
    ips: list[str] = []
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            ips.append(sock.getsockname()[0])
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127.") and ip not in ips:
                ips.append(ip)
    except socket.gaierror:
        pass
    return ips or ["127.0.0.1"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    class ReusableServer(socketserver.TCPServer):
        allow_reuse_address = True

    with ReusableServer((args.host, args.port), Handler) as httpd:
        print("Checkerboard server")
        print(f"  local:  http://127.0.0.1:{args.port}/")
        for ip in lan_ips():
            print(f"  phone:  http://{ip}:{args.port}/")
        print("Same Wi-Fi. Ctrl+C to stop.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nstopped")


if __name__ == "__main__":
    main()

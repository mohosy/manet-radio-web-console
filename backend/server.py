from __future__ import annotations

import argparse
import json
import threading
import time
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .manet_sim import ManetSimulator

ROOT_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT_DIR / "web"


class AppContext:
    def __init__(self) -> None:
        self.sim = ManetSimulator()
        self.running = True


def _json_response(handler: SimpleHTTPRequestHandler, code: int, payload: dict) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class ManetHandler(SimpleHTTPRequestHandler):
    context: AppContext

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            _json_response(self, HTTPStatus.OK, {"ok": True})
            return

        if parsed.path == "/api/state":
            _json_response(self, HTTPStatus.OK, self.context.sim.state())
            return

        if parsed.path == "/api/events":
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()

            # Push state snapshots every 1s; browser auto-reconnect handles disconnects.
            for _ in range(120):
                if not self.context.running:
                    break
                payload = json.dumps(self.context.sim.state())
                self.wfile.write(f"data: {payload}\n\n".encode("utf-8"))
                self.wfile.flush()
                time.sleep(1.0)
            return

        if parsed.path == "/":
            self.path = "/index.html"

        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if not parsed.path.startswith("/api/node/"):
            _json_response(self, HTTPStatus.NOT_FOUND, {"error": "not-found"})
            return

        parts = parsed.path.strip("/").split("/")
        if len(parts) != 4:
            _json_response(self, HTTPStatus.BAD_REQUEST, {"error": "invalid-path"})
            return

        _, _, node_id, action = parts

        body_len = int(self.headers.get("Content-Length", "0"))
        payload = {}
        if body_len > 0:
            payload = json.loads(self.rfile.read(body_len).decode("utf-8"))

        ok = False
        if action == "tx_power":
            ok = self.context.sim.update_tx_power(node_id, float(payload.get("value", 0)))
        elif action == "channel":
            ok = self.context.sim.update_channel(node_id, int(payload.get("value", 1)))
        elif action == "reboot":
            ok = self.context.sim.reboot(node_id)

        if not ok:
            _json_response(self, HTTPStatus.BAD_REQUEST, {"error": "update-failed"})
            return

        _json_response(self, HTTPStatus.OK, self.context.sim.state())


def start_tick_loop(context: AppContext) -> threading.Thread:
    def _run() -> None:
        while context.running:
            context.sim.tick()
            time.sleep(0.4)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return thread


def create_server(host: str, port: int) -> ThreadingHTTPServer:
    context = AppContext()
    handler_cls = ManetHandler
    handler_cls.context = context
    server = ThreadingHTTPServer((host, port), handler_cls)
    server.context = context  # type: ignore[attr-defined]
    return server


def main() -> None:
    parser = argparse.ArgumentParser(description="MANET radio web console")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8088)
    args = parser.parse_args()

    server = create_server(args.host, args.port)
    start_tick_loop(server.context)  # type: ignore[attr-defined]

    print(f"MANET console running at http://{args.host}:{args.port}")
    try:
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.context.running = False  # type: ignore[attr-defined]
        server.shutdown()


if __name__ == "__main__":
    main()

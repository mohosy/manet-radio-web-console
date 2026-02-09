import json
import threading
import time
import unittest
from urllib import request

from backend.server import create_server, start_tick_loop


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = create_server("127.0.0.1", 0)
        cls.host, cls.port = cls.server.server_address
        start_tick_loop(cls.server.context)  # type: ignore[attr-defined]

        cls.thread = threading.Thread(target=cls.server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        cls.thread.start()
        time.sleep(0.15)

    @classmethod
    def tearDownClass(cls):
        cls.server.context.running = False  # type: ignore[attr-defined]
        cls.server.shutdown()
        cls.thread.join(timeout=2.0)

    def _get_json(self, path: str):
        with request.urlopen(f"http://{self.host}:{self.port}{path}", timeout=3.0) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _post_json(self, path: str, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            f"http://{self.host}:{self.port}{path}",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with request.urlopen(req, timeout=3.0) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def test_state_endpoint_contains_advanced_sections(self):
        payload = self._get_json("/api/state")
        self.assertIn("nodes", payload)
        self.assertIn("links", payload)
        self.assertIn("kpis", payload)
        self.assertIn("routing", payload)
        self.assertIn("events", payload)

    def test_update_tx_power(self):
        payload = self._post_json("/api/node/R1/tx_power", {"value": 30})
        nodes = {n["node_id"]: n for n in payload["nodes"]}
        self.assertAlmostEqual(nodes["R1"]["tx_power_dbm"], 30.0)

    def test_route_endpoint(self):
        route = self._get_json("/api/route?src=R1&dst=R5")
        self.assertIn("reachable", route)
        self.assertIn("src", route)
        self.assertIn("dst", route)
        self.assertEqual(route["src"], "R1")
        self.assertEqual(route["dst"], "R5")

    def test_channel_optimization_endpoint(self):
        result = self._post_json("/api/network/optimize_channels", {})
        self.assertIn("changed", result)
        self.assertIn("kpis", result)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import math
import random
import threading
import time
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple

from .native_bridge import metric


@dataclass
class Node:
    node_id: str
    x: float
    y: float
    tx_power_dbm: float
    channel: int
    battery: float
    status: str


class ManetSimulator:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._rng = random.Random(42)
        self._tick = 0
        self._noise_floor_dbm = -92.0
        self._nodes: Dict[str, Node] = {
            "R1": Node("R1", 40, 45, 26.0, 1, 99.0, "online"),
            "R2": Node("R2", 130, 80, 24.0, 1, 97.0, "online"),
            "R3": Node("R3", 205, 130, 23.0, 1, 96.0, "online"),
            "R4": Node("R4", 110, 190, 22.0, 6, 94.0, "online"),
            "R5": Node("R5", 260, 210, 24.0, 1, 93.0, "online")
        }

    def update_tx_power(self, node_id: str, tx_power_dbm: float) -> bool:
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                return False
            node.tx_power_dbm = max(5.0, min(33.0, tx_power_dbm))
            return True

    def update_channel(self, node_id: str, channel: int) -> bool:
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                return False
            node.channel = max(1, min(11, channel))
            return True

    def reboot(self, node_id: str) -> bool:
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                return False
            node.status = "rebooting"

        def _complete() -> None:
            time.sleep(0.4)
            with self._lock:
                n = self._nodes.get(node_id)
                if n:
                    n.status = "online"

        threading.Thread(target=_complete, daemon=True).start()
        return True

    def tick(self) -> None:
        with self._lock:
            self._tick += 1
            for node in self._nodes.values():
                if node.status == "online":
                    node.x = max(20.0, min(300.0, node.x + self._rng.uniform(-3.0, 3.0)))
                    node.y = max(20.0, min(240.0, node.y + self._rng.uniform(-3.0, 3.0)))
                    node.battery = max(10.0, node.battery - self._rng.uniform(0.01, 0.06))

                    if node.battery < 20.0 and self._rng.random() < 0.02:
                        node.status = "degraded"
                elif node.status == "degraded" and self._rng.random() < 0.2:
                    node.status = "online"

    def _link_score(self, a: Node, b: Node) -> float:
        dx = a.x - b.x
        dy = a.y - b.y
        distance = math.sqrt(dx * dx + dy * dy)
        power = (a.tx_power_dbm + b.tx_power_dbm) / 2.0
        return metric.score(distance, power, self._noise_floor_dbm, a.channel == b.channel)

    def _links(self) -> List[Dict[str, float]]:
        nodes = list(self._nodes.values())
        links: List[Dict[str, float]] = []

        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                score = self._link_score(nodes[i], nodes[j])
                if score < 0.10:
                    continue
                links.append(
                    {
                        "a": nodes[i].node_id,
                        "b": nodes[j].node_id,
                        "score": round(score, 4),
                        "status": "stable" if score >= 0.55 else "degraded"
                    }
                )
        return links

    def _kpis(self, links: List[Dict[str, float]]) -> Dict[str, float]:
        node_values = list(self._nodes.values())
        online_nodes = sum(1 for n in node_values if n.status == "online")
        degraded_nodes = sum(1 for n in node_values if n.status == "degraded")
        avg_battery = sum(n.battery for n in node_values) / len(node_values)
        avg_score = (sum(l["score"] for l in links) / len(links)) if links else 0.0
        degraded_links = sum(1 for l in links if l["status"] == "degraded")

        return {
            "online_nodes": online_nodes,
            "degraded_nodes": degraded_nodes,
            "avg_battery": round(avg_battery, 2),
            "avg_link_score": round(avg_score, 4),
            "degraded_links": degraded_links
        }

    def state(self) -> Dict[str, object]:
        with self._lock:
            nodes = [asdict(node) for node in self._nodes.values()]
        links = self._links()

        return {
            "tick": self._tick,
            "timestamp": time.time(),
            "nodes": nodes,
            "links": links,
            "kpis": self._kpis(links)
        }


def parse_control_payload(payload: Dict[str, object]) -> Tuple[str, float]:
    if "field" not in payload or "value" not in payload:
        raise ValueError("missing field/value")
    return str(payload["field"]), float(payload["value"])

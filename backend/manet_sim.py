from __future__ import annotations

import heapq
import math
import random
import threading
import time
from collections import deque
from dataclasses import asdict, dataclass
from typing import Deque, Dict, List

from .native_bridge import metric


@dataclass
class Node:
    node_id: str
    x: float
    y: float
    tx_power_dbm: float
    channel: int
    battery: float
    queue_depth: int
    firmware_version: str
    status: str


class ManetSimulator:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._rng = random.Random(42)
        self._tick = 0
        self._noise_floor_dbm = -92.0
        self._opt_channels = [1, 3, 6, 9, 11]
        self._event_log: Deque[dict] = deque(maxlen=150)

        self._nodes: Dict[str, Node] = {
            "R1": Node("R1", 40, 45, 26.0, 1, 99.0, 8, "2.4.1", "online"),
            "R2": Node("R2", 130, 80, 24.0, 1, 97.0, 12, "2.4.1", "online"),
            "R3": Node("R3", 205, 130, 23.0, 1, 96.0, 6, "2.4.0", "online"),
            "R4": Node("R4", 110, 190, 22.0, 6, 94.0, 10, "2.3.9", "online"),
            "R5": Node("R5", 260, 210, 24.0, 1, 93.0, 11, "2.4.1", "online")
        }

        self._push_event("boot", "simulator initialized")

    def _push_event(self, kind: str, message: str, payload: dict | None = None) -> None:
        self._event_log.appendleft(
            {
                "tick": self._tick,
                "timestamp": round(time.time(), 3),
                "kind": kind,
                "message": message,
                "payload": payload or {}
            }
        )

    def _distance(self, a: Node, b: Node) -> float:
        return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)

    @staticmethod
    def _channel_factor(channel_a: int, channel_b: int) -> float:
        diff = abs(channel_a - channel_b)
        if diff == 0:
            return 1.0
        if diff <= 2:
            return 0.65
        if diff <= 4:
            return 0.35
        return 0.05

    def _link_metrics(self, a: Node, b: Node) -> dict:
        distance = self._distance(a, b)
        base_power = (a.tx_power_dbm + b.tx_power_dbm) / 2.0
        baseline = metric.score(distance, base_power, self._noise_floor_dbm, True)

        score = baseline * self._channel_factor(a.channel, b.channel)
        score = min(max(score, 0.0), 1.0)

        etx = 1.0 / max(score, 0.05)
        latency_ms = 2.2 + (1.0 - score) * 20.0 + (distance / 165.0)

        capacity_mbps = metric.capacity_mbps(score, channel_width_mhz=20.0, mimo_streams=2)
        # Deeper queueing drives lower practical throughput.
        queue_penalty = 1.0 + (a.queue_depth + b.queue_depth) / 120.0
        capacity_mbps = max(0.1, capacity_mbps / queue_penalty)

        return {
            "a": a.node_id,
            "b": b.node_id,
            "score": round(score, 4),
            "etx": round(etx, 3),
            "latency_ms": round(latency_ms, 2),
            "throughput_mbps": round(capacity_mbps, 2),
            "distance_m": round(distance, 1),
            "status": "stable" if score >= 0.55 else "degraded"
        }

    def _links(self) -> List[dict]:
        nodes = list(self._nodes.values())
        links: List[dict] = []

        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                link = self._link_metrics(nodes[i], nodes[j])
                if link["score"] < 0.10:
                    continue
                links.append(link)

        return links

    def _graph(self, links: List[dict]) -> Dict[str, List[tuple]]:
        graph: Dict[str, List[tuple]] = {node_id: [] for node_id in self._nodes.keys()}
        for link in links:
            cost = float(link["etx"]) + (float(link["latency_ms"]) / 15.0)
            graph[link["a"]].append((link["b"], cost, link))
            graph[link["b"]].append((link["a"], cost, link))
        return graph

    def _route_from_links(self, src: str, dst: str, links: List[dict]) -> dict:
        if src not in self._nodes or dst not in self._nodes:
            return {
                "src": src,
                "dst": dst,
                "reachable": False,
                "reason": "unknown-node"
            }

        if src == dst:
            return {
                "src": src,
                "dst": dst,
                "reachable": True,
                "path": [src],
                "hops": 0,
                "cost": 0.0,
                "avg_link_score": 1.0,
                "estimated_latency_ms": 0.0,
                "bottleneck_mbps": 0.0
            }

        graph = self._graph(links)

        dist = {src: 0.0}
        parent: Dict[str, str | None] = {src: None}
        parent_link: Dict[str, dict] = {}
        heap = [(0.0, src)]

        while heap:
            d, node = heapq.heappop(heap)
            if node == dst:
                break
            if d > dist.get(node, float("inf")):
                continue

            for nxt, w, edge in graph.get(node, []):
                nd = d + w
                if nd < dist.get(nxt, float("inf")):
                    dist[nxt] = nd
                    parent[nxt] = node
                    parent_link[nxt] = edge
                    heapq.heappush(heap, (nd, nxt))

        if dst not in dist:
            return {
                "src": src,
                "dst": dst,
                "reachable": False,
                "reason": "no-path"
            }

        path = []
        cur = dst
        while cur is not None:
            path.append(cur)
            cur = parent[cur]
        path.reverse()

        traversed = []
        for i in range(1, len(path)):
            traversed.append(parent_link[path[i]])

        avg_score = sum(float(link["score"]) for link in traversed) / max(len(traversed), 1)
        total_latency = sum(float(link["latency_ms"]) for link in traversed)
        bottleneck = min((float(link["throughput_mbps"]) for link in traversed), default=0.0)

        return {
            "src": src,
            "dst": dst,
            "reachable": True,
            "path": path,
            "hops": len(path) - 1,
            "cost": round(dist[dst], 3),
            "avg_link_score": round(avg_score, 4),
            "estimated_latency_ms": round(total_latency, 2),
            "bottleneck_mbps": round(bottleneck, 2)
        }

    def route(self, src: str, dst: str) -> dict:
        with self._lock:
            links = self._links()
            return self._route_from_links(src, dst, links)

    def _routing_summary(self, links: List[dict], root: str = "R1") -> dict:
        routes: Dict[str, dict] = {}
        reachable = 0

        for node_id in self._nodes.keys():
            if node_id == root:
                continue
            route = self._route_from_links(root, node_id, links)
            routes[node_id] = route
            if route.get("reachable"):
                reachable += 1

        total_targets = max(len(self._nodes) - 1, 1)
        return {
            "root": root,
            "connectivity_ratio": round(reachable / total_targets, 3),
            "routes": routes
        }

    def optimize_channels(self) -> dict:
        with self._lock:
            changed = []
            node_ids = sorted(self._nodes.keys())

            for node_id in node_ids:
                node = self._nodes[node_id]
                original_channel = node.channel
                best_channel = original_channel
                best_objective = float("-inf")

                for candidate in self._opt_channels:
                    node.channel = candidate

                    local_scores = []
                    same_channel_neighbors = 0
                    for other_id, other in self._nodes.items():
                        if other_id == node_id:
                            continue
                        metrics = self._link_metrics(node, other)
                        local_scores.append(metrics["score"])
                        if candidate == other.channel and metrics["distance_m"] < 140.0:
                            same_channel_neighbors += 1

                    objective = (sum(local_scores) / max(len(local_scores), 1)) - 0.03 * same_channel_neighbors
                    if objective > best_objective:
                        best_objective = objective
                        best_channel = candidate

                node.channel = best_channel
                if best_channel != original_channel:
                    changed.append({"node": node_id, "from": original_channel, "to": best_channel})

            if changed:
                self._push_event("channel-optimize", "automatic channel plan applied", {"changes": changed})
            else:
                self._push_event("channel-optimize", "channel plan unchanged")

            links = self._links()
            summary = self._routing_summary(links)
            return {
                "changed": changed,
                "routing": summary,
                "kpis": self._kpis(links, summary)
            }

    def update_tx_power(self, node_id: str, tx_power_dbm: float) -> bool:
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                return False
            node.tx_power_dbm = max(5.0, min(33.0, tx_power_dbm))
            self._push_event("node-update", f"{node_id} tx_power updated", {"tx_power_dbm": node.tx_power_dbm})
            return True

    def update_channel(self, node_id: str, channel: int) -> bool:
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                return False
            node.channel = max(1, min(11, channel))
            self._push_event("node-update", f"{node_id} channel updated", {"channel": node.channel})
            return True

    def reboot(self, node_id: str) -> bool:
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                return False
            node.status = "rebooting"
            self._push_event("node-reboot", f"{node_id} reboot initiated")

        def _complete() -> None:
            time.sleep(0.4)
            with self._lock:
                n = self._nodes.get(node_id)
                if n:
                    n.status = "online"
                    self._push_event("node-reboot", f"{node_id} back online")

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

                    inflow = self._rng.randint(0, 4)
                    outflow = self._rng.randint(0, 4)
                    node.queue_depth = int(min(120, max(0, node.queue_depth + inflow - outflow)))

                    if node.battery < 20.0 and self._rng.random() < 0.02:
                        node.status = "degraded"
                        self._push_event("node-health", f"{node.node_id} entered degraded mode", {"battery": round(node.battery, 2)})
                elif node.status == "degraded" and self._rng.random() < 0.2:
                    node.status = "online"
                    self._push_event("node-health", f"{node.node_id} recovered")

            if self._tick % 25 == 0:
                self._push_event("telemetry", "periodic telemetry snapshot")

    def _kpis(self, links: List[dict], routing_summary: dict) -> Dict[str, float]:
        node_values = list(self._nodes.values())
        online_nodes = sum(1 for n in node_values if n.status == "online")
        degraded_nodes = sum(1 for n in node_values if n.status == "degraded")
        avg_battery = sum(n.battery for n in node_values) / len(node_values)
        avg_queue = sum(n.queue_depth for n in node_values) / len(node_values)

        avg_score = (sum(float(l["score"]) for l in links) / len(links)) if links else 0.0
        avg_latency = (sum(float(l["latency_ms"]) for l in links) / len(links)) if links else 0.0
        avg_capacity = (sum(float(l["throughput_mbps"]) for l in links) / len(links)) if links else 0.0
        degraded_links = sum(1 for l in links if l["status"] == "degraded")

        return {
            "online_nodes": online_nodes,
            "degraded_nodes": degraded_nodes,
            "avg_battery": round(avg_battery, 2),
            "avg_queue_depth": round(avg_queue, 2),
            "avg_link_score": round(avg_score, 4),
            "avg_latency_ms": round(avg_latency, 2),
            "avg_capacity_mbps": round(avg_capacity, 2),
            "degraded_links": degraded_links,
            "connectivity_ratio": routing_summary["connectivity_ratio"]
        }

    def state(self) -> Dict[str, object]:
        with self._lock:
            nodes = [asdict(node) for node in self._nodes.values()]
            links = self._links()
            routing = self._routing_summary(links)
            kpis = self._kpis(links, routing)
            events = list(self._event_log)

        return {
            "tick": self._tick,
            "timestamp": time.time(),
            "nodes": nodes,
            "links": links,
            "routing": routing,
            "kpis": kpis,
            "events": events
        }

    def event_log(self) -> List[dict]:
        with self._lock:
            return list(self._event_log)

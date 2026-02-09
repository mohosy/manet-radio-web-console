import test from "node:test";
import assert from "node:assert/strict";
import { JSDOM } from "jsdom";

const html = `
<!doctype html>
<html>
  <body>
    <button id="refresh-btn"></button>
    <button id="optimize-btn"></button>
    <span id="tick-label"></span>
    <div id="kpi-grid"></div>
    <div id="nodes-list"></div>
    <table><tbody id="links-body"></tbody></table>
    <table><tbody id="routes-body"></tbody></table>
    <div id="events-list"></div>
    <select id="route-src"></select>
    <select id="route-dst"></select>
    <button id="route-btn"></button>
    <pre id="route-output"></pre>
    <canvas id="topology-canvas" width="640" height="320"></canvas>
    <div id="toast"></div>
  </body>
</html>
`;

function makeSampleState() {
  return {
    tick: 3,
    kpis: {
      online_nodes: 4,
      degraded_nodes: 1,
      avg_battery: 88.5,
      avg_queue_depth: 12.4,
      avg_link_score: 0.6231,
      avg_latency_ms: 7.8,
      avg_capacity_mbps: 42.1,
      degraded_links: 2,
      connectivity_ratio: 1.0
    },
    nodes: [
      { node_id: "R1", x: 40, y: 40, tx_power_dbm: 25, channel: 1, battery: 96.2, queue_depth: 9, firmware_version: "2.4.1", status: "online" },
      { node_id: "R2", x: 100, y: 90, tx_power_dbm: 22, channel: 1, battery: 82.1, queue_depth: 17, firmware_version: "2.4.0", status: "degraded" }
    ],
    links: [
      { a: "R1", b: "R2", score: 0.6123, etx: 1.62, latency_ms: 7.2, throughput_mbps: 51.3, status: "stable" }
    ],
    routing: {
      root: "R1",
      connectivity_ratio: 1.0,
      routes: {
        R2: {
          reachable: true,
          path: ["R1", "R2"],
          estimated_latency_ms: 7.2,
          bottleneck_mbps: 51.3
        }
      }
    },
    events: [
      { tick: 3, kind: "node-update", message: "R1 tx_power updated" }
    ]
  };
}

test("applyState renders advanced telemetry panels", async () => {
  const dom = new JSDOM(html, { url: "http://localhost" });
  global.window = dom.window;
  global.document = dom.window.document;
  global.window.__MANET_DISABLE_AUTO_BOOTSTRAP = true;

  global.fetch = async () => ({ ok: true, json: async () => makeSampleState() });
  global.EventSource = class {
    constructor() {}
    set onmessage(_) {}
    set onerror(_) {}
  };

  dom.window.HTMLCanvasElement.prototype.getContext = () => ({
    clearRect() {},
    fillRect() {},
    beginPath() {},
    moveTo() {},
    lineTo() {},
    stroke() {},
    arc() {},
    fill() {},
    fillText() {}
  });

  const module = await import(`file:///Users/mo/Downloads/manet-radio-web-console/web/app.js?${Date.now()}`);

  const refs = {
    tickLabel: dom.window.document.getElementById("tick-label"),
    kpiGrid: dom.window.document.getElementById("kpi-grid"),
    nodesList: dom.window.document.getElementById("nodes-list"),
    linksBody: dom.window.document.getElementById("links-body"),
    routesBody: dom.window.document.getElementById("routes-body"),
    eventsList: dom.window.document.getElementById("events-list"),
    routeSrc: dom.window.document.getElementById("route-src"),
    routeDst: dom.window.document.getElementById("route-dst"),
    routeOutput: dom.window.document.getElementById("route-output"),
    canvas: dom.window.document.getElementById("topology-canvas")
  };

  module.applyState(makeSampleState(), refs, () => {});

  assert.equal(refs.tickLabel.textContent, "Tick 3");
  assert.equal(refs.nodesList.children.length, 2);
  assert.equal(refs.linksBody.children.length, 1);
  assert.equal(refs.routesBody.children.length, 1);
  assert.equal(refs.eventsList.children.length, 1);
  assert.ok(refs.kpiGrid.textContent.includes("Connectivity"));
  assert.equal(refs.routeSrc.options.length, 2);
});

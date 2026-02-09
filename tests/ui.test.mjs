import test from "node:test";
import assert from "node:assert/strict";
import { JSDOM } from "jsdom";

const html = `
<!doctype html>
<html>
  <body>
    <button id="refresh-btn"></button>
    <span id="tick-label"></span>
    <div id="kpi-grid"></div>
    <div id="nodes-list"></div>
    <table><tbody id="links-body"></tbody></table>
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
      avg_link_score: 0.6231,
      degraded_links: 2
    },
    nodes: [
      { node_id: "R1", x: 40, y: 40, tx_power_dbm: 25, channel: 1, battery: 96.2, status: "online" },
      { node_id: "R2", x: 100, y: 90, tx_power_dbm: 22, channel: 1, battery: 82.1, status: "degraded" }
    ],
    links: [
      { a: "R1", b: "R2", score: 0.6123, status: "stable" }
    ]
  };
}

test("applyState renders KPI, node cards, and links", async () => {
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
    canvas: dom.window.document.getElementById("topology-canvas")
  };

  module.applyState(makeSampleState(), refs, () => {});

  assert.equal(refs.tickLabel.textContent, "Tick 3");
  assert.equal(refs.nodesList.children.length, 2);
  assert.equal(refs.linksBody.children.length, 1);
  assert.ok(refs.kpiGrid.textContent.includes("Online Nodes"));
});

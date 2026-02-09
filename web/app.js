const API = {
  state: "/api/state",
  route: "/api/route",
  optimize: "/api/network/optimize_channels"
};

function clamp(v, min, max) {
  return Math.min(Math.max(v, min), max);
}

async function postJson(url, payload) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    throw new Error(`request failed: ${res.status}`);
  }
  return res.json();
}

function showToast(el, text) {
  if (!el) {
    return;
  }
  el.textContent = text;
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 1200);
}

export function renderKpis(container, kpis) {
  if (!container) {
    return;
  }

  container.innerHTML = "";
  const items = [
    ["Online Nodes", String(kpis.online_nodes ?? 0)],
    ["Degraded Nodes", String(kpis.degraded_nodes ?? 0)],
    ["Connectivity", `${((kpis.connectivity_ratio ?? 0) * 100).toFixed(1)}%`],
    ["Avg Battery", `${(kpis.avg_battery ?? 0).toFixed(2)}%`],
    ["Avg Queue", (kpis.avg_queue_depth ?? 0).toFixed(2)],
    ["Avg Link Score", (kpis.avg_link_score ?? 0).toFixed(4)],
    ["Avg Latency", `${(kpis.avg_latency_ms ?? 0).toFixed(2)} ms`],
    ["Avg Capacity", `${(kpis.avg_capacity_mbps ?? 0).toFixed(2)} Mbps`]
  ];

  for (const [label, value] of items) {
    const card = container.ownerDocument.createElement("article");
    card.className = "kpi";

    const l = container.ownerDocument.createElement("div");
    l.className = "label";
    l.textContent = label;

    const v = container.ownerDocument.createElement("div");
    v.className = "value";
    v.textContent = value;

    card.append(l, v);
    container.append(card);
  }
}

export function renderLinks(tbody, links) {
  if (!tbody) {
    return;
  }

  tbody.innerHTML = "";
  for (const link of links) {
    const tr = tbody.ownerDocument.createElement("tr");

    const a = tbody.ownerDocument.createElement("td");
    a.textContent = link.a;
    const b = tbody.ownerDocument.createElement("td");
    b.textContent = link.b;

    const score = tbody.ownerDocument.createElement("td");
    score.textContent = Number(link.score).toFixed(4);

    const etx = tbody.ownerDocument.createElement("td");
    etx.textContent = Number(link.etx ?? 0).toFixed(3);

    const latency = tbody.ownerDocument.createElement("td");
    latency.textContent = `${Number(link.latency_ms ?? 0).toFixed(2)}ms`;

    const throughput = tbody.ownerDocument.createElement("td");
    throughput.textContent = `${Number(link.throughput_mbps ?? 0).toFixed(2)}`;

    const status = tbody.ownerDocument.createElement("td");
    status.textContent = link.status;
    status.className = link.status === "stable" ? "status-stable" : "status-degraded";

    tr.append(a, b, score, etx, latency, throughput, status);
    tbody.append(tr);
  }
}

function makeNodeCard(doc, node, onAction) {
  const card = doc.createElement("article");
  card.className = "node-card";

  const top = doc.createElement("div");
  top.className = "node-top";

  const title = doc.createElement("strong");
  title.textContent = `${node.node_id} (CH ${node.channel})`;

  const badge = doc.createElement("span");
  badge.className = `badge ${node.status}`;
  badge.textContent = node.status;

  top.append(title, badge);

  const text = doc.createElement("p");
  text.textContent = `TX ${node.tx_power_dbm.toFixed(1)} dBm | Battery ${node.battery.toFixed(1)}% | Queue ${node.queue_depth}`;
  text.style.color = "var(--muted)";
  text.style.margin = "0 0 8px";

  const fw = doc.createElement("p");
  fw.textContent = `FW ${node.firmware_version}`;
  fw.style.color = "var(--muted)";
  fw.style.margin = "0 0 8px";

  const controls = doc.createElement("div");
  controls.className = "controls";

  const txInput = doc.createElement("input");
  txInput.type = "number";
  txInput.min = "5";
  txInput.max = "33";
  txInput.value = String(node.tx_power_dbm);

  const chInput = doc.createElement("input");
  chInput.type = "number";
  chInput.min = "1";
  chInput.max = "11";
  chInput.value = String(node.channel);

  const applyBtn = doc.createElement("button");
  applyBtn.textContent = "Apply";

  const rebootBtn = doc.createElement("button");
  rebootBtn.textContent = "Reboot";

  applyBtn.addEventListener("click", () => {
    onAction(node.node_id, {
      txPower: clamp(Number(txInput.value || node.tx_power_dbm), 5, 33),
      channel: clamp(Number(chInput.value || node.channel), 1, 11)
    });
  });

  rebootBtn.addEventListener("click", () => {
    onAction(node.node_id, { reboot: true });
  });

  controls.append(txInput, chInput, applyBtn);
  card.append(top, text, fw, controls, rebootBtn);
  return card;
}

export function renderNodes(container, nodes, onAction) {
  if (!container) {
    return;
  }

  container.innerHTML = "";
  for (const node of nodes) {
    container.append(makeNodeCard(container.ownerDocument, node, onAction));
  }
}

export function renderRoutingSummary(tbody, routing) {
  if (!tbody) {
    return;
  }

  tbody.innerHTML = "";
  const routes = routing?.routes ?? {};
  const destinations = Object.keys(routes).sort();

  for (const dest of destinations) {
    const route = routes[dest];
    const tr = tbody.ownerDocument.createElement("tr");

    const tdDest = tbody.ownerDocument.createElement("td");
    tdDest.textContent = dest;

    const tdPath = tbody.ownerDocument.createElement("td");
    tdPath.textContent = route.reachable ? route.path.join(" -> ") : "unreachable";

    const tdLatency = tbody.ownerDocument.createElement("td");
    tdLatency.textContent = route.reachable ? `${Number(route.estimated_latency_ms).toFixed(2)}ms` : "-";

    const tdBw = tbody.ownerDocument.createElement("td");
    tdBw.textContent = route.reachable ? `${Number(route.bottleneck_mbps).toFixed(2)}Mbps` : "-";

    tr.append(tdDest, tdPath, tdLatency, tdBw);
    tbody.append(tr);
  }
}

export function renderEvents(container, events) {
  if (!container) {
    return;
  }

  container.innerHTML = "";
  for (const item of events.slice(0, 40)) {
    const block = container.ownerDocument.createElement("article");
    block.className = "event-item";

    const meta = container.ownerDocument.createElement("div");
    meta.className = "meta";
    meta.textContent = `tick=${item.tick} kind=${item.kind}`;

    const msg = container.ownerDocument.createElement("div");
    msg.className = "msg";
    msg.textContent = item.message;

    block.append(meta, msg);
    container.append(block);
  }
}

export function drawTopology(canvas, nodes, links) {
  if (!canvas) {
    return;
  }

  const ctx = canvas.getContext("2d");
  if (!ctx) {
    return;
  }

  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "#071221";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  for (const link of links) {
    const a = nodes.find((n) => n.node_id === link.a);
    const b = nodes.find((n) => n.node_id === link.b);
    if (!a || !b) {
      continue;
    }

    const color = link.status === "stable" ? "#2dd4bf" : "#f59e0b";
    ctx.strokeStyle = color;
    ctx.lineWidth = Math.max(1, Number(link.score) * 3);
    ctx.beginPath();
    ctx.moveTo(a.x * 2, a.y * 1.2);
    ctx.lineTo(b.x * 2, b.y * 1.2);
    ctx.stroke();
  }

  for (const node of nodes) {
    const x = node.x * 2;
    const y = node.y * 1.2;

    ctx.fillStyle = node.status === "online" ? "#5eead4" : node.status === "degraded" ? "#fbbf24" : "#fca5a5";
    ctx.beginPath();
    ctx.arc(x, y, 9, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = "#e7edf8";
    ctx.font = "12px JetBrains Mono";
    ctx.fillText(node.node_id, x + 12, y + 4);
  }
}

function setRouteSelectors(dom, nodes) {
  if (!dom.routeSrc || !dom.routeDst) {
    return;
  }

  const ids = nodes.map((n) => n.node_id).sort();
  const prevSrc = dom.routeSrc.value;
  const prevDst = dom.routeDst.value;

  for (const select of [dom.routeSrc, dom.routeDst]) {
    select.innerHTML = "";
    for (const id of ids) {
      const opt = select.ownerDocument.createElement("option");
      opt.value = id;
      opt.textContent = id;
      select.append(opt);
    }
  }

  dom.routeSrc.value = ids.includes(prevSrc) ? prevSrc : ids[0] ?? "";
  dom.routeDst.value = ids.includes(prevDst) ? prevDst : ids[ids.length - 1] ?? "";
}

function formatRoute(route) {
  if (!route || !route.reachable) {
    return `unreachable (${route?.reason ?? "no-path"})`;
  }
  return [
    `path: ${route.path.join(" -> ")}`,
    `hops: ${route.hops}`,
    `cost: ${Number(route.cost).toFixed(3)}`,
    `latency: ${Number(route.estimated_latency_ms).toFixed(2)} ms`,
    `bottleneck: ${Number(route.bottleneck_mbps).toFixed(2)} Mbps`,
    `avg-link-score: ${Number(route.avg_link_score).toFixed(4)}`
  ].join("\n");
}

export function applyState(state, dom, onAction) {
  if (dom.tickLabel) {
    dom.tickLabel.textContent = `Tick ${state.tick}`;
  }

  renderKpis(dom.kpiGrid, state.kpis ?? {});
  renderLinks(dom.linksBody, state.links ?? []);
  renderNodes(dom.nodesList, state.nodes ?? [], onAction);
  renderRoutingSummary(dom.routesBody, state.routing ?? {});
  renderEvents(dom.eventsList, state.events ?? []);
  drawTopology(dom.canvas, state.nodes ?? [], state.links ?? []);
  setRouteSelectors(dom, state.nodes ?? []);
}

function collectDom(documentRef) {
  return {
    refreshBtn: documentRef.getElementById("refresh-btn"),
    optimizeBtn: documentRef.getElementById("optimize-btn"),
    tickLabel: documentRef.getElementById("tick-label"),
    kpiGrid: documentRef.getElementById("kpi-grid"),
    nodesList: documentRef.getElementById("nodes-list"),
    linksBody: documentRef.getElementById("links-body"),
    routesBody: documentRef.getElementById("routes-body"),
    eventsList: documentRef.getElementById("events-list"),
    routeSrc: documentRef.getElementById("route-src"),
    routeDst: documentRef.getElementById("route-dst"),
    routeBtn: documentRef.getElementById("route-btn"),
    routeOutput: documentRef.getElementById("route-output"),
    canvas: documentRef.getElementById("topology-canvas"),
    toast: documentRef.getElementById("toast")
  };
}

export async function bootstrap(documentRef = document, windowRef = window) {
  const dom = collectDom(documentRef);

  async function refresh() {
    const state = await fetch(API.state).then((r) => r.json());
    applyState(state, dom, onNodeAction);
  }

  async function onNodeAction(nodeId, payload) {
    try {
      if (payload.reboot) {
        await postJson(`/api/node/${nodeId}/reboot`, {});
      } else {
        await postJson(`/api/node/${nodeId}/tx_power`, { value: payload.txPower });
        await postJson(`/api/node/${nodeId}/channel`, { value: payload.channel });
      }
      await refresh();
      showToast(dom.toast, `${nodeId} updated`);
    } catch (error) {
      showToast(dom.toast, "Update failed");
      console.error(error);
    }
  }

  async function optimizeChannels() {
    try {
      await postJson(API.optimize, {});
      await refresh();
      showToast(dom.toast, "Channel optimization applied");
    } catch (error) {
      showToast(dom.toast, "Optimization failed");
      console.error(error);
    }
  }

  async function analyzeRoute() {
    if (!dom.routeSrc || !dom.routeDst || !dom.routeOutput) {
      return;
    }
    const src = dom.routeSrc.value;
    const dst = dom.routeDst.value;
    if (!src || !dst) {
      return;
    }

    const route = await fetch(`${API.route}?src=${encodeURIComponent(src)}&dst=${encodeURIComponent(dst)}`).then((r) => r.json());
    dom.routeOutput.textContent = formatRoute(route);
  }

  dom.refreshBtn?.addEventListener("click", refresh);
  dom.optimizeBtn?.addEventListener("click", optimizeChannels);
  dom.routeBtn?.addEventListener("click", () => {
    analyzeRoute().catch((error) => {
      showToast(dom.toast, "Route lookup failed");
      console.error(error);
    });
  });

  await refresh();

  const events = new windowRef.EventSource("/api/events");
  events.onmessage = (event) => {
    const state = JSON.parse(event.data);
    applyState(state, dom, onNodeAction);
  };

  events.onerror = () => {
    showToast(dom.toast, "Live stream reconnecting");
  };
}

if (
  typeof window !== "undefined" &&
  typeof document !== "undefined" &&
  !window.__MANET_DISABLE_AUTO_BOOTSTRAP
) {
  bootstrap().catch((error) => {
    console.error(error);
  });
}

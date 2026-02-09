const API_STATE = "/api/state";

function clamp(v, min, max) {
  return Math.min(Math.max(v, min), max);
}

export function renderKpis(container, kpis) {
  container.innerHTML = "";
  const items = [
    ["Online Nodes", String(kpis.online_nodes ?? 0)],
    ["Degraded Nodes", String(kpis.degraded_nodes ?? 0)],
    ["Avg Battery", `${(kpis.avg_battery ?? 0).toFixed(2)}%`],
    ["Avg Link Score", (kpis.avg_link_score ?? 0).toFixed(4)],
    ["Degraded Links", String(kpis.degraded_links ?? 0)]
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
  tbody.innerHTML = "";
  for (const link of links) {
    const tr = tbody.ownerDocument.createElement("tr");

    const a = tbody.ownerDocument.createElement("td");
    a.textContent = link.a;
    const b = tbody.ownerDocument.createElement("td");
    b.textContent = link.b;
    const score = tbody.ownerDocument.createElement("td");
    score.textContent = Number(link.score).toFixed(4);
    const status = tbody.ownerDocument.createElement("td");
    status.textContent = link.status;
    status.className = link.status === "stable" ? "status-stable" : "status-degraded";

    tr.append(a, b, score, status);
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
  text.textContent = `TX ${node.tx_power_dbm.toFixed(1)} dBm | Battery ${node.battery.toFixed(1)}%`;
  text.style.color = "var(--muted)";
  text.style.margin = "0 0 8px";

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
  card.append(top, text, controls, rebootBtn);
  return card;
}

export function renderNodes(container, nodes, onAction) {
  container.innerHTML = "";
  for (const node of nodes) {
    container.append(makeNodeCard(container.ownerDocument, node, onAction));
  }
}

export function drawTopology(canvas, nodes, links) {
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
    ctx.lineWidth = Math.max(1, link.score * 3);
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

function showToast(el, text) {
  el.textContent = text;
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 1200);
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

export function applyState(state, dom, onAction) {
  dom.tickLabel.textContent = `Tick ${state.tick}`;
  renderKpis(dom.kpiGrid, state.kpis);
  renderLinks(dom.linksBody, state.links);
  renderNodes(dom.nodesList, state.nodes, onAction);
  drawTopology(dom.canvas, state.nodes, state.links);
}

function collectDom(documentRef) {
  return {
    refreshBtn: documentRef.getElementById("refresh-btn"),
    tickLabel: documentRef.getElementById("tick-label"),
    kpiGrid: documentRef.getElementById("kpi-grid"),
    nodesList: documentRef.getElementById("nodes-list"),
    linksBody: documentRef.getElementById("links-body"),
    canvas: documentRef.getElementById("topology-canvas"),
    toast: documentRef.getElementById("toast")
  };
}

export async function bootstrap(documentRef = document, windowRef = window) {
  const dom = collectDom(documentRef);

  async function refresh() {
    const state = await fetch(API_STATE).then((r) => r.json());
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

  dom.refreshBtn.addEventListener("click", refresh);
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

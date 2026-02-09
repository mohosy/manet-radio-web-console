# MANET Radio Web Console

![Language](https://img.shields.io/badge/frontend-JavaScript%20%2B%20HTML%2FCSS-f7df1e)
![Backend](https://img.shields.io/badge/backend-Python-3776AB)
![Native](https://img.shields.io/badge/native-C-555)
![License](https://img.shields.io/badge/license-MIT-blue)

A Silvus-style embedded web interface project for managing MANET radios. The stack combines a Python network-management backend, mobile-friendly JavaScript UI, a native C RF metric library, route analytics, and automated API/UI test coverage.

![Demo](docs/demo.svg)

## Why This Matches the Embedded Web Interface Role
- **JavaScript + HTML**: responsive, field-usable network control interface.
- **Python backend**: control-plane APIs, telemetry simulator, and topology/routing logic.
- **Mobile web development**: adaptive layout designed for tablets and laptops.
- **UI test automation**: deterministic `jsdom` tests for rendering and state updates.
- **C programming**: native link-quality and capacity estimation loaded via `ctypes`.

## Advanced Features Added
- Real-time topology map with live link quality overlays.
- Rich per-link telemetry:
  - quality score
  - ETX estimate
  - latency estimate
  - throughput estimate
- Multi-hop route analysis (`src -> dst`) via Dijkstra over dynamic link costs.
- Auto channel optimization endpoint with evented change tracking.
- R1 routing summary table with latency and bottleneck throughput.
- Event log stream (node health, updates, optimization events, telemetry snapshots).
- Node controls for TX power, channel assignment, and reboot simulation.

## API Surface
- `GET /api/health`
- `GET /api/state`
- `GET /api/route?src=R1&dst=R5`
- `GET /api/events/log`
- `GET /api/events` (SSE)
- `POST /api/node/<id>/tx_power`
- `POST /api/node/<id>/channel`
- `POST /api/node/<id>/reboot`
- `POST /api/network/optimize_channels`

## Architecture
```mermaid
flowchart LR
  A[Web UI (JS/HTML/CSS)] -->|REST/SSE| B[Python Control Server]
  B --> C[MANET Simulator]
  C --> D[Link Graph + Route Engine]
  C --> E[C RF Metric Library]
  D --> F[Routing Summary + KPIs]
```

Core files:
- `/Users/mo/Downloads/manet-radio-web-console/backend/server.py`
- `/Users/mo/Downloads/manet-radio-web-console/backend/manet_sim.py`
- `/Users/mo/Downloads/manet-radio-web-console/backend/native_bridge.py`
- `/Users/mo/Downloads/manet-radio-web-console/native/link_quality.c`
- `/Users/mo/Downloads/manet-radio-web-console/web/app.js`
- `/Users/mo/Downloads/manet-radio-web-console/tests/test_api.py`
- `/Users/mo/Downloads/manet-radio-web-console/tests/ui.test.mjs`

## Run
```bash
cd /Users/mo/Downloads/manet-radio-web-console
./scripts/build_native.sh
python3 -m backend.server --host 127.0.0.1 --port 8088
```

Open:
```text
http://127.0.0.1:8088
```

## Test
Python API/native tests:
```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

UI automation tests:
```bash
npm install
npm run test:ui
```

## Notes
- Native C library is optional; Python fallback metrics are used when shared object is absent.
- Route computation currently uses a shortest-path heuristic over ETX and latency cost.
- The simulator is intentionally structured to mirror embedded network-management software workflows.

## Author
Mo Shirmohammadi
- GitHub: [github.com/mohosy](https://github.com/mohosy)

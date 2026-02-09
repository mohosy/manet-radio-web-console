# MANET Radio Web Console

![Language](https://img.shields.io/badge/frontend-JavaScript%20%2B%20HTML%2FCSS-f7df1e)
![Backend](https://img.shields.io/badge/backend-Python-3776AB)
![Native](https://img.shields.io/badge/native-C-555)
![License](https://img.shields.io/badge/license-MIT-blue)

A Silvus-style embedded web interface project for managing MANET radios. It includes a Python network-management backend, a mobile-friendly JavaScript UI, a C-based link quality module, and UI/API test automation.

![Demo](docs/demo.svg)

## Why This Matches the Role
- **JavaScript + HTML**: responsive web interface for radio and link management.
- **Python backend**: network control APIs and telemetry simulation loop.
- **Mobile-friendly UI**: optimized layout and controls for tablet/field usage.
- **UI test automation**: automated frontend rendering checks with `jsdom`.
- **C programming**: native link-quality scoring function loaded via `ctypes`.

## Features
- Real-time topology map with stable/degraded link visualization.
- Node-level controls:
  - TX power updates
  - channel changes
  - reboot command
- KPI dashboard:
  - online/degraded nodes
  - average battery
  - average link score
  - degraded link count
- REST + SSE API for network state and live updates.

## Architecture
```mermaid
flowchart LR
  A[Web UI (JS/HTML)] -->|REST/SSE| B[Python Control Server]
  B --> C[MANET Simulator]
  C --> D[C Link Metric Engine]
  B --> E[Node + Link State]
```

Key files:
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
- Native C library is optional; Python fallback metric is used if the shared object is absent.
- This project is a simulation environment intentionally shaped like embedded network-management software.

## Author
Mo Shirmohammadi
- GitHub: [github.com/mohosy](https://github.com/mohosy)

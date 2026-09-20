# 🛡️ ResQRoute: Real-Time Hazard-Aware Evacuation & Autonomous Relief Dispatch Engine

> **A mission-critical disaster management software platform combining dynamic risk-weighted routing ($A^*$ with flood penalties), automated multi-factor emergency triage, and autonomous rescue fleet dispatch.**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![WebSockets](https://img.shields.io/badge/WebSockets-Real--Time-6366f1?style=for-the-badge)](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API)
[![Leaflet](https://img.shields.io/badge/GIS-Leaflet.js-199900?style=for-the-badge&logo=leaflet&logoColor=white)](https://leafletjs.com)
[![Tests](https://img.shields.io/badge/Tests-Passing%20(6/6)-10b981?style=for-the-badge)](https://docs.pytest.org)

---

## 📌 The Problem
During severe flash floods, cyclones, and wildfires:
1. **Standard GPS Apps Fail:** Commercial navigation services (Google Maps, Waze) optimize purely for distance or regular traffic delays. During a disaster, they routinely guide escaping civilians into submerged underpasses, washed-out bridges, or burning corridors.
2. **First Responders Overwhelmed:** Emergency helplines (911/112) experience catastrophic bottlenecking. First responders lack automated prioritization tools to triage distress calls based on casualty counts, infants/elderly presence, and medical urgency.
3. **Suboptimal Dispatch:** Ambulances and rescue boats are dispatched blindly, often hitting road blockages mid-route and turning back.

---

## 💡 The Solution: ResQRoute
ResQRoute bridges the gap with a dual-interface full-stack engine:
* **Citizen Evacuation Navigator (Mobile/PWA):** Calculates the fastest **hazard-free** path to the nearest operational high-ground shelter. If a river breaches or a road collapses mid-journey, the route dynamically recalculates in real-time. Includes an offline-cached shelter directory and a one-tap emergency SOS distress beacon.
* **Incident Commander Operations Center (First Responders):** Real-time tactical GIS console with live triage queue, hazard polygon drawing tools, fleet telemetry, and an **Autonomous Dispatch Engine** that pairs high-priority distress calls with optimal rescue vehicles.

---

## ⚙️ Core Technical Innovations

### 1. Dynamic Risk-Weighted Graph Routing ($A^*$)
Standard routing algorithms optimize for physical distance:
$$\text{Cost}(e) = \text{Distance}(e)$$

**ResQRoute calculates Risk-Weighted Evacuation Cost:**
$$\text{Cost}(e) = \text{Distance}(e) \times \left(1 + \sum \text{Hazard Penalties}(e)\right)$$

Using Shapely polygon-line intersection algorithms:
* If a road segment intersects an active **CRITICAL** flood zone ($\text{depth} \ge 1.0\text{m}$) or collapsed bridge:
  $$\text{Penalty} \to 10,000 \quad (\text{Effectively Impassable})$$
* The graph router automatically forces evacuation traffic away from floodplains and onto higher-ground highways (e.g. Western Expressway bypass).

### 2. Multi-Factor Objective Triage Scoring
SOS distress signals are dynamically ranked using an objective severity formulation:
$$\text{Score} = (N_{\text{casualties}} \times 10) + (N_{\text{vulnerable}} \times 25) + (M \times 50) + \left(\frac{T_{\text{wait}}}{60} \times 1.5\right)$$
* $N_{\text{casualties}}$: Number of trapped individuals
* $N_{\text{vulnerable}}$: Infants or elderly individuals requiring assistance
* $M$: Medical emergency boolean ($1$ if true, $0$ if false)
* $T_{\text{wait}}$: Elapsed seconds in queue (prevents starvation of lower-priority cases)

### 3. Autonomous Fleet Matching
Pairs available rescue vehicles (Ambulances, Zodiac Amphibious Boats, Heavy Rescue Trucks) to the highest-priority pending SOS calls based on adjusted transit time and vehicle capabilities.

---

## 🏗️ System Architecture

```
                                +---------------------------+
                                |  Citizen Evacuation App   |
                                |  (Mobile PWA / Offline)   |
                                +-------------+-------------+
                                              |
                          WebSocket Telemetry | REST APIs
                                              v
+-----------------------------------------------------------------------------------+
|                           ResQRoute FastAPI Backend                               |
|                                                                                   |
|  +--------------------+   +---------------------+   +--------------------------+  |
|  |   Graph Router     |   |    Triage Engine    |   |     Dispatch Engine      |  |
|  | - NetworkX Graph   |   | - Objective Scoring |   | - Safe-Path Unit Alloc   |  |
|  | - Shapely Hazards  |   | - Queue Priority    |   | - Fleet Telemetry        |  |
|  | - Dynamic Penalties|   | - Deduplication     |   | - ETA Tracking           |  |
|  +--------------------+   +---------------------+   +--------------------------+  |
|                                     |                                             |
|                                     v                                             |
|                         WebSocket Broadcast Hub                                   |
+-------------------------------------+---------------------------------------------+
                                      |
                                      v
                        +---------------------------+
                        |  Incident Commander HUD   |
                        | (Tactical GIS / Dispatch) |
                        +---------------------------+
```

---

## 🚀 Quick Start Guide

### Prerequisites
* Python 3.10+ (or [uv](https://github.com/astral-sh/uv))

### 1. Installation
```bash
# Clone the repository
git clone https://github.com/jagantj28-wq/ResQRoute-Real-Time-Hazard-Aware-Evacuation-Autonomous-Relief-Dispatch-Engine.git
cd ResQRoute-Real-Time-Hazard-Aware-Evacuation-Autonomous-Relief-Dispatch-Engine

# Install dependencies
pip install -r requirements.txt
```

### 2. Launch the Application
**On Windows:**
Double-click `run.bat` or run:
```powershell
.\run.ps1
```

**On Linux / macOS:**
```bash
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 3. Access Portals
* **Landing Hub:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
* **Citizen Evacuation Navigator:** [http://127.0.0.1:8000/citizen](http://127.0.0.1:8000/citizen)
* **Incident Commander Center:** [http://127.0.0.1:8000/dispatcher](http://127.0.0.1:8000/dispatcher)
* **Interactive API Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 🧪 Running Automated Tests

Run the complete test suite verifying routing, triage ranking, and dispatch matching:
```bash
pytest -v
```

```
tests/test_dispatch.py::test_triage_scoring PASSED                       [ 16%]
tests/test_dispatch.py::test_triage_queue_ranking PASSED                 [ 33%]
tests/test_dispatch.py::test_autonomous_dispatch_matching PASSED         [ 50%]
tests/test_router.py::test_nearest_node_lookup PASSED                    [ 66%]
tests/test_router.py::test_baseline_evacuation_routing PASSED            [ 83%]
tests/test_router.py::test_dynamic_hazard_avoidance_reroute PASSED       [100%]
============================== 6 passed in 0.65s ==============================
```

---

## 🎬 3-Minute Live Pitch / Demonstration Script

Follow this sequence when presenting to hackathon or competition judges:

1. **Step 1: Open Split Screen**
   * Open the **Incident Commander** (`/dispatcher`) on the left half of your screen.
   * Open the **Citizen Navigator** (`/citizen`) on the right half (mobile view).
2. **Step 2: Request Baseline Route**
   * In the Citizen app, click **"Find Safe Shelter"**.
   * Show the optimal path crossing the Central Causeway Bridge toward the North Hill Fortress.
3. **Step 3: Trigger the Disaster Simulation**
   * In the Commander console, click **"Phase 1: River Basin Surge"** and then **"Phase 2: Causeway Breach"**.
   * Watch the map: A red flood polygon appears over the causeway bridge.
   * In the Citizen view, point out the real-time banner: **"Alert: Causeway Breach reported! Auto-recalculating safe route..."**
   * The path dynamically recalculates through the Western Expressway bypass with zero user manual intervention!
4. **Step 4: Transmit SOS Distress Signal**
   * In the Citizen view, click the red **"SOS Beacon"** button. Select 4 casualties, 2 infants, and check "Urgent Medical Attention".
   * Click **Transmit Distress Beacon**.
   * Watch it immediately appear at the top of the Commander's **Triage Queue** ranked as **CRITICAL** (Priority Score: 140+).
5. **Step 5: Autonomous Dispatch**
   * In the Command Center, click **"Run Auto-Dispatch"**.
   * Show the system assigning the nearest available ambulance/rescue boat, drawing an orange safe route avoiding all floodwaters, and estimating exact arrival time (ETA).

---

## 📡 API Reference Overview

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/routing/safe-path` | Calculates risk-weighted evacuation path avoiding active hazards |
| `GET` | `/api/routing/shelters` | Lists emergency shelters with capacity, occupancy, and status |
| `GET` | `/api/hazards` | Retrieves all active flood and hazard polygons |
| `POST` | `/api/hazards` | Adds or updates a hazard polygon and broadcasts to all clients |
| `DELETE` | `/api/hazards/{id}` | Clears a resolved hazard from the road network |
| `POST` | `/api/sos` | Ingests emergency distress signal and ranks via triage scoring |
| `GET` | `/api/sos/queue` | Returns ranked emergency triage queue |
| `POST` | `/api/dispatch/auto` | Executes autonomous dispatch matching for the highest priority SOS |
| `POST` | `/api/simulation/step/{n}` | Triggers sequential phases of the disaster scenario |
| `WS` | `/ws` | Real-time WebSocket connection for live telemetry and threat alerts |

---

## 📄 License
This project is open source and available under the [MIT License](LICENSE).

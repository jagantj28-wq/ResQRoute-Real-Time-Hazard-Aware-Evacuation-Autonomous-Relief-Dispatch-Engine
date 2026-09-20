// ResQRoute Incident Commander Tactical Console
let map;
let networkData = null;
let edgeLayers = [];
let nodeMarkers = [];
let shelterMarkers = [];
let depotMarkers = [];
let unitMarkers = {};
let sosMarkers = {};
let hazardLayers = [];
let dispatchRouteLayers = [];

document.addEventListener("DOMContentLoaded", () => {
  initMap();
  loadNetworkData().then(() => {
    loadHazards();
    loadTriageQueue();
    loadFleet();
  });
  setupSocketListeners();
  logEvent("SYSTEM", "Tactical Command Center online. Monitoring network...");
});

function initMap() {
  map = L.map("dispatcher-map", {
    zoomControl: false,
    attributionControl: false
  }).setView([13.0827, 80.2650], 13);

  // CartoDB Dark Matter
  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    maxZoom: 19
  }).addTo(map);

  L.control.zoom({ position: "bottomright" }).addTo(map);
}

async function loadNetworkData() {
  try {
    const res = await fetch("/api/routing/network-data");
    networkData = await res.json();

    // 1. Draw Road Network Edges
    const nodeMap = {};
    networkData.nodes.forEach((n) => (nodeMap[n.id] = n));

    networkData.edges.forEach((e) => {
      const u = nodeMap[e.from];
      const v = nodeMap[e.to];
      if (u && v) {
        const line = L.polyline(
          [
            [u.lat, u.lng],
            [v.lat, v.lng]
          ],
          {
            color: "#374151",
            weight: 3,
            opacity: 0.8
          }
        ).addTo(map);
        edgeLayers.push(line);
      }
    });

    // 2. Draw Shelters
    networkData.shelters.forEach((s) => {
      const isOperational = s.status === "OPERATIONAL";
      const color = isOperational ? "#10b981" : "#ef4444";
      const icon = L.divIcon({
        className: "custom-marker",
        html: `<div style="background: ${color}; width: 28px; height: 28px; border-radius: 8px; border: 2px solid #fff; display: flex; align-items: center; justify-content: center; color: #fff; font-size: 13px; box-shadow: 0 0 10px ${color};"><i class="fa-solid fa-campground"></i></div>`,
        iconSize: [28, 28],
        iconAnchor: [14, 14]
      });
      const m = L.marker([s.lat, s.lng], { icon: icon }).addTo(map);
      m.bindPopup(`<b>${s.name}</b><br>Capacity: ${s.current_occupancy}/${s.capacity}<br>Elev: ${s.elevation}m`);
      shelterMarkers.push(m);
    });

    // 3. Draw Depots
    networkData.rescue_depots.forEach((d) => {
      const icon = L.divIcon({
        className: "custom-marker",
        html: `<div style="background: #6366f1; width: 26px; height: 26px; border-radius: 6px; border: 2px solid #fff; display: flex; align-items: center; justify-content: center; color: #fff; font-size: 12px; box-shadow: 0 0 8px #6366f1;"><i class="fa-solid fa-warehouse"></i></div>`,
        iconSize: [26, 26],
        iconAnchor: [13, 13]
      });
      const m = L.marker([d.lat, d.lng], { icon: icon }).addTo(map);
      m.bindPopup(`<b>${d.name}</b><br>Deployment Base`);
      depotMarkers.push(m);
    });
  } catch (e) {
    console.error("Error loading network data:", e);
  }
}

async function loadHazards() {
  try {
    const res = await fetch("/api/hazards");
    const hazards = await res.json();

    hazardLayers.forEach((l) => map.removeLayer(l));
    hazardLayers = [];

    hazards.forEach((h) => {
      if (h.polygon && h.polygon.length >= 3) {
        const color = h.severity === "CRITICAL" ? "#ef4444" : h.severity === "HIGH" ? "#f97316" : "#f59e0b";
        const poly = L.polygon(h.polygon, {
          color: color,
          fillColor: color,
          fillOpacity: 0.5,
          weight: 2,
          dashArray: h.passable ? "4, 4" : null
        }).addTo(map);

        poly.bindPopup(`
          <div style="color: #111827; font-family: sans-serif;">
            <h4 style="font-weight: bold; color: ${color};">${h.name}</h4>
            <p style="font-size: 11px;">Severity: <b>${h.severity}</b> (${h.water_depth_meters}m water)</p>
            <p style="font-size: 11px;">Passable: <b>${h.passable ? "Yes (Slow)" : "NO - ROAD CLOSED"}</b></p>
            <button onclick="removeHazard('${h.id}')" style="margin-top: 6px; background: #dc2626; color: white; border: none; padding: 3px 8px; border-radius: 4px; font-size: 11px; cursor: pointer;">Clear Hazard</button>
          </div>
        `);
        hazardLayers.push(poly);
      }
    });
  } catch (e) {
    console.error("Error loading hazards:", e);
  }
}

async function loadTriageQueue() {
  try {
    const res = await fetch("/api/sos/queue");
    const queue = await res.json();

    const listEl = document.getElementById("triage-queue-list");
    const countBadge = document.getElementById("sos-count-badge");
    const pendingList = queue.filter((s) => s.status !== "RESOLVED");

    countBadge.textContent = `${pendingList.length} Pending`;

    // Clear old map markers
    Object.values(sosMarkers).forEach((m) => map.removeLayer(m));
    sosMarkers = {};

    if (pendingList.length === 0) {
      listEl.innerHTML = `
        <div class="text-center py-8 text-gray-500 text-xs">
          <i class="fa-solid fa-shield-check text-2xl text-emerald-500/50 mb-2"></i>
          <p>No active SOS distress signals.</p>
        </div>
      `;
      return;
    }

    listEl.innerHTML = "";

    pendingList.forEach((s) => {
      const isCritical = s.priority_level === "CRITICAL";
      const isHigh = s.priority_level === "HIGH";
      const badgeColor = isCritical ? "bg-red-500/20 text-red-400 border-red-500/30" : isHigh ? "bg-amber-500/20 text-amber-400 border-amber-500/30" : "bg-sky-500/20 text-sky-400 border-sky-500/30";

      // Card in queue
      listEl.innerHTML += `
        <div class="p-3 rounded-xl bg-gray-900 border ${isCritical ? "border-red-500/40" : "border-gray-800"} space-y-2">
          <div class="flex items-center justify-between">
            <span class="font-mono font-bold text-xs text-white">${s.id}</span>
            <span class="px-2 py-0.5 rounded-full border text-[10px] font-bold ${badgeColor}">
              ${s.priority_level} (${s.priority_score})
            </span>
          </div>

          <div class="text-[11px] text-gray-300">
            <div><i class="fa-solid fa-users text-gray-500 mr-1"></i> Casualties: <b>${s.casualty_count}</b> ${s.infants_or_elderly > 0 ? `(${s.infants_or_elderly} infants/elderly)` : ""}</div>
            ${s.medical_emergency ? `<div class="text-red-400 font-bold"><i class="fa-solid fa-notes-medical mr-1"></i> Urgent Medical Emergency</div>` : ""}
            <div class="text-gray-400 truncate mt-0.5">${s.details || "No additional details provided."}</div>
          </div>

          <div class="flex items-center justify-between pt-1 border-t border-gray-800/80 text-[11px]">
            <span class="text-gray-400">Status: <b class="${s.status === "DISPATCHED" ? "text-amber-400" : "text-sky-400"}">${s.status}</b></span>
            <button onclick="resolveSos('${s.id}')" class="px-2 py-0.5 rounded bg-gray-800 hover:bg-gray-700 text-gray-300 text-[10px]">
              Resolve
            </button>
          </div>
        </div>
      `;

      // Map marker for SOS
      const markerHtml = `<div class="sos-pulse" style="width: 24px; height: 24px; background: ${isCritical ? "#ef4444" : "#f59e0b"}; border: 2px solid #fff; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-size: 11px;"><i class="fa-solid fa-bell"></i></div>`;
      const icon = L.divIcon({
        className: "custom-marker",
        html: markerHtml,
        iconSize: [24, 24],
        iconAnchor: [12, 12]
      });

      const marker = L.marker([s.lat, s.lng], { icon: icon }).addTo(map);
      marker.bindPopup(`
        <b>${s.id}</b> (${s.priority_level})<br>
        Casualties: ${s.casualty_count} (Vulnerable: ${s.infants_or_elderly})<br>
        Medical: ${s.medical_emergency ? "YES" : "No"}<br>
        Status: ${s.status}<br>
        <button onclick="resolveSos('${s.id}')" style="margin-top: 4px; background: #059669; color: white; border: none; padding: 2px 6px; border-radius: 4px; font-size: 10px; cursor: pointer;">Mark Rescued</button>
      `);
      sosMarkers[s.id] = marker;
    });
  } catch (e) {
    console.error("Error loading triage queue:", e);
  }
}

async function loadFleet() {
  try {
    const res = await fetch("/api/dispatch/units");
    const units = await res.json();

    const listEl = document.getElementById("fleet-list");
    listEl.innerHTML = "";

    // Clear old unit markers
    Object.values(unitMarkers).forEach((m) => map.removeLayer(m));
    unitMarkers = {};

    units.forEach((u) => {
      const isAvailable = u.status === "AVAILABLE";
      const statusColor = isAvailable ? "text-emerald-400" : "text-amber-400";
      const iconSymbol = u.type === "AMBULANCE" ? "fa-truck-medical" : u.type === "RESCUE_BOAT" ? "fa-ship" : "fa-truck";

      listEl.innerHTML += `
        <div class="p-2 rounded-lg bg-gray-900/60 border border-gray-800 text-[11px] flex items-center justify-between">
          <div class="flex items-center gap-2">
            <i class="fa-solid ${iconSymbol} text-sky-400"></i>
            <div>
              <div class="font-bold text-gray-200 text-xs truncate w-36">${u.name}</div>
              <div class="text-[10px] text-gray-400">Speed: ${u.speed_kmh}km/h • Cap: ${u.capacity}</div>
            </div>
          </div>
          <span class="font-mono text-[10px] font-bold ${statusColor}">${u.status}</span>
        </div>
      `;

      // Map marker
      const markerColor = isAvailable ? "#10b981" : "#f59e0b";
      const icon = L.divIcon({
        className: "custom-marker",
        html: `<div style="background: ${markerColor}; width: 22px; height: 22px; border-radius: 50%; border: 2px solid #fff; display: flex; align-items: center; justify-content: center; color: white; font-size: 10px; box-shadow: 0 0 8px ${markerColor};"><i class="fa-solid ${iconSymbol}"></i></div>`,
        iconSize: [22, 22],
        iconAnchor: [11, 11]
      });

      const m = L.marker([u.lat, u.lng], { icon: icon }).addTo(map);
      m.bindPopup(`<b>${u.name}</b><br>Type: ${u.type}<br>Status: ${u.status}`);
      unitMarkers[u.id] = m;
    });
  } catch (e) {
    console.error("Error loading fleet:", e);
  }
}

async function triggerAutonomousDispatch() {
  try {
    logEvent("DISPATCH", "Calculating optimal safe-path fleet assignment...");
    const res = await fetch("/api/dispatch/auto", { method: "POST" });
    const action = await res.json();

    if (!action) {
      alert("No pending SOS signals or no available rescue vehicles!");
      logEvent("DISPATCH", "No pending SOS alerts requiring immediate dispatch.");
      return;
    }

    logEvent("SUCCESS", `Unit ${action.unit_id} dispatched to ${action.sos_id}. ETA: ${action.eta_minutes} mins.`);

    // Draw dispatch route line
    if (action.route_coords && action.route_coords.length > 0) {
      const line = L.polyline(action.route_coords, {
        color: "#f59e0b",
        weight: 5,
        dashArray: "6, 6",
        opacity: 0.95
      }).addTo(map);
      dispatchRouteLayers.push(line);
      map.fitBounds(line.getBounds(), { padding: [50, 50] });
    }

    loadFleet();
    loadTriageQueue();
  } catch (e) {
    console.error("Dispatch error:", e);
  }
}

async function resolveSos(sosId) {
  try {
    await fetch(`/api/sos/${sosId}/resolve`, { method: "POST" });
    logEvent("RESOLVED", `SOS distress beacon ${sosId} marked resolved.`);
    loadTriageQueue();
  } catch (e) {
    console.error("Resolve error:", e);
  }
}

async function resetFleet() {
  try {
    await fetch("/api/dispatch/reset", { method: "POST" });
    dispatchRouteLayers.forEach((l) => map.removeLayer(l));
    dispatchRouteLayers = [];
    logEvent("FLEET", "Rescue fleet reset to standby deployment depots.");
    loadFleet();
  } catch (e) {
    console.error("Reset fleet error:", e);
  }
}

async function removeHazard(hazardId) {
  try {
    await fetch(`/api/hazards/${hazardId}`, { method: "DELETE" });
    logEvent("HAZARD", `Hazard zone ${hazardId} cleared from network.`);
    loadHazards();
  } catch (e) {
    console.error("Remove hazard error:", e);
  }
}

// Simulation Deck
async function triggerSimStep(step) {
  try {
    logEvent("SIMULATION", `Executing scenario Phase ${step}...`);
    const res = await fetch(`/api/simulation/step/${step}`, { method: "POST" });
    const data = await res.json();

    // Highlight button
    for (let i = 1; i <= 4; i++) {
      const btn = document.getElementById(`sim-btn-${i}`);
      if (btn) {
        if (i === step) {
          btn.classList.add("border-sky-500", "bg-gray-800");
        } else if (i < step) {
          btn.classList.add("border-emerald-500/40");
        }
      }
    }

    loadHazards();
    loadTriageQueue();
    loadFleet();
  } catch (e) {
    console.error("Sim error:", e);
  }
}

async function resetSimulation() {
  try {
    await fetch("/api/simulation/reset", { method: "POST" });
    dispatchRouteLayers.forEach((l) => map.removeLayer(l));
    dispatchRouteLayers = [];

    for (let i = 1; i <= 4; i++) {
      const btn = document.getElementById(`sim-btn-${i}`);
      if (btn) {
        btn.className = "w-full text-left p-2.5 rounded-xl bg-gray-900 hover:bg-gray-800 border border-gray-800 flex items-center justify-between transition-all";
      }
    }

    logEvent("SIMULATION", "Disaster scenario reset. Baseline network restored.");
    loadHazards();
    loadTriageQueue();
    loadFleet();
  } catch (e) {
    console.error("Sim reset error:", e);
  }
}

// Manual Hazard Injection
function openHazardModal() {
  document.getElementById("hazard-modal").classList.remove("hidden");
}

function closeHazardModal() {
  document.getElementById("hazard-modal").classList.add("hidden");
}

async function submitHazardInjection() {
  const preset = document.getElementById("hazard-preset").value;
  const severity = document.getElementById("hazard-severity").value;

  let polygon = [];
  let name = "";

  if (preset === "river_bridge") {
    name = "River Bridge Flood Breach";
    polygon = [
      [13.0750, 80.2680],
      [13.0760, 80.2880],
      [13.0660, 80.2870],
      [13.0650, 80.2670]
    ];
  } else if (preset === "grand_boulevard") {
    name = "Grand Boulevard Flash Flood";
    polygon = [
      [13.0840, 80.2450],
      [13.0840, 80.2550],
      [13.0760, 80.2550],
      [13.0760, 80.2450]
    ];
  } else {
    name = "Marina Coastal Storm Surge";
    polygon = [
      [13.0680, 80.2900],
      [13.0680, 80.3050],
      [13.0580, 80.3050],
      [13.0580, 80.2900]
    ];
  }

  const payload = {
    id: `HAZ-MANUAL-${Date.now()}`,
    name: name,
    type: "FLOOD",
    severity: severity,
    water_depth_meters: severity === "CRITICAL" ? 1.5 : 0.4,
    passable: severity !== "CRITICAL",
    polygon: polygon,
    description: "Manual threat injection from Command Center."
  };

  try {
    await fetch("/api/hazards", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    closeHazardModal();
    logEvent("HAZARD", `Hazard '${name}' [${severity}] injected into network.`);
    loadHazards();
  } catch (e) {
    console.error("Inject hazard error:", e);
  }
}

// Log utility
function logEvent(tag, message) {
  const container = document.getElementById("event-log-container");
  if (!container) return;

  const timeStr = new Date().toLocaleTimeString();
  const colors = {
    SYSTEM: "text-gray-400",
    DISPATCH: "text-amber-400",
    SUCCESS: "text-emerald-400",
    SIMULATION: "text-indigo-400",
    HAZARD: "text-rose-400",
    RESOLVED: "text-sky-400"
  };
  const colorClass = colors[tag] || "text-gray-300";

  container.innerHTML = `
    <div class="leading-relaxed border-b border-gray-900 pb-1">
      <span class="text-gray-600">[${timeStr}]</span>
      <span class="${colorClass} font-bold">[${tag}]</span>
      <span class="text-gray-300">${message}</span>
    </div>
  ` + container.innerHTML;
}

function clearLogs() {
  const container = document.getElementById("event-log-container");
  if (container) container.innerHTML = "";
}

function setupSocketListeners() {
  window.resqSocket.on("HAZARD_UPDATED", (msg) => {
    logEvent("HAZARD", `Active hazard updated: ${msg.data?.name}`);
    loadHazards();
  });

  window.resqSocket.on("HAZARD_REMOVED", (msg) => {
    logEvent("HAZARD", `Hazard removed: ${msg.hazard_id}`);
    loadHazards();
  });

  window.resqSocket.on("SOS_ALERT", (msg) => {
    logEvent("SOS", `Distress alert received: ${msg.data?.id} (Priority: ${msg.data?.priority_score})`);
    loadTriageQueue();
  });

  window.resqSocket.on("SOS_RESOLVED", (msg) => {
    logEvent("RESOLVED", `SOS marked resolved: ${msg.sos_id}`);
    loadTriageQueue();
  });

  window.resqSocket.on("UNIT_DISPATCHED", (msg) => {
    logEvent("DISPATCH", `Autonomous deployment: Unit ${msg.data?.unit_id} -> SOS ${msg.data?.sos_id}`);
    loadFleet();
    loadTriageQueue();
  });

  window.resqSocket.on("SIM_STEP_EVENT", (msg) => {
    logEvent("SIMULATION", `${msg.title}: ${msg.message}`);
    loadHazards();
    loadTriageQueue();
    loadFleet();
  });

  window.resqSocket.on("SIM_RESET", (msg) => {
    logEvent("SIMULATION", msg.message);
    loadHazards();
    loadTriageQueue();
    loadFleet();
  });
}

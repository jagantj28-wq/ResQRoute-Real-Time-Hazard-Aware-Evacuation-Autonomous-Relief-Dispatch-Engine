// ResQRoute Citizen Evacuation App Logic
let map;
let userMarker;
let routeLine = null;
let shelterMarkers = [];
let hazardLayers = [];
let activeRouteData = null;
let cachedShelters = [];

// Default starting point: South Bay Residential Sector (N9)
let userLocation = { lat: 13.0550, lng: 80.2750 };

document.addEventListener("DOMContentLoaded", () => {
  initMap();
  loadShelters();
  loadHazards();
  setupSocketListeners();
  registerServiceWorker();
});

function initMap() {
  map = L.map("citizen-map", {
    zoomControl: false,
    attributionControl: false
  }).setView([userLocation.lat, userLocation.lng], 13);

  // CartoDB Dark Matter tiles (reliable and fast)
  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    maxZoom: 19
  }).addTo(map);

  L.control.zoom({ position: "bottomright" }).addTo(map);

  // User Marker
  const userIcon = L.divIcon({
    className: "custom-marker",
    html: `<div style="width: 28px; height: 28px; background: #38bdf8; border: 3px solid #ffffff; border-radius: 50%; box-shadow: 0 0 15px #38bdf8; display: flex; align-items: center; justify-content: center; color: #0b0f19; font-size: 14px;"><i class="fa-solid fa-person"></i></div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14]
  });

  userMarker = L.marker([userLocation.lat, userLocation.lng], {
    draggable: true,
    icon: userIcon
  }).addTo(map);

  userMarker.on("dragend", (e) => {
    const pos = e.target.getLatLng();
    userLocation = { lat: pos.lat, lng: pos.lng };
    if (activeRouteData) {
      findSafeRoute(); // Auto-recalculate if user moves
    }
  });
}

async function loadShelters() {
  try {
    const res = await fetch("/api/routing/shelters");
    const shelters = await res.json();
    cachedShelters = shelters;
    localStorage.setItem("resq_cached_shelters", JSON.stringify(shelters));

    shelterMarkers.forEach((m) => map.removeLayer(m));
    shelterMarkers = [];

    const listEl = document.getElementById("shelter-list");
    if (listEl) listEl.innerHTML = "";

    shelters.forEach((s) => {
      const isOperational = s.status === "OPERATIONAL";
      const isFull = s.current_occupancy >= s.capacity;
      const bgColor = !isOperational ? "#ef4444" : isFull ? "#f59e0b" : "#10b981";

      const icon = L.divIcon({
        className: "shelter-icon",
        html: `<div style="width: 32px; height: 32px; background: ${bgColor}; border: 2px solid #ffffff; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: white; font-size: 14px; box-shadow: 0 0 10px ${bgColor};"><i class="fa-solid fa-campground"></i></div>`,
        iconSize: [32, 32],
        iconAnchor: [16, 16]
      });

      const marker = L.marker([s.lat, s.lng], { icon: icon }).addTo(map);
      marker.bindPopup(`
        <div style="font-family: sans-serif; color: #111827; min-width: 160px;">
          <h4 style="font-weight: bold; margin-bottom: 4px;">${s.name}</h4>
          <p style="font-size: 11px; margin: 2px 0;">Status: <b>${s.status}</b></p>
          <p style="font-size: 11px; margin: 2px 0;">Occupancy: <b>${s.current_occupancy} / ${s.capacity}</b></p>
          <p style="font-size: 11px; margin: 2px 0;">Elevation: <b>${s.elevation}m ASL</b></p>
          <button onclick="routeToSpecificShelter('${s.node_id}')" style="margin-top: 6px; width: 100%; background: #0284c7; color: white; border: none; padding: 4px 8px; border-radius: 4px; font-size: 11px; cursor: pointer; font-weight: bold;">Evacuate Here</button>
        </div>
      `);
      shelterMarkers.push(marker);

      // Populate Drawer
      if (listEl) {
        listEl.innerHTML += `
          <div class="p-3.5 rounded-xl bg-gray-900 border border-gray-800 flex items-center justify-between">
            <div>
              <div class="font-bold text-xs text-white">${s.name}</div>
              <div class="text-[11px] text-gray-400 mt-0.5">Occupancy: ${s.current_occupancy}/${s.capacity} • Elev: ${s.elevation}m</div>
            </div>
            <button onclick="routeToSpecificShelter('${s.node_id}')" class="px-2.5 py-1 rounded bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold">
              Route
            </button>
          </div>
        `;
      }
    });
  } catch (e) {
    console.warn("Could not load fresh shelters, checking cache...", e);
    const cached = localStorage.getItem("resq_cached_shelters");
    if (cached) {
      document.getElementById("network-offline-badge")?.classList.remove("hidden");
    }
  }
}

async function loadHazards() {
  try {
    const res = await fetch("/api/hazards");
    const hazards = await res.json();
    renderHazards(hazards);
  } catch (e) {
    console.error("Error loading hazards:", e);
  }
}

function renderHazards(hazards) {
  hazardLayers.forEach((l) => map.removeLayer(l));
  hazardLayers = [];

  hazards.forEach((h) => {
    if (h.polygon && h.polygon.length >= 3) {
      const color = h.severity === "CRITICAL" ? "#ef4444" : h.severity === "HIGH" ? "#f97316" : "#f59e0b";
      const poly = L.polygon(h.polygon, {
        color: color,
        fillColor: color,
        fillOpacity: 0.45,
        weight: 2,
        dashArray: h.passable ? "4, 4" : null
      }).addTo(map);

      poly.bindPopup(`
        <div style="color: #111827; font-family: sans-serif;">
          <h4 style="font-weight: bold; color: ${color};">${h.name}</h4>
          <p style="font-size: 11px;">Severity: <b>${h.severity}</b></p>
          <p style="font-size: 11px;">Water Depth: <b>${h.water_depth_meters}m</b></p>
          <p style="font-size: 11px;">Passable: <b>${h.passable ? "Yes (Slow)" : "NO - CLOSED"}</b></p>
          <p style="font-size: 11px; margin-top: 4px; color: #4b5563;">${h.description || ""}</p>
        </div>
      `);
      hazardLayers.push(poly);
    }
  });
}

async function findSafeRoute(destinationNode = null) {
  try {
    const payload = {
      origin_lat: userLocation.lat,
      origin_lng: userLocation.lng,
      destination_node: destinationNode,
      avoid_hazards: true
    };

    const res = await fetch("/api/routing/safe-path", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const routeData = await res.json();
    if (!routeData.success || routeData.path_coords.length === 0) {
      alert("No passable evacuation route found! All exits are currently compromised by severe hazards. Seek immediate vertical shelter.");
      return;
    }

    activeRouteData = routeData;
    drawRoute(routeData);
  } catch (e) {
    console.error("Routing error:", e);
  }
}

function routeToSpecificShelter(nodeId) {
  toggleShelterDrawer(false);
  findSafeRoute(nodeId);
}

function drawRoute(data) {
  if (routeLine) {
    map.removeLayer(routeLine);
  }

  // Draw glowing cyan evacuation path
  routeLine = L.polyline(data.path_coords, {
    color: "#38bdf8",
    weight: 6,
    opacity: 0.9,
    lineJoin: "round"
  }).addTo(map);

  map.fitBounds(routeLine.getBounds(), { padding: [60, 60] });

  // Update HUD
  const hud = document.getElementById("nav-hud");
  hud.classList.remove("hidden");
  document.getElementById("hud-dest-name").textContent = data.destination_shelter ? data.destination_shelter.name : "Safe Shelter (" + data.destination_node + ")";
  document.getElementById("hud-dist").textContent = data.total_distance_km;
  document.getElementById("hud-eta").textContent = data.estimated_time_minutes;
  document.getElementById("hud-hazards-avoided").textContent = data.hazards_avoided_count;
}

function clearRoute() {
  if (routeLine) {
    map.removeLayer(routeLine);
    routeLine = null;
  }
  activeRouteData = null;
  document.getElementById("nav-hud").classList.add("hidden");
  document.getElementById("route-alert-banner").classList.add("hidden");
}

function setupSocketListeners() {
  window.resqSocket.on("HAZARD_UPDATED", (msg) => {
    console.log("[Citizen] Hazard updated event received:", msg);
    loadHazards();
    triggerDynamicRerouteCheck(msg.data?.name || "Active Hazard");
  });

  window.resqSocket.on("HAZARD_REMOVED", () => {
    loadHazards();
  });

  window.resqSocket.on("SIM_STEP_EVENT", (msg) => {
    loadHazards();
    if (msg.step === 2 || msg.step === 1) {
      triggerDynamicRerouteCheck(msg.title);
    }
  });

  window.resqSocket.on("SIM_RESET", () => {
    loadHazards();
    clearRoute();
  });
}

function triggerDynamicRerouteCheck(reason) {
  if (!activeRouteData) return;

  const banner = document.getElementById("route-alert-banner");
  banner.classList.remove("hidden");
  banner.querySelector("span").textContent = `Alert: ${reason} reported! Auto-recalculating safe route...`;

  setTimeout(() => {
    findSafeRoute(activeRouteData.destination_node);
    setTimeout(() => {
      banner.classList.add("hidden");
    }, 4000);
  }, 1200);
}

// SOS Logic
function openSosModal() {
  document.getElementById("sos-modal").classList.remove("hidden");
}

function closeSosModal() {
  document.getElementById("sos-modal").classList.add("hidden");
}

function adjustCounter(id, change) {
  const el = document.getElementById(id);
  let val = parseInt(el.textContent, 10) + change;
  if (val < 0) val = 0;
  el.textContent = val;
}

async function submitEmergencySos() {
  const casualties = parseInt(document.getElementById("sos-casualties").textContent, 10);
  const vulnerable = parseInt(document.getElementById("sos-vulnerable").textContent, 10);
  const medical = document.getElementById("sos-medical").checked;
  const details = document.getElementById("sos-details").value;

  const payload = {
    lat: userLocation.lat,
    lng: userLocation.lng,
    casualty_count: casualties,
    infants_or_elderly: vulnerable,
    medical_emergency: medical,
    details: details
  };

  try {
    const res = await fetch("/api/sos", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const result = await res.json();
    closeSosModal();
    alert(`Distress SOS Beacon Transmitted!\n\nID: ${result.id}\nPriority Score: ${result.priority_score} (${result.priority_level})\n\nFirst responders have been notified. Stay in high-ground shelter.`);
  } catch (e) {
    alert("Beacon queued for background sync when network reconnects.");
    closeSosModal();
  }
}

function toggleShelterDrawer(forceState = null) {
  const drawer = document.getElementById("shelter-drawer");
  if (forceState !== null) {
    drawer.classList.toggle("hidden", !forceState);
  } else {
    drawer.classList.toggle("hidden");
  }
}

function registerServiceWorker() {
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/citizen-static/sw.js").catch((err) => {
      console.log("SW registration skipped:", err);
    });
  }
}

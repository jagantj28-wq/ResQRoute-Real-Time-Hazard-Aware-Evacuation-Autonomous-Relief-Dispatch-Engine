from fastapi import APIRouter
from typing import Dict, Any
import time
from backend.app.models.schemas import Hazard, HazardType, HazardSeverity, SOSRequest, SOSPriority
from backend.app.core.graph_router import GraphRouter
from backend.app.core.triage import triage_engine
from backend.app.core.dispatch_engine import DispatchEngine
from backend.app.websockets.manager import manager

router = APIRouter(prefix="/api/simulation", tags=["simulation"])
graph_router_instance: GraphRouter = None
dispatch_engine_instance: DispatchEngine = None

def set_dependencies(gr: GraphRouter, de: DispatchEngine):
    global graph_router_instance, dispatch_engine_instance
    graph_router_instance = gr
    dispatch_engine_instance = de

sim_state = {
    "current_step": 0,
    "active": False,
    "scenario": "Coastal Basin Category 4 Flash Flood & Causeway Submersion"
}

@router.get("/status")
async def get_simulation_status():
    return sim_state

@router.post("/step/{step_number}")
async def run_simulation_step(step_number: int):
    if not graph_router_instance or not dispatch_engine_instance:
        return {"error": "Engines not ready"}

    sim_state["current_step"] = step_number
    sim_state["active"] = True

    if step_number == 1:
        # Step 1: River Basin Rising
        h1 = Hazard(
            id="SIM-HAZ-1",
            name="River Basin Inundation Zone",
            type=HazardType.FLOOD,
            severity=HazardSeverity.MEDIUM,
            water_depth_meters=0.35,
            passable=True,
            polygon=[
                [13.0760, 80.2550],
                [13.0770, 80.2850],
                [13.0680, 80.2830],
                [13.0670, 80.2570]
            ],
            description="Rising water along riverbanks; slow transit advisory."
        )
        graph_router_instance.add_or_update_hazard(h1)
        await manager.broadcast({
            "type": "SIM_STEP_EVENT",
            "step": 1,
            "title": "Phase 1: River Basin Water Rising",
            "message": "Heavy monsoon rainfall has caused water to surge along River Corridor. Roads are slippery with minor pooling.",
            "hazard": h1.model_dump()
        })
        return {"success": True, "step": 1, "description": "Phase 1 triggered"}

    elif step_number == 2:
        # Step 2: Causeway Breach - Bridge Impassable
        h2 = Hazard(
            id="SIM-HAZ-2",
            name="East River Causeway Bridge Breach",
            type=HazardType.FLOOD,
            severity=HazardSeverity.CRITICAL,
            water_depth_meters=1.65,
            passable=False,
            polygon=[
                [13.0750, 80.2680],
                [13.0760, 80.2880],
                [13.0660, 80.2870],
                [13.0650, 80.2670]
            ],
            description="CRITICAL: Causeway flooded under 1.65m water. Road completely closed."
        )
        graph_router_instance.add_or_update_hazard(h2)
        await manager.broadcast({
            "type": "SIM_STEP_EVENT",
            "step": 2,
            "title": "Phase 2: Causeway Bridge Submerged",
            "message": "Water levels have breached the East Causeway. Central-South arterial route is impassable! Rerouting required.",
            "hazard": h2.model_dump()
        })
        return {"success": True, "step": 2, "description": "Phase 2 triggered"}

    elif step_number == 3:
        # Step 3: Urgent SOS Distress Call
        sos1 = SOSRequest(
            id="SOS-SIM-88",
            lat=13.0550,
            lng=80.2750,
            nearest_node="N9",
            casualty_count=4,
            infants_or_elderly=2,
            medical_emergency=True,
            details="Family with 2 infants stranded on 1st floor balcony. Ground floor submerged. Immediate boat/medic needed.",
            phone_contact="+1-555-0192"
        )
        ingested = triage_engine.ingest_sos(sos1)
        await manager.broadcast({
            "type": "SIM_STEP_EVENT",
            "step": 3,
            "title": "Phase 3: Emergency Distress SOS Ingested",
            "message": f"Critical SOS {ingested.id} received: 4 people stranded (2 infants) with medical need. Priority Score: {ingested.priority_score}",
            "sos": ingested.model_dump()
        })
        return {"success": True, "step": 3, "description": "Phase 3 triggered"}

    elif step_number == 4:
        # Step 4: Autonomous Dispatch & Safe Bypass Routing
        action = dispatch_engine_instance.autonomous_dispatch_next()
        await manager.broadcast({
            "type": "SIM_STEP_EVENT",
            "step": 4,
            "title": "Phase 4: Autonomous Safe-Path Dispatch Activated",
            "message": f"Unit {action.unit_id if action else 'Fleet'} deployed via western high-ground bypass around submerged bridge! ETA: {action.eta_minutes if action else 0} mins.",
            "dispatch": action.model_dump() if action else None
        })
        return {"success": True, "step": 4, "dispatch": action.model_dump() if action else None}

    return {"error": "Unknown step"}

@router.post("/reset")
async def reset_simulation():
    if not graph_router_instance or not dispatch_engine_instance:
        return {"error": "Engines not ready"}

    # Clear hazards
    to_remove = [h_id for h_id in graph_router_instance.active_hazards.keys() if h_id.startswith("SIM-")]
    for hid in to_remove:
        graph_router_instance.remove_hazard(hid)

    # Clear SOS
    to_remove_sos = [s_id for s_id in triage_engine.sos_registry.keys() if s_id.startswith("SOS-SIM-")]
    for sid in to_remove_sos:
        del triage_engine.sos_registry[sid]

    # Reset units
    dispatch_engine_instance.load_units_from_depots()
    sim_state["current_step"] = 0
    sim_state["active"] = False

    await manager.broadcast({
        "type": "SIM_RESET",
        "message": "Simulation cleared and network reset to baseline state."
    })
    return {"success": True, "message": "Simulation reset successfully"}

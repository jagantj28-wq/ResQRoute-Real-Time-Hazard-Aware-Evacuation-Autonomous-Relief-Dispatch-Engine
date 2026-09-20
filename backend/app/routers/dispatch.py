from fastapi import APIRouter, HTTPException
from typing import List, Optional
from backend.app.models.schemas import RescueUnit, RescueUnitStatus, DispatchAction
from backend.app.core.dispatch_engine import DispatchEngine
from backend.app.websockets.manager import manager

router = APIRouter(prefix="/api/dispatch", tags=["dispatch"])
dispatch_engine_instance: DispatchEngine = None

def set_engine(de: DispatchEngine):
    global dispatch_engine_instance
    dispatch_engine_instance = de

@router.get("/units", response_model=List[RescueUnit])
async def list_units():
    if not dispatch_engine_instance:
        return []
    return list(dispatch_engine_instance.units.values())

@router.post("/auto", response_model=Optional[DispatchAction])
async def trigger_auto_dispatch():
    if not dispatch_engine_instance:
        raise HTTPException(status_code=500, detail="Dispatch engine uninitialized")
    action = dispatch_engine_instance.autonomous_dispatch_next()
    if action:
        await manager.broadcast({
            "type": "UNIT_DISPATCHED",
            "data": action.model_dump()
        })
        return action
    return None

@router.post("/reset")
async def reset_units():
    if not dispatch_engine_instance:
        raise HTTPException(status_code=500, detail="Dispatch engine uninitialized")
    dispatch_engine_instance.load_units_from_depots()
    await manager.broadcast({
        "type": "UNITS_RESET",
        "units": [u.model_dump() for u in dispatch_engine_instance.units.values()]
    })
    return {"success": True, "message": "Fleet reset to home depots."}

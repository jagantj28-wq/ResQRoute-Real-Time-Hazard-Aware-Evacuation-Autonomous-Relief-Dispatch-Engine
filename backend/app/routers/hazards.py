from fastapi import APIRouter, HTTPException
from typing import List
import time
from backend.app.models.schemas import Hazard
from backend.app.core.graph_router import GraphRouter
from backend.app.core.config import settings
from backend.app.websockets.manager import manager

router = APIRouter(prefix="/api/hazards", tags=["hazards"])
graph_router_instance: GraphRouter = None

def set_router(gr: GraphRouter):
    global graph_router_instance
    graph_router_instance = gr

@router.get("", response_model=List[Hazard])
async def list_hazards():
    if not graph_router_instance:
        return []
    return list(graph_router_instance.active_hazards.values())

@router.post("", response_model=Hazard)
async def create_or_update_hazard(hazard: Hazard):
    if not graph_router_instance:
        raise HTTPException(status_code=500, detail="Graph router uninitialized")
    if not hazard.created_at:
        hazard.created_at = time.time()
    graph_router_instance.add_or_update_hazard(hazard)
    
    await manager.broadcast({
        "type": "HAZARD_UPDATED",
        "data": hazard.model_dump()
    })
    return hazard

@router.delete("/{hazard_id}")
async def delete_hazard(hazard_id: str):
    if not graph_router_instance:
        raise HTTPException(status_code=500, detail="Graph router uninitialized")
    graph_router_instance.remove_hazard(hazard_id)
    
    await manager.broadcast({
        "type": "HAZARD_REMOVED",
        "hazard_id": hazard_id
    })
    return {"success": True, "message": f"Hazard {hazard_id} cleared"}

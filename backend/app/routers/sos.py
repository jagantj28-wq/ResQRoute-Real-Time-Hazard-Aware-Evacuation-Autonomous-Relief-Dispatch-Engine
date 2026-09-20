from fastapi import APIRouter, HTTPException
from typing import List
import time
import uuid
from backend.app.models.schemas import SOSRequest, SOSStatus
from backend.app.core.triage import triage_engine
from backend.app.core.graph_router import GraphRouter
from backend.app.websockets.manager import manager

router = APIRouter(prefix="/api/sos", tags=["sos"])
graph_router_instance: GraphRouter = None

def set_router(gr: GraphRouter):
    global graph_router_instance
    graph_router_instance = gr

@router.post("", response_model=SOSRequest)
async def submit_sos(req: SOSRequest):
    if not req.id:
        req.id = f"SOS-{uuid.uuid4().hex[:6].upper()}"
    if not req.created_at:
        req.created_at = time.time()
    if not req.nearest_node and graph_router_instance:
        req.nearest_node = graph_router_instance.get_nearest_node(req.lat, req.lng)
        
    ingested = triage_engine.ingest_sos(req)
    
    await manager.broadcast({
        "type": "SOS_ALERT",
        "data": ingested.model_dump()
    })
    return ingested

@router.get("/queue", response_model=List[SOSRequest])
async def get_triage_queue():
    return triage_engine.get_ranked_queue()

@router.post("/{sos_id}/resolve")
async def resolve_sos(sos_id: str):
    try:
        updated = triage_engine.update_status(sos_id, SOSStatus.RESOLVED)
        await manager.broadcast({
            "type": "SOS_RESOLVED",
            "sos_id": sos_id
        })
        return {"success": True, "data": updated.model_dump()}
    except KeyError:
        raise HTTPException(status_code=404, detail="SOS not found")

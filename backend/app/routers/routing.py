from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from backend.app.models.schemas import RouteRequest, RouteResponse, Shelter
from backend.app.core.graph_router import GraphRouter

router = APIRouter(prefix="/api/routing", tags=["routing"])
graph_router_instance: GraphRouter = None

def set_router(gr: GraphRouter):
    global graph_router_instance
    graph_router_instance = gr

@router.post("/safe-path", response_model=RouteResponse)
async def compute_safe_path(req: RouteRequest):
    if not graph_router_instance:
        raise HTTPException(status_code=500, detail="Graph router uninitialized")
    
    res = graph_router_instance.compute_safe_route(
        origin_lat=req.origin_lat,
        origin_lng=req.origin_lng,
        destination_node=req.destination_node,
        avoid_hazards=req.avoid_hazards
    )
    return res

@router.get("/shelters", response_model=List[Shelter])
async def list_shelters():
    if not graph_router_instance:
        return []
    return [Shelter(**s) for s in graph_router_instance.shelters.values()]

@router.get("/network-data")
async def get_network_data():
    if not graph_router_instance:
        raise HTTPException(status_code=500, detail="Graph router uninitialized")
    return {
        "nodes": list(graph_router_instance.nodes.values()),
        "edges": graph_router_instance.edges,
        "shelters": list(graph_router_instance.shelters.values()),
        "hospitals": list(graph_router_instance.hospitals.values()),
        "rescue_depots": graph_router_instance.rescue_depots
    }

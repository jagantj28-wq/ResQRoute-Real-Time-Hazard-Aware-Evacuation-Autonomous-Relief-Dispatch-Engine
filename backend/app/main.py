from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import logging

from backend.app.core.config import settings
from backend.app.core.graph_router import GraphRouter
from backend.app.core.triage import triage_engine
from backend.app.core.dispatch_engine import DispatchEngine
from backend.app.websockets.manager import manager

from backend.app.routers import hazards, routing, sos, dispatch, simulation

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("resqroute.main")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize engines
router_instance = GraphRouter(str(settings.DATA_PATH))
dispatch_instance = DispatchEngine(router_instance, triage_engine)

# Inject dependencies
hazards.set_router(router_instance)
routing.set_router(router_instance)
sos.set_router(router_instance)
dispatch.set_engine(dispatch_instance)
simulation.set_dependencies(router_instance, dispatch_instance)

# Include API Routers
app.include_router(hazards.router)
app.include_router(routing.router)
app.include_router(sos.router)
app.include_router(dispatch.router)
app.include_router(simulation.router)

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo or heartbeat
            await websocket.send_text(f'{{"type":"ACK","received":"{data[:20]}"}}')
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"WS error: {e}")
        manager.disconnect(websocket)

# Static file mounting & UI Routes
BASE_DIR = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

app.mount("/shared", StaticFiles(directory=str(FRONTEND_DIR / "shared")), name="shared")
app.mount("/citizen-static", StaticFiles(directory=str(FRONTEND_DIR / "citizen")), name="citizen-static")
app.mount("/dispatcher-static", StaticFiles(directory=str(FRONTEND_DIR / "dispatcher")), name="dispatcher-static")

@app.get("/")
async def serve_index():
    return FileResponse(str(FRONTEND_DIR / "index.html"))

@app.get("/citizen")
async def serve_citizen():
    return FileResponse(str(FRONTEND_DIR / "citizen" / "index.html"))

@app.get("/dispatcher")
async def serve_dispatcher():
    return FileResponse(str(FRONTEND_DIR / "dispatcher" / "index.html"))

@app.get("/api/health")
async def health_check():
    return {
        "status": "HEALTHY",
        "system": settings.PROJECT_NAME,
        "nodes_loaded": len(router_instance.nodes),
        "edges_loaded": len(router_instance.edges),
        "shelters_count": len(router_instance.shelters),
        "units_available": len(dispatch_instance.get_available_units()),
        "active_hazards": len(router_instance.active_hazards)
    }

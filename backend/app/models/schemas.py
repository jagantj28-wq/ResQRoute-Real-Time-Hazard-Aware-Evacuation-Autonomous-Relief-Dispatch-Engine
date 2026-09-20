from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from enum import Enum

class HazardSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class HazardType(str, Enum):
    FLOOD = "FLOOD"
    ROAD_COLLAPSE = "ROAD_COLLAPSE"
    WILDFIRE = "WILDFIRE"
    DEBRIS = "DEBRIS"
    CHEMICAL_SPILL = "CHEMICAL_SPILL"

class Hazard(BaseModel):
    id: str
    name: str
    type: HazardType
    severity: HazardSeverity
    water_depth_meters: float = 0.0
    passable: bool = False
    polygon: List[List[float]]  # List of [lat, lng]
    created_at: float = 0.0
    description: Optional[str] = ""

class SOSPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class SOSStatus(str, Enum):
    PENDING = "PENDING"
    TRIAGED = "TRIAGED"
    DISPATCHED = "DISPATCHED"
    RESOLVED = "RESOLVED"

class SOSRequest(BaseModel):
    id: Optional[str] = None
    lat: float
    lng: float
    nearest_node: Optional[str] = None
    casualty_count: int = 1
    infants_or_elderly: int = 0
    medical_emergency: bool = False
    details: Optional[str] = ""
    phone_contact: Optional[str] = "ANONYMOUS"
    priority_score: float = 0.0
    priority_level: SOSPriority = SOSPriority.MEDIUM
    status: SOSStatus = SOSStatus.PENDING
    assigned_unit_id: Optional[str] = None
    created_at: float = 0.0

class Shelter(BaseModel):
    id: str
    name: str
    node_id: str
    lat: float
    lng: float
    elevation: float
    capacity: int
    current_occupancy: int
    resources: Dict[str, Any]
    status: str

class RescueUnitStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    DISPATCHED = "DISPATCHED"
    EN_ROUTE = "EN_ROUTE"
    ON_SCENE = "ON_SCENE"
    MAINTENANCE = "MAINTENANCE"

class RescueUnit(BaseModel):
    id: str
    name: str
    type: str
    speed_kmh: float
    capacity: int
    status: RescueUnitStatus = RescueUnitStatus.AVAILABLE
    lat: float
    lng: float
    current_node: str
    assigned_sos_id: Optional[str] = None
    current_route: List[str] = []

class RouteRequest(BaseModel):
    origin_lat: float
    origin_lng: float
    destination_node: Optional[str] = None
    avoid_hazards: bool = True
    vehicle_type: str = "FOOT_OR_LIGHT_VEHICLE"

class RouteResponse(BaseModel):
    success: bool
    origin_node: str
    destination_node: str
    destination_shelter: Optional[Shelter] = None
    path_nodes: List[str]
    path_coords: List[List[float]]
    total_distance_km: float
    estimated_time_minutes: float
    risk_score: float
    hazards_avoided_count: int
    status_message: str

class DispatchAction(BaseModel):
    unit_id: str
    sos_id: str
    route_nodes: List[str]
    route_coords: List[List[float]]
    eta_minutes: float

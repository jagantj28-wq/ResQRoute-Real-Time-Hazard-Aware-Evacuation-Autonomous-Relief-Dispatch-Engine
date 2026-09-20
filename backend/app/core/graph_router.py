import json
import math
import logging
from typing import Dict, List, Optional, Tuple, Any
import networkx as nx
from shapely.geometry import Point, LineString, Polygon
from backend.app.models.schemas import Hazard, HazardSeverity, Shelter, RouteResponse

logger = logging.getLogger("resqroute.router")

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

class GraphRouter:
    def __init__(self, data_path: str):
        self.data_path = data_path
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: List[Dict[str, Any]] = []
        self.shelters: Dict[str, Dict[str, Any]] = {}
        self.hospitals: Dict[str, Dict[str, Any]] = {}
        self.rescue_depots: List[Dict[str, Any]] = []
        self.active_hazards: Dict[str, Hazard] = {}
        self.graph = nx.Graph()
        self.load_network()

    def load_network(self):
        with open(self.data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        for n in data.get("nodes", []):
            self.nodes[n["id"]] = n
            self.graph.add_node(n["id"], lat=n["lat"], lng=n["lng"], elevation=n.get("elevation", 10.0), name=n.get("name", n["id"]))

        for e in data.get("edges", []):
            self.edges.append(e)
            self.graph.add_edge(
                e["from"],
                e["to"],
                id=e["id"],
                base_distance=e["distance_km"],
                speed_limit=e.get("speed_limit_kmh", 50),
                edge_type=e.get("type", "urban")
            )

        for s in data.get("shelters", []):
            self.shelters[s["id"]] = s

        for h in data.get("hospitals", []):
            self.hospitals[h["id"]] = h

        self.rescue_depots = data.get("rescue_depots", [])
        logger.info(f"Loaded network: {len(self.nodes)} nodes, {len(self.edges)} edges, {len(self.shelters)} shelters")

    def add_or_update_hazard(self, hazard: Hazard):
        self.active_hazards[hazard.id] = hazard
        logger.info(f"Hazard added/updated: {hazard.id} ({hazard.name}, {hazard.severity})")

    def remove_hazard(self, hazard_id: str):
        if hazard_id in self.active_hazards:
            del self.active_hazards[hazard_id]
            logger.info(f"Hazard removed: {hazard_id}")

    def get_nearest_node(self, lat: float, lng: float) -> str:
        best_node = None
        min_dist = float("inf")
        for node_id, data in self.nodes.items():
            dist = haversine_km(lat, lng, data["lat"], data["lng"])
            if dist < min_dist:
                min_dist = dist
                best_node = node_id
        return best_node

    def _check_edge_hazard_intersection(self, u: str, v: str) -> Tuple[float, int]:
        u_lat, u_lng = self.nodes[u]["lat"], self.nodes[u]["lng"]
        v_lat, v_lng = self.nodes[v]["lat"], self.nodes[v]["lng"]
        edge_line = LineString([(u_lng, u_lat), (v_lng, v_lat)])

        total_penalty = 0.0
        intersecting_count = 0

        for hazard in self.active_hazards.values():
            if len(hazard.polygon) < 3:
                continue
            poly_coords = [(pt[1], pt[0]) for pt in hazard.polygon]
            poly = Polygon(poly_coords)

            if poly.intersects(edge_line):
                intersecting_count += 1
                if hazard.severity in (HazardSeverity.CRITICAL, HazardSeverity.HIGH) or not hazard.passable:
                    total_penalty += 10000.0  # Impassable
                elif hazard.severity == HazardSeverity.MEDIUM:
                    total_penalty += 8.0
                else:
                    total_penalty += 2.5

        return total_penalty, intersecting_count

    def compute_safe_route(self, origin_lat: float, origin_lng: float, destination_node: Optional[str] = None, avoid_hazards: bool = True) -> RouteResponse:
        start_node = self.get_nearest_node(origin_lat, origin_lng)
        
        # Build dynamic weighted graph
        G = nx.Graph()
        for u, v, d in self.graph.edges(data=True):
            base_dist = d["base_distance"]
            penalty = 0.0
            haz_count = 0
            if avoid_hazards and self.active_hazards:
                penalty, haz_count = self._check_edge_hazard_intersection(u, v)
            
            effective_weight = base_dist * (1.0 + penalty)
            G.add_edge(u, v, weight=effective_weight, base_dist=base_dist, speed=d.get("speed_limit", 50), haz_count=haz_count)

        # If destination not specified, pick best operational shelter
        target_node = destination_node
        chosen_shelter = None
        if not target_node:
            best_cost = float("inf")
            for s_id, s_data in self.shelters.items():
                if s_data.get("status") == "OPERATIONAL" and s_data.get("current_occupancy", 0) < s_data.get("capacity", 1):
                    cand_node = s_data["node_id"]
                    try:
                        cost = nx.shortest_path_length(G, start_node, cand_node, weight="weight")
                        if cost < best_cost:
                            best_cost = cost
                            target_node = cand_node
                            chosen_shelter = Shelter(**s_data)
                    except nx.NetworkXNoPath:
                        continue
        else:
            for s_data in self.shelters.values():
                if s_data["node_id"] == target_node:
                    chosen_shelter = Shelter(**s_data)
                    break

        if not target_node:
            for s_data in self.shelters.values():
                if s_data.get("status") == "OPERATIONAL":
                    target_node = s_data["node_id"]
                    chosen_shelter = Shelter(**s_data)
                    break

        try:
            path_nodes = nx.shortest_path(G, source=start_node, target=target_node, weight="weight")
            
            total_dist = 0.0
            est_minutes = 0.0
            total_risk = 0.0
            total_hazards_avoided = 0
            coords = []

            for i in range(len(path_nodes)):
                n_id = path_nodes[i]
                node_data = self.nodes[n_id]
                coords.append([node_data["lat"], node_data["lng"]])
                if i > 0:
                    prev_id = path_nodes[i - 1]
                    edge_data = G[prev_id][n_id]
                    dist = edge_data["base_dist"]
                    speed = edge_data.get("speed", 40.0)
                    total_dist += dist
                    est_minutes += (dist / max(speed, 10.0)) * 60.0
                    weight = edge_data["weight"]
                    if weight > dist:
                        total_risk += (weight / dist) - 1.0
                    total_hazards_avoided += edge_data.get("haz_count", 0)

            status_msg = "Optimal safe evacuation route generated."
            if total_risk > 500:
                status_msg = "Caution: High risk zone encountered on the only available corridor."
            elif total_hazards_avoided > 0:
                status_msg = f"Route dynamically rerouted around {total_hazards_avoided} active hazard zone(s)."

            return RouteResponse(
                success=True,
                origin_node=start_node,
                destination_node=target_node,
                destination_shelter=chosen_shelter,
                path_nodes=path_nodes,
                path_coords=coords,
                total_distance_km=round(total_dist, 2),
                estimated_time_minutes=round(est_minutes, 1),
                risk_score=round(total_risk, 1),
                hazards_avoided_count=total_hazards_avoided,
                status_message=status_msg
            )
        except Exception as e:
            logger.error(f"Pathfinding error: {e}")
            return RouteResponse(
                success=False,
                origin_node=start_node,
                destination_node=target_node or "",
                destination_shelter=chosen_shelter,
                path_nodes=[],
                path_coords=[],
                total_distance_km=0.0,
                estimated_time_minutes=0.0,
                risk_score=9999.0,
                hazards_avoided_count=0,
                status_message="No passable evacuation route found due to severe flooding/hazard containment."
            )

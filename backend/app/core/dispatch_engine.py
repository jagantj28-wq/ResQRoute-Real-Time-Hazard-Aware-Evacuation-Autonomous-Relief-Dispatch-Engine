import time
import logging
from typing import Dict, List, Optional
from backend.app.models.schemas import RescueUnit, RescueUnitStatus, SOSStatus, DispatchAction
from backend.app.core.graph_router import GraphRouter
from backend.app.core.triage import TriageEngine

logger = logging.getLogger("resqroute.dispatch")

class DispatchEngine:
    def __init__(self, router: GraphRouter, triage: TriageEngine):
        self.router = router
        self.triage = triage
        self.units: Dict[str, RescueUnit] = {}
        self.load_units_from_depots()

    def load_units_from_depots(self):
        for depot in self.router.rescue_depots:
            for u in depot.get("units", []):
                unit = RescueUnit(
                    id=u["id"],
                    name=u["name"],
                    type=u["type"],
                    speed_kmh=u.get("speed_kmh", 50.0),
                    capacity=u.get("capacity", 4),
                    status=RescueUnitStatus.AVAILABLE,
                    lat=u["lat"],
                    lng=u["lng"],
                    current_node=u["current_node"]
                )
                self.units[unit.id] = unit
        logger.info(f"Loaded {len(self.units)} rescue units into fleet.")

    def get_available_units(self) -> List[RescueUnit]:
        return [u for u in self.units.values() if u.status == RescueUnitStatus.AVAILABLE]

    def autonomous_dispatch_next(self) -> Optional[DispatchAction]:
        ranked_queue = self.triage.get_ranked_queue()
        pending_sos = [s for s in ranked_queue if s.status in (SOSStatus.PENDING, SOSStatus.TRIAGED)]
        if not pending_sos:
            return None

        available_units = self.get_available_units()
        if not available_units:
            return None

        target_sos = pending_sos[0]
        sos_target_node = target_sos.nearest_node or self.router.get_nearest_node(target_sos.lat, target_sos.lng)

        best_unit = None
        best_route = None
        best_eta = float("inf")

        for unit in available_units:
            if target_sos.medical_emergency and unit.type == "AMBULANCE":
                type_bonus = 0.8
            else:
                type_bonus = 1.0

            route_res = self.router.compute_safe_route(
                origin_lat=unit.lat,
                origin_lng=unit.lng,
                destination_node=sos_target_node,
                avoid_hazards=True
            )

            if route_res.success and route_res.risk_score < 5000:
                adjusted_eta = route_res.estimated_time_minutes * type_bonus
                if adjusted_eta < best_eta:
                    best_eta = adjusted_eta
                    best_unit = unit
                    best_route = route_res

        if best_unit and best_route:
            best_unit.status = RescueUnitStatus.DISPATCHED
            best_unit.assigned_sos_id = target_sos.id
            best_unit.current_route = best_route.path_nodes

            self.triage.update_status(target_sos.id, SOSStatus.DISPATCHED, assigned_unit_id=best_unit.id)

            logger.info(f"Autonomous dispatch: Unit {best_unit.name} -> SOS {target_sos.id} (ETA {round(best_eta, 1)}m)")
            return DispatchAction(
                unit_id=best_unit.id,
                sos_id=target_sos.id,
                route_nodes=best_route.path_nodes,
                route_coords=best_route.path_coords,
                eta_minutes=round(best_eta, 1)
            )

        return None

import pytest
from pathlib import Path
from backend.app.core.graph_router import GraphRouter
from backend.app.models.schemas import Hazard, HazardSeverity, HazardType

DATA_PATH = Path(__file__).resolve().parent.parent / "frontend" / "shared" / "data" / "city_network.json"

@pytest.fixture
def router():
    return GraphRouter(str(DATA_PATH))

def test_nearest_node_lookup(router):
    node = router.get_nearest_node(13.0830, 80.2710)
    assert node == "N3"

def test_baseline_evacuation_routing(router):
    res = router.compute_safe_route(origin_lat=13.0550, origin_lng=80.2750, avoid_hazards=False)
    assert res.success is True
    assert len(res.path_nodes) > 1
    assert res.total_distance_km > 0

def test_dynamic_hazard_avoidance_reroute(router):
    # Initial path from South Bay (N9) to North Hill (N1)
    initial_route = router.compute_safe_route(
        origin_lat=13.0550,
        origin_lng=80.2750,
        destination_node="N1",
        avoid_hazards=True
    )
    assert initial_route.success is True

    # Inject critical flood cutting through N6 Causeway Bridge
    hazard1 = Hazard(
        id="TEST-HAZ-1",
        name="Critical Causeway Submersion",
        type=HazardType.FLOOD,
        severity=HazardSeverity.CRITICAL,
        water_depth_meters=2.0,
        passable=False,
        polygon=[
            [13.0780, 80.2650],
            [13.0780, 80.2850],
            [13.0680, 80.2850],
            [13.0680, 80.2650]
        ]
    )
    router.add_or_update_hazard(hazard1)

    # Re-calculate path with hazard avoidance
    rerouted = router.compute_safe_route(
        origin_lat=13.0550,
        origin_lng=80.2750,
        destination_node="N1",
        avoid_hazards=True
    )
    assert rerouted.success is True
    # Verify N6 is strictly avoided
    assert "N6" not in rerouted.path_nodes

    # Now also flood the coastal road N7/N8, forcing western expressway N11/N12
    hazard2 = Hazard(
        id="TEST-HAZ-2",
        name="Coastal Highway Storm Surge",
        type=HazardType.FLOOD,
        severity=HazardSeverity.CRITICAL,
        water_depth_meters=1.8,
        passable=False,
        polygon=[
            [13.0900, 80.2900],
            [13.0900, 80.3050],
            [13.0600, 80.3050],
            [13.0600, 80.2900]
        ]
    )
    router.add_or_update_hazard(hazard2)

    west_rerouted = router.compute_safe_route(
        origin_lat=13.0550,
        origin_lng=80.2750,
        destination_node="N1",
        avoid_hazards=True
    )
    assert west_rerouted.success is True
    assert "N6" not in west_rerouted.path_nodes
    assert "N7" not in west_rerouted.path_nodes
    # Now forced to take western highlands bypass
    assert "N11" in west_rerouted.path_nodes or "N12" in west_rerouted.path_nodes

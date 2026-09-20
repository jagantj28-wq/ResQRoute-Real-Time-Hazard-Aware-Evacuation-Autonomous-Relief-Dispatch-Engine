import pytest
import time
from pathlib import Path
from backend.app.core.graph_router import GraphRouter
from backend.app.core.triage import TriageEngine, calculate_priority_score
from backend.app.core.dispatch_engine import DispatchEngine
from backend.app.models.schemas import SOSRequest, SOSPriority, SOSStatus

DATA_PATH = Path(__file__).resolve().parent.parent / "frontend" / "shared" / "data" / "city_network.json"

@pytest.fixture
def system():
    router = GraphRouter(str(DATA_PATH))
    triage = TriageEngine()
    dispatch = DispatchEngine(router, triage)
    return router, triage, dispatch

def test_triage_scoring():
    sos = SOSRequest(
        id="SOS-01",
        lat=13.0550,
        lng=80.2750,
        casualty_count=3,
        infants_or_elderly=1,
        medical_emergency=True,
        created_at=time.time()
    )
    # Expected: (3*10) + (1*25) + 50 = 105.0
    score = calculate_priority_score(sos)
    assert score >= 105.0

def test_triage_queue_ranking(system):
    _, triage, _ = system
    
    # Low priority SOS
    sos_low = SOSRequest(id="SOS-LOW", lat=13.05, lng=80.27, casualty_count=1, infants_or_elderly=0, medical_emergency=False)
    # Critical priority SOS
    sos_crit = SOSRequest(id="SOS-CRIT", lat=13.06, lng=80.28, casualty_count=4, infants_or_elderly=2, medical_emergency=True)

    triage.ingest_sos(sos_low)
    triage.ingest_sos(sos_crit)

    queue = triage.get_ranked_queue()
    assert queue[0].id == "SOS-CRIT"
    assert queue[0].priority_level == SOSPriority.CRITICAL

def test_autonomous_dispatch_matching(system):
    router, triage, dispatch = system

    sos = SOSRequest(
        id="SOS-EMERGENCY",
        lat=13.0550,
        lng=80.2750,
        nearest_node="N9",
        casualty_count=2,
        infants_or_elderly=1,
        medical_emergency=True
    )
    triage.ingest_sos(sos)

    action = dispatch.autonomous_dispatch_next()
    assert action is not None
    assert action.sos_id == "SOS-EMERGENCY"
    assert action.unit_id is not None
    assert len(action.route_nodes) > 1
    assert action.eta_minutes > 0

    # Verify unit status updated
    unit = dispatch.units[action.unit_id]
    assert unit.status == "DISPATCHED"
    assert unit.assigned_sos_id == "SOS-EMERGENCY"

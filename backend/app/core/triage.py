import time
from typing import List, Dict
from backend.app.models.schemas import SOSRequest, SOSPriority, SOSStatus

def calculate_priority_score(sos: SOSRequest) -> float:
    """
    Computes objective triage priority score.
    Formula:
      Score = (Casualty Count * 10) + (Vulnerable * 25) + (Medical * 50) + (Wait Time Mins * 1.5)
    """
    base = sos.casualty_count * 10.0
    vulnerable_penalty = sos.infants_or_elderly * 25.0
    medical_penalty = 50.0 if sos.medical_emergency else 0.0
    
    elapsed_seconds = max(0.0, time.time() - sos.created_at)
    wait_time_bonus = (elapsed_seconds / 60.0) * 1.5

    total_score = base + vulnerable_penalty + medical_penalty + wait_time_bonus
    return round(total_score, 1)

def assign_priority_level(score: float) -> SOSPriority:
    if score >= 80.0:
        return SOSPriority.CRITICAL
    elif score >= 50.0:
        return SOSPriority.HIGH
    elif score >= 25.0:
        return SOSPriority.MEDIUM
    else:
        return SOSPriority.LOW

class TriageEngine:
    def __init__(self):
        self.sos_registry: Dict[str, SOSRequest] = {}

    def ingest_sos(self, sos: SOSRequest) -> SOSRequest:
        if not sos.created_at:
            sos.created_at = time.time()
        score = calculate_priority_score(sos)
        sos.priority_score = score
        sos.priority_level = assign_priority_level(score)
        self.sos_registry[sos.id] = sos
        return sos

    def get_ranked_queue(self) -> List[SOSRequest]:
        ranked = []
        for sos in self.sos_registry.values():
            if sos.status != SOSStatus.RESOLVED:
                sos.priority_score = calculate_priority_score(sos)
                sos.priority_level = assign_priority_level(sos.priority_score)
            ranked.append(sos)
        ranked.sort(key=lambda s: (s.status == SOSStatus.RESOLVED, -s.priority_score))
        return ranked

    def update_status(self, sos_id: str, status: SOSStatus, assigned_unit_id: str = None) -> SOSRequest:
        if sos_id in self.sos_registry:
            sos = self.sos_registry[sos_id]
            sos.status = status
            if assigned_unit_id:
                sos.assigned_unit_id = assigned_unit_id
            return sos
        raise KeyError(f"SOS {sos_id} not found")

triage_engine = TriageEngine()

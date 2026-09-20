from pathlib import Path

class Settings:
    PROJECT_NAME: str = "ResQRoute"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "Real-Time Hazard-Aware Evacuation & Autonomous Relief Dispatch Engine"
    DATA_PATH: Path = Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "shared" / "data" / "city_network.json"
    DEFAULT_SPEED_KMH: float = 40.0
    SEVERE_PENALTY_MULTIPLIER: float = 10000.0
    MODERATE_PENALTY_MULTIPLIER: float = 5.0

settings = Settings()

import httpx
from typing import Optional, List, Dict
from .models import CloudAction, CloudObservation, CloudState

class CloudAuditClient:
    """
    Standard OpenEnv client for the CloudAudit environment.
    Wraps the FastAPI endpoints into a clean Python API.
    """
    def __init__(self, base_url: str = "http://localhost:7860"):
        self.base_url = base_url.rstrip("/")

    async def reset(self, task_name: str = "easy_audit") -> CloudObservation:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # OpenEnv standard reset often takes task_name in URL or body
            resp = await client.post(f"{self.base_url}/reset", params={"task_name": task_name})
            resp.raise_for_status()
            return CloudObservation(**resp.json())

    async def step(self, action: CloudAction) -> CloudObservation:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{self.base_url}/step", json=action.model_dump())
            resp.raise_for_status()
            return CloudObservation(**resp.json())

    async def get_state(self) -> CloudState:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self.base_url}/state")
            resp.raise_for_status()
            return CloudState(**resp.json())

    async def close(self):
        pass # Handle session cleanup if needed

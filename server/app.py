from openenv.core.env_server import create_fastapi_app
from .cloud_audit_env import CloudAuditEnv
from models import CloudAction, CloudObservation

# The create_fastapi_app helper wraps the Environment class into a FastAPI app
# that exposes /reset, /step, and /state endpoints.
app = create_fastapi_app(
    env=CloudAuditEnv,
    action_cls=CloudAction,
    observation_cls=CloudObservation
)

def main():
    import uvicorn
    print("[DEBUG] Starting Unified CloudAudit Server", flush=True)
    # When deployed via entry point, we refer to the module 'server.app:app'
    uvicorn.run("server.app:app", host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()

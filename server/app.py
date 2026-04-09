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

@app.post("/reset")
async def reset_with_task(task_name: str = "easy_audit"):
    # Access the shared environment instance created by create_fastapi_app
    # Note: create_fastapi_app typically stores the env instance in app.state.env
    env = app.state.env
    obs = env.reset(task_name=task_name)
    return obs.model_dump()

def main():
    import uvicorn
    print("[DEBUG] Starting Unified CloudAudit Server", flush=True)
    # When deployed via entry point, we refer to the module 'server.app:app'
    uvicorn.run("server.app:app", host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()

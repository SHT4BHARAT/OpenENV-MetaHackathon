from fastapi import FastAPI
from openenv.core.env_server import create_fastapi_app
from .cloud_audit_env import CloudAuditEnv
from models import CloudAction, CloudObservation, CloudState

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/step":
            body = await request.body()
            print(f"[DEBUG] Incoming /step body: {body.decode()}", flush=True)
            async def receive():
                return {"type": "http.request", "body": body}
            request._receive = receive
        return await call_next(request)

# The create_fastapi_app helper wraps the Environment class into a FastAPI app
# that exposes /reset, /step, and /state endpoints.
app = create_fastapi_app(
    env=CloudAuditEnv,
    action_cls=CloudAction,
    observation_cls=CloudObservation
)
app.add_middleware(LoggingMiddleware)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    body = await request.body()
    print(f"[DEBUG] Validation Error for body: {body.decode()}", flush=True)
    print(f"[DEBUG] Errors: {exc.errors()}", flush=True)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "body": body.decode()},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)

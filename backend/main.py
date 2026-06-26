"""aegis FastAPI application entrypoint.

`/health` is a dependency-free liveness probe: it does not touch settings or any
external service so the runtime is provably bootable on its own.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.obs.tracing import init_sentry


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    init_sentry()
    yield


app = FastAPI(title="aegis", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe used by the SC-ENV-01 smoke test."""
    return {"status": "ok"}


@app.get("/sentry-debug")
async def trigger_error():
    """Debug endpoint to verify Sentry integration."""
    division_by_zero = 1 / 0

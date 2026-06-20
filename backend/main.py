"""aegis FastAPI application entrypoint.

`/health` is a dependency-free liveness probe: it does not touch settings or any
external service so the runtime is provably bootable on its own.
"""

from fastapi import FastAPI

app = FastAPI(title="aegis", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe used by the SC-ENV-01 smoke test."""
    return {"status": "ok"}

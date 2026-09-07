"""aegis FastAPI application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.backend.storage.sqlite_store import init_db
from src.backend.api.intake import router as intake_router
from src.backend.api.logs import router as logs_router
from src.backend.api.trends import router as trends_router
from src.backend.api.patterns import router as patterns_router
from src.backend.api.directive import router as directive_router
from src.backend.api.alerts import router as alerts_router
from src.backend.api.settings import router as settings_router
from src.backend.api.goals import router as goals_router
from src.backend.api.fitbit import router as fitbit_router
from src.backend.api.fitindex import router as fitindex_router
from src.backend.api.calendar import router as calendar_router
from src.backend.api.sync import router as sync_router
from src.backend.api.chat import router as chat_router
from src.backend.api.geolocation import router as geolocation_router
from src.backend.api.takeout import router as takeout_router
from src.backend.api.metrics import router as metrics_router
from src.backend.sync.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize storage on startup."""
    init_db()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="aegis",
    description="Voice-first fitness tracking copilot for functional longevity",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend dev server and local network access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(intake_router)
app.include_router(logs_router)
app.include_router(trends_router)
app.include_router(patterns_router)
app.include_router(directive_router)
app.include_router(alerts_router)
app.include_router(settings_router)
app.include_router(goals_router)
app.include_router(fitbit_router)
app.include_router(fitindex_router)
app.include_router(calendar_router)
app.include_router(sync_router)
app.include_router(chat_router)
app.include_router(geolocation_router)
app.include_router(takeout_router)
app.include_router(metrics_router)


@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0.0"}

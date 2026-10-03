"""Main FastAPI application entrypoint for BLACKBOX: AI Agent Flight Recorder."""
from contextlib import asynccontextmanager
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.database import init_db
from backend.api import router as api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure database tables and initial seed data exist on startup."""
    init_db()
    from backend.seed import seed_database
    try:
        from backend.database import SessionLocal
        from backend.models import Run
        db = SessionLocal()
        count = db.query(Run).count()
        db.close()
        if count == 0:
            seed_database()
    except Exception as e:
        print(f"Seed verification notice: {e}")
    yield


app = FastAPI(
    title="BLACKBOX",
    description="AI Agent Flight Recorder — Autonomous recording, hybrid diagnosis, counterfactual replay, and evaluation studio.",
    version="2.1.0",
    lifespan=lifespan,
)

# Enable CORS for frontend dev servers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Router
app.include_router(api_router)

# Static files mount if static/ or frontend build exists
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    def serve_frontend_root():
        index_file = os.path.join(static_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"app": "BLACKBOX", "status": "running", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)

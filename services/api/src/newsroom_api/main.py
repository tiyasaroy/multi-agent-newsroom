from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from newsroom_api.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Multi-Agent Newsroom API",
    description="Evidence-first newsroom orchestration and editorial API.",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name, "environment": settings.app_env}


@app.get("/api/v1/newsroom", tags=["newsroom"])
async def newsroom_status() -> dict[str, object]:
    return {
        "status": "operational",
        "active_stories": 0,
        "active_agents": 0,
        "publication_gate": "human_required",
    }

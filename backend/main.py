"""Theme 1: Unified Business Identifier (UBID) — API Server"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.database import init_db
from app.routers import records, linkage, unified


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="UBID — Unified Business Identifier Platform",
    description="Entity resolution across Karnataka's department systems with lifecycle intelligence",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(records.router, prefix="/api/records", tags=["records"])
app.include_router(linkage.router, prefix="/api/linkage", tags=["linkage"])
app.include_router(unified.router, prefix="/api/unified", tags=["unified"])


@app.get("/health")
def health():
    return {"status": "ok", "service": "ubid-platform"}

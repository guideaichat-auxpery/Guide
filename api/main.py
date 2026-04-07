import os
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist")
SERVE_STATIC = os.path.isdir(STATIC_DIR)

app = FastAPI(
    title="Guide API",
    description="REST API for Guide — Montessori educational platform",
    version="1.0.0",
)

ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "").split(",")
ALLOWED_ORIGINS = [o.strip() for o in ALLOWED_ORIGINS if o.strip()]

REPLIT_DEV_DOMAIN = os.getenv("REPLIT_DEV_DOMAIN", "")
REPLIT_DOMAINS = os.getenv("REPLIT_DOMAINS", "")
REPLIT_DEPLOYMENT_URL = os.getenv("REPLIT_DEPLOYMENT_URL", "")

for domain in [REPLIT_DEV_DOMAIN, REPLIT_DOMAINS, REPLIT_DEPLOYMENT_URL]:
    if domain:
        origin = f"https://{domain}" if not domain.startswith("http") else domain
        if origin not in ALLOWED_ORIGINS:
            ALLOWED_ORIGINS.append(origin)

if not ALLOWED_ORIGINS:
    ALLOWED_ORIGINS = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True if ALLOWED_ORIGINS != ["*"] else False,
    allow_methods=["*"],
    allow_headers=["*"],
)

from api.routes.auth import router as auth_router
from api.routes.users import router as users_router
from api.routes.students import router as students_router
from api.routes.schools import router as schools_router
from api.routes.tools import router as tools_router
from api.routes.notes import router as notes_router
from api.routes.data import router as data_router
from api.routes.adaptive import router as adaptive_router

app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(students_router, prefix="/api")
app.include_router(schools_router, prefix="/api")
app.include_router(tools_router, prefix="/api")
app.include_router(notes_router, prefix="/api")
app.include_router(data_router, prefix="/api")
app.include_router(adaptive_router, prefix="/api")


@app.get("/api/health")
def health_check():
    from api.db import get_engine
    engine = get_engine()
    db_status = "unavailable"
    if engine:
        try:
            from sqlalchemy import text
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            db_status = "connected"
        except Exception:
            db_status = "error"
    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "service": "Guide API",
        "database": db_status,
    }


if SERVE_STATIC:
    from fastapi.staticfiles import StaticFiles

    INDEX_HTML = os.path.join(STATIC_DIR, "index.html")

    assets_dir = os.path.join(STATIC_DIR, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="static-assets")

    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        if full_path:
            file_path = os.path.realpath(os.path.join(STATIC_DIR, full_path))
            if file_path.startswith(os.path.realpath(STATIC_DIR) + os.sep) and os.path.isfile(file_path):
                return FileResponse(file_path)
        return FileResponse(INDEX_HTML)

    logger.info(f"Static frontend configured from {STATIC_DIR}")


@app.on_event("startup")
def startup():
    logger.info("Guide API starting up...")
    from api.db import get_engine
    engine = get_engine()
    if engine:
        logger.info("Database engine initialized")
    else:
        logger.warning("Database not available")

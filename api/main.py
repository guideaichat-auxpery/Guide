import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Guide API",
    description="REST API for Guide — Montessori educational platform",
    version="1.0.0",
)

ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "").split(",")
ALLOWED_ORIGINS = [o.strip() for o in ALLOWED_ORIGINS if o.strip()]

_replit_domain_vars = [
    os.getenv("REPLIT_DEV_DOMAIN", ""),
    os.getenv("REPLIT_DOMAINS", ""),
    os.getenv("REPLIT_DEPLOYMENT_URL", ""),
]
for raw in _replit_domain_vars:
    for part in raw.split(","):
        domain = part.strip()
        if domain:
            origin = f"https://{domain}" if not domain.startswith("http") else domain
            if origin not in ALLOWED_ORIGINS:
                ALLOWED_ORIGINS.append(origin)

_replit_slug = os.getenv("REPL_SLUG", "")
_replit_owner = os.getenv("REPL_OWNER", "")
if _replit_slug and _replit_owner:
    static_origin = f"https://{_replit_slug}-{_replit_owner}.replit.app"
    if static_origin not in ALLOWED_ORIGINS:
        ALLOWED_ORIGINS.append(static_origin)

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
    import httpx
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

    adaptive_status = "unavailable"
    adaptive_port = os.getenv("ADAPTIVE_PORT", "3000")
    try:
        resp = httpx.get(f"http://127.0.0.1:{adaptive_port}/health", timeout=3)
        if resp.status_code == 200:
            adaptive_status = "healthy"
        else:
            adaptive_status = "error"
    except Exception:
        adaptive_status = "unreachable"

    all_healthy = db_status == "connected" and adaptive_status == "healthy"
    return {
        "status": "healthy" if all_healthy else "degraded",
        "service": "Guide API",
        "database": db_status,
        "adaptive": adaptive_status,
    }




@app.on_event("startup")
def startup():
    logger.info("Guide API starting up...")
    from api.db import get_engine
    engine = get_engine()
    if engine:
        logger.info("Database engine initialized")
    else:
        logger.warning("Database not available")

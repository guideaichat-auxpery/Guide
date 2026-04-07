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

app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(students_router, prefix="/api")
app.include_router(schools_router, prefix="/api")
app.include_router(tools_router, prefix="/api")
app.include_router(notes_router, prefix="/api")
app.include_router(data_router, prefix="/api")


@app.get("/api/health")
def health_check():
    from api.db import get_engine
    engine = get_engine()
    return {
        "status": "healthy",
        "service": "Guide API",
        "database": "connected" if engine else "unavailable",
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

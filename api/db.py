import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
from contextlib import contextmanager

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

_engine = None
_SessionFactory = None


def _normalize_database_url(url):
    if not url:
        return url
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


def get_engine():
    global _engine
    if _engine is not None:
        return _engine
    db_url = _normalize_database_url(DATABASE_URL)
    if not db_url:
        logger.warning("DATABASE_URL not configured")
        return None

    connect_args = {"connect_timeout": 10}
    if "sslmode" not in db_url:
        if "neon.tech" in db_url:
            connect_args["sslmode"] = "require"
        else:
            connect_args["sslmode"] = "prefer"

    _engine = create_engine(
        db_url,
        pool_pre_ping=True,
        pool_recycle=3600,
        pool_size=5,
        max_overflow=10,
        connect_args=connect_args,
    )
    logger.info("FastAPI database engine created")
    return _engine


def get_session_factory():
    global _SessionFactory
    if _SessionFactory is not None:
        return _SessionFactory
    engine = get_engine()
    if engine is None:
        return None
    _SessionFactory = scoped_session(
        sessionmaker(autocommit=False, autoflush=False, bind=engine)
    )
    return _SessionFactory


def get_db():
    factory = get_session_factory()
    if factory is None:
        raise RuntimeError("Database not available")
    session = factory()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        factory.remove()


from database import (
    Base,
    User,
    Student,
    StudentActivity,
    School,
    EducatorStudentAccess,
    LessonPlan,
    GreatStory,
    PlanningNote,
    ChatConversation,
    ConversationHistory,
    EducatorAnalytics,
    CurriculumContext,
    TrendingKeyword,
    ChatAnalytics,
    EducatorAuditLog,
    SafetyAlert,
    SystemConfig,
    PasswordResetToken,
    ContactSubmission,
    PersistentSession,
    ConsentRecord,
    ParentalConsentRecord,
)

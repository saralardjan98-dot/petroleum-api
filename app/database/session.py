from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


# =========================
# Database Engine
# =========================
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    echo=settings.DEBUG
)


# =========================
# Session Factory
# =========================
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# =========================
# Base Class
# =========================
class Base(DeclarativeBase):
    pass


# =========================
# Dependency (FastAPI)
# =========================
def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# =========================
# Init DB
# =========================
def init_db():
    from app.models import (
        user,
        well,
        petrophysical_file,
        analysis_result,
        audit_log
    )

    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized")
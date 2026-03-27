from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import NullPool
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Create engine with connection pooling
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,       # Test connections before use
    pool_size=10,             # Connection pool size
    max_overflow=20,          # Extra connections allowed
    pool_recycle=3600,        # Recycle connections after 1h
    echo=settings.DEBUG,      # Log SQL in debug mode
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency: provides a database session per request."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """Create all tables on startup."""
    from app.models import user, well, petrophysical_file, curve_data, analysis_result, audit_log
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized")

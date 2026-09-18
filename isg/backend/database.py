from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from config import get_settings

Base = declarative_base()

_engine = None
_SessionLocal = None


def _get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        url = settings.database_url
        if url.startswith("sqlite"):
            _engine = create_engine(
                url,
                connect_args={"check_same_thread": False},
            )
        else:
            _engine = create_engine(
                url,
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20,
            )
    return _engine


def _get_session_local():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_get_engine())
    return _SessionLocal


# Expose engine for alembic / metadata operations
@property
def engine():
    return _get_engine()


# Keep module-level engine for Base.metadata.create_all compatibility
class _LazyEngine:
    def __getattr__(self, item):
        return getattr(_get_engine(), item)

engine = _LazyEngine()  # type: ignore
SessionLocal = None  # will be set on first use


def get_db():
    Session = _get_session_local()
    db = Session()
    try:
        yield db
    finally:
        db.close()

"""Database setup and session management for BLACKBOX."""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DB_PATH = os.environ.get("BLACKBOX_DB_PATH", os.path.join(os.path.dirname(__file__), "blackbox.db"))
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency injection generator for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables in the database."""
    from backend import models  # noqa: F401
    from backend import itinerary_routes  # noqa: F401 — registers Itinerary models
    Base.metadata.create_all(bind=engine)

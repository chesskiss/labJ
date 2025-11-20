# agents/db.py
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Path to your existing SQLite file "journal.sqlite" in repo root.
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "journal.sqlite"
DATABASE_URL = f"sqlite:///{DB_PATH}"


engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite + FastAPI
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for declarative models."""
    pass


def init_db():
    """
    This will not drop or change existing tables.
    It just ensures our ORM models are registered.
    """
    from . import models  # noqa: F401
    # We don't call Base.metadata.create_all here because your schema already exists.
    # If you WANT SQLAlchemy to create missing tables, you could uncomment:
    # Base.metadata.create_all(bind=engine)

"""Database engine/session factory helpers."""

from __future__ import annotations

import os
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def get_database_url(database_url: Optional[str] = None) -> str:
    """Resolve DATABASE_URL from explicit arg or environment."""
    url = database_url or os.getenv("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL is not set")
    return url


def create_db_engine(database_url: Optional[str] = None) -> Engine:
    """Create SQLAlchemy engine for the configured database URL."""
    return create_engine(get_database_url(database_url), future=True)


def create_session_factory(database_url: Optional[str] = None) -> sessionmaker[Session]:
    """Create SQLAlchemy session factory for the configured database."""
    engine = create_db_engine(database_url)
    return sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        class_=Session,
    )

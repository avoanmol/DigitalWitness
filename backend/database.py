
import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://dw:change_this_local_password@localhost:5432/dw",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    """Base class for SQLAlchemy database models."""


def check_database_connection() -> bool:
    """Return True if PostgreSQL accepts a query."""
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return True

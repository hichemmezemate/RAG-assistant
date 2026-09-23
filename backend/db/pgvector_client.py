import os
import logging
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv

from backend.models.document import Base

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/rag_assistant",
)

# If URL is postgres:// (standard Heroku/older formats), normalize to postgresql+psycopg://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://") and not DATABASE_URL.startswith("postgresql+"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

# SQLite configuration for testing or fallback
is_sqlite = DATABASE_URL.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {"connect_timeout": 3}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=not is_sqlite,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Initialize database, pgvector extension, and create tables."""
    try:
        if not is_sqlite:
            with engine.connect() as connection:
                connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                connection.commit()
                logger.info("Extension pgvector initialisée avec succès.")
        Base.metadata.create_all(bind=engine)
        logger.info("Tables de la base de données initialisées avec succès.")
    except Exception as e:
        logger.warning(
            f"Note lors de l'initialisation de la base ({DATABASE_URL}): {e}. "
            "Assurez-vous que PostgreSQL et pgvector sont démarrés pour la persistance complète."
        )
        # Still attempt to create tables if possible
        try:
            Base.metadata.create_all(bind=engine)
        except Exception:
            pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

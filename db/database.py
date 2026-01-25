"""
Database Configuration and Session Management

Provides database connection, session management, and initialization utilities.
"""

import os
from typing import Generator, Optional
from contextlib import contextmanager
import logging

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from .models import Base

logger = logging.getLogger(__name__)

# Default to SQLite for development, PostgreSQL for production
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'sqlite:///./grc_platform.db'
)


class DatabaseManager:
    """
    Database manager for handling connections and sessions.
    """

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or DATABASE_URL
        self.engine = None
        self.SessionLocal = None
        self._initialized = False

    def init(self, echo: bool = False):
        """
        Initialize database engine and session factory.

        Args:
            echo: If True, log all SQL statements
        """
        if self._initialized:
            return

        # Handle SQLite special case
        if self.database_url.startswith('sqlite'):
            self.engine = create_engine(
                self.database_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=echo
            )

            # Enable foreign keys for SQLite
            @event.listens_for(self.engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
        else:
            # PostgreSQL or other databases
            self.engine = create_engine(
                self.database_url,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                echo=echo
            )

        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

        self._initialized = True
        logger.info(f"Database initialized: {self.database_url.split('@')[-1] if '@' in self.database_url else self.database_url}")

    def create_tables(self):
        """Create all database tables"""
        if not self._initialized:
            self.init()

        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created")

    def drop_tables(self):
        """Drop all database tables (use with caution!)"""
        if not self._initialized:
            self.init()

        Base.metadata.drop_all(bind=self.engine)
        logger.warning("Database tables dropped")

    def get_session(self) -> Session:
        """Get a new database session"""
        if not self._initialized:
            self.init()

        return self.SessionLocal()

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """
        Context manager for database sessions.

        Automatically handles commit/rollback and session cleanup.

        Usage:
            with db_manager.session_scope() as session:
                session.add(obj)
                # Auto-commits if no exception
        """
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            session.close()

    def health_check(self) -> dict:
        """Check database connectivity"""
        if not self._initialized:
            self.init()

        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return {
                "status": "healthy",
                "database": self.database_url.split('@')[-1] if '@' in self.database_url else "local"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }


# Global database manager instance
db_manager = DatabaseManager()


def init_db(database_url: Optional[str] = None, echo: bool = False):
    """Initialize the database"""
    global db_manager

    if database_url:
        db_manager = DatabaseManager(database_url)

    db_manager.init(echo=echo)
    db_manager.create_tables()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI to get database session.

    Usage in FastAPI:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()
    """
    if not db_manager._initialized:
        db_manager.init()
        db_manager.create_tables()

    db = db_manager.get_session()
    try:
        yield db
    finally:
        db.close()

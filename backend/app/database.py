import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import settings


def _get_engine():
    """Create engine, falling back to SQLite if PostgreSQL is unavailable."""
    db_url = settings.database_url

    # If PostgreSQL URL but no PG available locally, use SQLite fallback
    if db_url.startswith("postgresql"):
        try:
            eng = create_engine(db_url, pool_pre_ping=True)
            with eng.connect() as conn:
                conn.execute(conn.dialect.do_ping(conn) if hasattr(conn.dialect, 'do_ping') else conn.connection)
            return eng
        except Exception:
            # Fallback to SQLite
            db_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage")
            os.makedirs(db_dir, exist_ok=True)
            sqlite_url = f"sqlite:///{db_dir}/gromo_dev.db"
            eng = create_engine(sqlite_url, connect_args={"check_same_thread": False})
            # Enable WAL mode for better concurrency
            @event.listens_for(eng, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.close()
            return eng
    else:
        return create_engine(db_url, pool_pre_ping=True)


engine = _get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables (used for SQLite dev mode)."""
    Base.metadata.create_all(bind=engine)

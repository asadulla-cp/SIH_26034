from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import DATA_DIR, DB_PATH, REPORT_DIR, UPLOAD_DIR


class Base(DeclarativeBase):
    pass


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)


engine = None
SessionLocal = None


def get_engine():
    global engine, SessionLocal
    if engine is None:
        ensure_dirs()
        engine = create_engine(
            f"sqlite:///{DB_PATH}",
            connect_args={"check_same_thread": False},
        )
        SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return engine


def get_db():
    get_engine()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

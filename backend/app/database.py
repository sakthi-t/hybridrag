from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import get_settings

engine = None
SessionLocal = None
Base = declarative_base()


def init_db(database_url: str | None = None):
    global engine, SessionLocal
    url = database_url or get_settings().database_url
    engine = create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=300,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
    )
    SessionLocal = sessionmaker(bind=engine)


def get_db():
    if SessionLocal is None:
        init_db()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

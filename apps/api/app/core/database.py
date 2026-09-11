from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models.database  # noqa: F401
from app.core.config import settings
from app.models.database import Base  # noqa: F401

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

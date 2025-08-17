import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json

from app.models.database import (
    Base,
    Project,  # noqa: F401
    Contact,  # noqa: F401
    ChatSession,  # noqa: F401
    ChatMessage,  # noqa: F401
    CVDownload,  # noqa: F401
)

# Test database configuration
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    """Create a test database session."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_project_data():
    """Sample project data for testing."""
    return {
        "github_id": 12345,
        "name": "test-project",
        "description": "A test project",
        "language": "Python",
        "url": "https://github.com/test/test-project",
        "stars": 10,
        "forks": 5,
        "topics": json.dumps(["python", "test"]),
        "is_featured": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }


@pytest.fixture
def sample_contact_data():
    """Sample contact data for testing."""
    return {
        "name": "Test User",
        "email": "test@example.com",
        "message": "This is a test message",
        "ip_address": "127.0.0.1",
        "user_agent": "Test Browser",
    }

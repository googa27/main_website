from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.main import app

client = TestClient(app)


def _database_health_response(session: Session):
    def override_get_db():
        yield session

    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as database_client:
            return database_client.get("/api/health/db")
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous


def _sqlite_engine():
    return create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def test_health_check():
    """Test the health check endpoint"""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "Cristobal Portfolio API" in data["service"]


def test_root_endpoint():
    """Test the root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Cristobal Portfolio API"
    assert data["version"] == "1.0.0"


def test_database_health_check_executes_supported_statement():
    engine = _sqlite_engine()
    try:
        with Session(engine) as session:
            response = _database_health_response(session)
    finally:
        engine.dispose()

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "database": "connected",
        "service": "Cristobal Portfolio API",
    }


def test_database_health_check_reports_closed_connection():
    engine = _sqlite_engine()
    connection = engine.connect()
    session = Session(bind=connection)
    connection.close()
    try:
        response = _database_health_response(session)
    finally:
        session.close()
        engine.dispose()

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["database"] == "disconnected"
    assert data["service"] == "Cristobal Portfolio API"
    assert "closed" in data["error"].lower()

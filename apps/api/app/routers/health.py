from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": settings.PROJECT_NAME, "version": "1.0.0"}


@router.get("/health/db")
async def database_health_check(db: Session = Depends(get_db)):
    """Database health check"""
    try:
        # Simple query to test database connection
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected",
            "service": settings.PROJECT_NAME,
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
            "service": settings.PROJECT_NAME,
        }

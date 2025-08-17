from sqlalchemy.orm import Session

from app.models.database import CVDownload


class AnalyticsService:
    """Service for analytics and tracking operations."""

    @staticmethod
    def record_cv_download(
        db: Session,
        ip_address: str | None = None,
        user_agent: str | None = None,
        referrer: str | None = None,
    ) -> CVDownload:
        """Record a CV download event."""
        new_download = CVDownload(
            ip_address=ip_address,
            user_agent=user_agent,
            referrer=referrer,
        )
        db.add(new_download)
        db.commit()
        db.refresh(new_download)
        return new_download

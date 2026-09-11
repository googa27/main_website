"""
CV management service for professional profile data.

This service handles:
- CV data storage and retrieval
- Multiple format exports (PDF, JSON, MDX)
- Integration with LinkedIn auto-sync
- CV versioning and updates
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Any

from app.core.time import utc_now
from app.schemas.cv import (
    CVExportRequest,
    CVExportResponse,
    CVProfile,
    LinkedInSyncRequest,
    LinkedInSyncResponse,
)
from app.services.linkedin import linkedin_service

from .rendering import render_mdx
from .storage import load_profile, save_profile

logger = logging.getLogger(__name__)


class CVService:
    """Service for CV data management and export functionality."""

    def __init__(self):
        """Initialize CV service."""
        self.cv_data_dir = Path(__file__).resolve().parents[2] / "static" / "cv"
        self.cv_data_dir.mkdir(parents=True, exist_ok=True)

        # CV data file
        self.cv_data_file = self.cv_data_dir / "cv_profile.json"

        # Export formats
        self.supported_formats = ["json", "pdf", "mdx"]

        # Current CV profile
        self._current_profile: CVProfile | None = None
        self._storage_lock = RLock()

    async def get_current_cv(self) -> CVProfile | None:
        return await asyncio.to_thread(self._current_snapshot)

    def _current_snapshot(self) -> CVProfile | None:
        with self._storage_lock:
            if self._current_profile is None:
                self._current_profile = load_profile(self.cv_data_file)
            return self._current_profile

    async def sync_from_linkedin(
        self, request: LinkedInSyncRequest
    ) -> LinkedInSyncResponse:
        """
        Sync CV data from LinkedIn.

        Args:
            request: LinkedIn sync request parameters

        Returns:
            LinkedInSyncResponse with sync results
        """
        try:
            logger.info("Starting LinkedIn CV sync")

            # Check if LinkedIn service is configured
            if not linkedin_service.is_configured():
                return LinkedInSyncResponse(
                    success=False,
                    message="LinkedIn service not configured",
                    last_sync=utc_now(),
                    data_updated=False,
                    changes=None,
                )

            # Perform LinkedIn sync
            cv_profile = await linkedin_service.sync_profile_data(
                force_refresh=request.force_refresh
            )

            if not cv_profile:
                return LinkedInSyncResponse(
                    success=False,
                    message="Failed to sync from LinkedIn",
                    last_sync=utc_now(),
                    data_updated=False,
                    changes=None,
                )

            changes = await asyncio.to_thread(self._apply_provider_snapshot, cv_profile)

            # Update sync status
            sync_status = linkedin_service.get_sync_status()

            logger.info("LinkedIn CV sync completed successfully")

            return LinkedInSyncResponse(
                success=True,
                message="CV synced successfully from LinkedIn",
                last_sync=datetime.fromisoformat(sync_status["last_sync"])
                if sync_status["last_sync"]
                else utc_now(),
                data_updated=bool(changes),
                changes=changes,
            )

        except Exception as e:
            logger.error(f"LinkedIn CV sync failed: {e!s}")
            return LinkedInSyncResponse(
                success=False,
                message=f"Sync failed: {e!s}",
                last_sync=utc_now(),
                data_updated=False,
                changes=None,
            )

    def _apply_provider_snapshot(self, cv_profile: CVProfile) -> dict[str, Any] | None:
        with self._storage_lock:
            # Compare with current profile to detect changes
            current_profile = self._current_snapshot()
            if current_profile:
                omitted = {
                    "projects",
                    "awards",
                    "date_precision_note",
                } - cv_profile.model_fields_set
                preserved = current_profile.model_dump(include=omitted)
                cv_profile = CVProfile.model_validate(
                    cv_profile.model_dump() | preserved
                )
            changes = (
                self._detect_changes(current_profile, cv_profile)
                if current_profile
                else None
            )

            # Save new profile
            if not save_profile(cv_profile, self.cv_data_dir, self.cv_data_file):
                raise OSError("CV storage update failed")
            self._current_profile = cv_profile
            return changes

    async def export_cv(self, request: CVExportRequest) -> CVExportResponse:
        """
        Export CV in the requested format.

        Args:
            request: CV export request with format and options

        Returns:
            CVExportResponse with export data or download URL
        """
        try:
            # Validate format
            if request.format.lower() not in self.supported_formats:
                return CVExportResponse(
                    format=request.format,
                    download_url=None,
                    content=f"Unsupported format: {request.format}. Supported formats: {', '.join(self.supported_formats)}",
                    file_size=None,
                    expires_at=None,
                )

            # Get current CV profile
            cv_profile = await self.get_current_cv()
            if not cv_profile:
                return CVExportResponse(
                    format=request.format,
                    download_url=None,
                    content="No CV profile available. Please sync from LinkedIn first.",
                    file_size=None,
                    expires_at=None,
                )

            # Export based on format
            if request.format.lower() == "json":
                return await self._export_json(cv_profile, request)
            elif request.format.lower() == "pdf":
                return await self._export_pdf(cv_profile, request)
            elif request.format.lower() == "mdx":
                return await self._export_mdx(cv_profile, request)
            else:
                return CVExportResponse(
                    format=request.format,
                    download_url=None,
                    content=f"Export format {request.format} not implemented yet",
                    file_size=None,
                    expires_at=None,
                )

        except Exception as e:
            logger.error(f"CV export failed: {e!s}")
            return CVExportResponse(
                format=request.format,
                download_url=None,
                content=f"Export failed: {e!s}",
                file_size=None,
                expires_at=None,
            )

    async def _export_json(
        self, cv_profile: CVProfile, request: CVExportRequest
    ) -> CVExportResponse:
        """Export CV as JSON."""
        try:
            export_data = cv_profile.model_dump()

            # Apply export options
            if not request.include_scores:
                # Remove skill scores if not requested
                for category in export_data["skills"].values():
                    if isinstance(category, list):
                        for skill in category:
                            if isinstance(skill, dict):
                                skill.pop("level", None)

            if not request.include_achievements:
                # Remove achievements if not requested
                for exp in export_data["experience"]:
                    exp.pop("achievements", None)

            if not request.include_technologies:
                # Remove technologies if not requested
                for exp in export_data["experience"]:
                    exp.pop("technologies", None)

            # Convert to JSON string
            json_content = json.dumps(export_data, indent=2, default=str)

            return CVExportResponse(
                format="json",
                download_url=None,
                content=json_content,
                file_size=len(json_content.encode("utf-8")),
                expires_at=None,
            )

        except Exception as e:
            logger.error(f"JSON export failed: {e!s}")
            raise

    async def _export_pdf(
        self, cv_profile: CVProfile, request: CVExportRequest
    ) -> CVExportResponse:
        """Export CV as PDF."""
        try:
            # For now, return a placeholder response
            # In a real implementation, you would use a library like reportlab or weasyprint
            # to generate a proper PDF from the CV data

            pdf_content = f"""
            CV Export - {cv_profile.personal_info.first_name} {cv_profile.personal_info.last_name}
            Format: PDF
            Generated: {utc_now().strftime("%Y-%m-%d %H:%M:%S UTC")}
            
            Note: PDF export is not yet implemented.
            Please use JSON or MDX format for now.
            """

            return CVExportResponse(
                format="pdf",
                download_url=None,
                content=pdf_content,
                file_size=len(pdf_content.encode("utf-8")),
                expires_at=None,
            )

        except Exception as e:
            logger.error(f"PDF export failed: {e!s}")
            raise

    async def _export_mdx(
        self, cv_profile: CVProfile, request: CVExportRequest
    ) -> CVExportResponse:
        """Export CV as MDX (Markdown with React components)."""
        try:
            # Generate MDX content
            mdx_content = self._generate_mdx_content(cv_profile, request)

            return CVExportResponse(
                format="mdx",
                download_url=None,
                content=mdx_content,
                file_size=len(mdx_content.encode("utf-8")),
                expires_at=None,
            )

        except Exception as e:
            logger.error(f"MDX export failed: {e!s}")
            raise

    def _generate_mdx_content(
        self, cv_profile: CVProfile, request: CVExportRequest
    ) -> str:
        return render_mdx(cv_profile, request)

    def _detect_changes(
        self, old_profile: CVProfile, new_profile: CVProfile
    ) -> dict[str, Any] | None:
        """Detect changes between old and new CV profiles."""
        changes = {}

        try:
            # Compare personal info
            if old_profile.personal_info.summary != new_profile.personal_info.summary:
                changes["summary"] = {
                    "old": old_profile.personal_info.summary,
                    "new": new_profile.personal_info.summary,
                }

            # Compare experience
            old_exp_count = len(old_profile.experience)
            new_exp_count = len(new_profile.experience)
            if old_exp_count != new_exp_count:
                changes["experience_count"] = {
                    "old": old_exp_count,
                    "new": new_exp_count,
                }

            # Compare skills
            old_skills = old_profile.skills.get_all_skills()
            new_skills = new_profile.skills.get_all_skills()

            old_skill_names = {skill.name for skill in old_skills}
            new_skill_names = {skill.name for skill in new_skills}

            added_skills = new_skill_names - old_skill_names
            removed_skills = old_skill_names - new_skill_names

            if added_skills:
                changes["added_skills"] = list(added_skills)
            if removed_skills:
                changes["removed_skills"] = list(removed_skills)

            # Compare education
            old_edu_count = len(old_profile.education)
            new_edu_count = len(new_profile.education)
            if old_edu_count != new_edu_count:
                changes["education_count"] = {
                    "old": old_edu_count,
                    "new": new_edu_count,
                }

            # Compare certifications
            old_cert_count = len(old_profile.certifications)
            new_cert_count = len(new_profile.certifications)
            if old_cert_count != new_cert_count:
                changes["certification_count"] = {
                    "old": old_cert_count,
                    "new": new_cert_count,
                }

            for section in ("projects", "awards", "date_precision_note"):
                if getattr(old_profile, section) != getattr(new_profile, section):
                    changes[f"{section}_updated"] = True

            return changes if changes else None

        except Exception as e:
            logger.error(f"Error detecting changes: {e!s}")
            return None

    async def _load_cv_from_storage(self) -> CVProfile | None:
        return await asyncio.to_thread(self._read_snapshot)

    def _read_snapshot(self) -> CVProfile | None:
        with self._storage_lock:
            return load_profile(self.cv_data_file)

    async def _save_cv_to_storage(self, cv_profile: CVProfile) -> bool:
        return await asyncio.to_thread(self._write_snapshot, cv_profile)

    def _write_snapshot(self, cv_profile: CVProfile) -> bool:
        with self._storage_lock:
            return save_profile(cv_profile, self.cv_data_dir, self.cv_data_file)

    def get_sync_status(self) -> dict[str, Any]:
        """Get CV sync status."""
        linkedin_status = linkedin_service.get_sync_status()

        return {
            "linkedin_service": linkedin_status,
            "cv_profile_available": self._current_profile is not None,
            "last_cv_update": self._current_profile.last_updated.isoformat()
            if self._current_profile
            else None,
            "supported_formats": self.supported_formats,
        }


# Global instance for easy access
cv_service = CVService()

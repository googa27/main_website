"""
CV management service for professional profile data.

This service handles:
- CV data storage and retrieval
- Multiple format exports (PDF, JSON, MDX)
- Integration with LinkedIn auto-sync
- CV versioning and updates
"""

import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pathlib import Path
import tempfile
import shutil

from app.models.cv import (
    CVProfile, CVExportRequest, CVExportResponse, 
    LinkedInSyncRequest, LinkedInSyncResponse
)
from app.services.linkedin import linkedin_service
from app.core.config import settings

logger = logging.getLogger(__name__)


class CVService:
    """Service for CV data management and export functionality."""
    
    def __init__(self):
        """Initialize CV service."""
        self.cv_data_dir = Path("app/static/cv")
        self.cv_data_dir.mkdir(parents=True, exist_ok=True)
        
        # CV data file
        self.cv_data_file = self.cv_data_dir / "cv_profile.json"
        
        # Export formats
        self.supported_formats = ["json", "pdf", "mdx"]
        
        # Current CV profile
        self._current_profile: Optional[CVProfile] = None
    
    async def get_current_cv(self) -> Optional[CVProfile]:
        """Get the current CV profile, loading from storage if needed."""
        if self._current_profile is None:
            self._current_profile = await self._load_cv_from_storage()
        
        return self._current_profile
    
    async def sync_from_linkedin(self, request: LinkedInSyncRequest) -> LinkedInSyncResponse:
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
                    last_sync=datetime.now(timezone.utc),
                    data_updated=False,
                    changes=None
                )
            
            # Perform LinkedIn sync
            cv_profile = await linkedin_service.sync_profile_data(
                force_refresh=request.force_refresh
            )
            
            if not cv_profile:
                return LinkedInSyncResponse(
                    success=False,
                    message="Failed to sync from LinkedIn",
                    last_sync=datetime.now(timezone.utc),
                    data_updated=False,
                    changes=None
                )
            
            # Compare with current profile to detect changes
            current_profile = await self.get_current_cv()
            changes = self._detect_changes(current_profile, cv_profile) if current_profile else None
            
            # Save new profile
            await self._save_cv_to_storage(cv_profile)
            self._current_profile = cv_profile
            
            # Update sync status
            sync_status = linkedin_service.get_sync_status()
            
            logger.info("LinkedIn CV sync completed successfully")
            
            return LinkedInSyncResponse(
                success=True,
                message="CV synced successfully from LinkedIn",
                last_sync=datetime.fromisoformat(sync_status["last_sync"]) if sync_status["last_sync"] else datetime.now(timezone.utc),
                data_updated=bool(changes),
                changes=changes
            )
            
        except Exception as e:
            logger.error(f"LinkedIn CV sync failed: {str(e)}")
            return LinkedInSyncResponse(
                success=False,
                message=f"Sync failed: {str(e)}",
                last_sync=datetime.now(timezone.utc),
                data_updated=False,
                changes=None
            )
    
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
                    expires_at=None
                )
            
            # Get current CV profile
            cv_profile = await self.get_current_cv()
            if not cv_profile:
                return CVExportResponse(
                    format=request.format,
                    download_url=None,
                    content="No CV profile available. Please sync from LinkedIn first.",
                    file_size=None,
                    expires_at=None
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
                    expires_at=None
                )
                
        except Exception as e:
            logger.error(f"CV export failed: {str(e)}")
            return CVExportResponse(
                format=request.format,
                download_url=None,
                content=f"Export failed: {str(e)}",
                file_size=None,
                expires_at=None
            )
    
    async def _export_json(self, cv_profile: CVProfile, request: CVExportRequest) -> CVExportResponse:
        """Export CV as JSON."""
        try:
            # Convert to dict with export options
            export_data = cv_profile.dict()
            
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
                file_size=len(json_content.encode('utf-8')),
                expires_at=None
            )
            
        except Exception as e:
            logger.error(f"JSON export failed: {str(e)}")
            raise
    
    async def _export_pdf(self, cv_profile: CVProfile, request: CVExportRequest) -> CVExportResponse:
        """Export CV as PDF."""
        try:
            # For now, return a placeholder response
            # In a real implementation, you would use a library like reportlab or weasyprint
            # to generate a proper PDF from the CV data
            
            pdf_content = f"""
            CV Export - {cv_profile.personal_info.first_name} {cv_profile.personal_info.last_name}
            Format: PDF
            Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
            
            Note: PDF export is not yet implemented.
            Please use JSON or MDX format for now.
            """
            
            return CVExportResponse(
                format="pdf",
                download_url=None,
                content=pdf_content,
                file_size=len(pdf_content.encode('utf-8')),
                expires_at=None
            )
            
        except Exception as e:
            logger.error(f"PDF export failed: {str(e)}")
            raise
    
    async def _export_mdx(self, cv_profile: CVProfile, request: CVExportRequest) -> CVExportResponse:
        """Export CV as MDX (Markdown with React components)."""
        try:
            # Generate MDX content
            mdx_content = self._generate_mdx_content(cv_profile, request)
            
            return CVExportResponse(
                format="mdx",
                download_url=None,
                content=mdx_content,
                file_size=len(mdx_content.encode('utf-8')),
                expires_at=None
            )
            
        except Exception as e:
            logger.error(f"MDX export failed: {str(e)}")
            raise
    
    def _generate_mdx_content(self, cv_profile: CVProfile, request: CVExportRequest) -> str:
        """Generate MDX content from CV profile."""
        mdx_lines = []
        
        # Header
        mdx_lines.append(f"# {cv_profile.personal_info.first_name} {cv_profile.personal_info.last_name}")
        mdx_lines.append("")
        mdx_lines.append(f"**{cv_profile.personal_info.summary}**")
        mdx_lines.append("")
        
        # Contact Information
        mdx_lines.append("## Contact Information")
        mdx_lines.append(f"- **Email:** {cv_profile.personal_info.email}")
        mdx_lines.append(f"- **Location:** {cv_profile.personal_info.location}")
        mdx_lines.append(f"- **LinkedIn:** [{cv_profile.personal_info.linkedin_url}]({cv_profile.personal_info.linkedin_url})")
        if cv_profile.personal_info.github_url:
            mdx_lines.append(f"- **GitHub:** [{cv_profile.personal_info.github_url}]({cv_profile.personal_info.github_url})")
        if cv_profile.personal_info.website_url:
            mdx_lines.append(f"- **Website:** [{cv_profile.personal_info.website_url}]({cv_profile.personal_info.website_url})")
        mdx_lines.append("")
        
        # Professional Summary
        mdx_lines.append("## Professional Summary")
        mdx_lines.append(cv_profile.personal_info.summary)
        mdx_lines.append("")
        
        # Work Experience
        if cv_profile.experience:
            mdx_lines.append("## Work Experience")
            mdx_lines.append("")
            
            for exp in cv_profile.experience:
                mdx_lines.append(f"### {exp.position}")
                mdx_lines.append(f"**{exp.company}** | {exp.location}")
                mdx_lines.append(f"*{exp.start_date.strftime('%B %Y')} - {exp.end_date.strftime('%B %Y') if exp.end_date else 'Present'}*")
                mdx_lines.append("")
                mdx_lines.append(exp.description)
                mdx_lines.append("")
                
                if request.include_achievements and exp.achievements:
                    mdx_lines.append("**Key Achievements:**")
                    for achievement in exp.achievements:
                        mdx_lines.append(f"- {achievement}")
                    mdx_lines.append("")
                
                if request.include_technologies and exp.technologies:
                    mdx_lines.append("**Technologies:**")
                    for tech in exp.technologies:
                        mdx_lines.append(f"- {tech}")
                    mdx_lines.append("")
        
        # Education
        if cv_profile.education:
            mdx_lines.append("## Education")
            mdx_lines.append("")
            
            for edu in cv_profile.education:
                mdx_lines.append(f"### {edu.degree}")
                mdx_lines.append(f"**{edu.institution}** | {edu.field_of_study}")
                mdx_lines.append(f"*{edu.start_date.strftime('%B %Y')} - {edu.end_date.strftime('%B %Y') if edu.end_date else 'Present'}*")
                if edu.gpa:
                    mdx_lines.append(f"**GPA:** {edu.gpa}")
                if edu.honors:
                    mdx_lines.append(f"**Honors:** {edu.honors}")
                if edu.description:
                    mdx_lines.append(edu.description)
                mdx_lines.append("")
        
        # Skills
        if cv_profile.skills:
            mdx_lines.append("## Skills")
            mdx_lines.append("")
            
            # Programming Languages
            if cv_profile.skills.programming_languages:
                mdx_lines.append("### Programming Languages")
                for skill in cv_profile.skills.programming_languages:
                    level_text = f" ({skill.level.value})" if request.include_scores else ""
                    mdx_lines.append(f"- {skill.name}{level_text}")
                mdx_lines.append("")
            
            # Machine Learning
            if cv_profile.skills.machine_learning:
                mdx_lines.append("### Machine Learning & AI")
                for skill in cv_profile.skills.machine_learning:
                    level_text = f" ({skill.level.value})" if request.include_scores else ""
                    mdx_lines.append(f"- {skill.name}{level_text}")
                mdx_lines.append("")
            
            # Other skill categories
            other_categories = [
                ('frameworks_libraries', 'Frameworks & Libraries'),
                ('databases', 'Databases'),
                ('cloud_platforms', 'Cloud Platforms'),
                ('devops_tools', 'DevOps & Tools'),
                ('mathematical', 'Mathematical Skills'),
                ('soft_skills', 'Soft Skills')
            ]
            
            for category, title in other_categories:
                skills = getattr(cv_profile.skills, category, [])
                if skills:
                    mdx_lines.append(f"### {title}")
                    for skill in skills:
                        level_text = f" ({skill.level.value})" if request.include_scores else ""
                        mdx_lines.append(f"- {skill.name}{level_text}")
                    mdx_lines.append("")
        
        # Certifications
        if cv_profile.certifications:
            mdx_lines.append("## Certifications")
            mdx_lines.append("")
            
            for cert in cv_profile.certifications:
                mdx_lines.append(f"### {cert.name}")
                mdx_lines.append(f"**{cert.issuing_organization}**")
                mdx_lines.append(f"*Issued: {cert.issue_date.strftime('%B %Y')}*")
                if cert.expiry_date:
                    mdx_lines.append(f"*Expires: {cert.expiry_date.strftime('%B %Y')}*")
                if cert.description:
                    mdx_lines.append(cert.description)
                mdx_lines.append("")
        
        # Languages
        if cv_profile.languages:
            mdx_lines.append("## Languages")
            mdx_lines.append("")
            
            for lang in cv_profile.languages:
                mdx_lines.append(f"- **{lang.name}:** {lang.proficiency}")
                if lang.reading and lang.writing and lang.speaking:
                    mdx_lines.append(f"  - Reading: {lang.reading}, Writing: {lang.writing}, Speaking: {lang.speaking}")
            mdx_lines.append("")
        
        # Footer
        mdx_lines.append("---")
        mdx_lines.append(f"*Last updated: {cv_profile.last_updated.strftime('%B %d, %Y at %H:%M UTC')}*")
        mdx_lines.append(f"*Version: {cv_profile.version}*")
        
        return "\n".join(mdx_lines)
    
    def _detect_changes(self, old_profile: CVProfile, new_profile: CVProfile) -> Optional[Dict[str, Any]]:
        """Detect changes between old and new CV profiles."""
        changes = {}
        
        try:
            # Compare personal info
            if old_profile.personal_info.summary != new_profile.personal_info.summary:
                changes["summary"] = {
                    "old": old_profile.personal_info.summary,
                    "new": new_profile.personal_info.summary
                }
            
            # Compare experience
            old_exp_count = len(old_profile.experience)
            new_exp_count = len(new_profile.experience)
            if old_exp_count != new_exp_count:
                changes["experience_count"] = {
                    "old": old_exp_count,
                    "new": new_exp_count
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
                    "new": new_edu_count
                }
            
            # Compare certifications
            old_cert_count = len(old_profile.certifications)
            new_cert_count = len(new_profile.certifications)
            if old_cert_count != new_cert_count:
                changes["certification_count"] = {
                    "old": old_cert_count,
                    "new": new_cert_count
                }
            
            return changes if changes else None
            
        except Exception as e:
            logger.error(f"Error detecting changes: {str(e)}")
            return None
    
    async def _load_cv_from_storage(self) -> Optional[CVProfile]:
        """Load CV profile from storage."""
        try:
            if not self.cv_data_file.exists():
                logger.info("No CV profile found in storage")
                return None
            
            with open(self.cv_data_file, 'r', encoding='utf-8') as f:
                cv_data = json.load(f)
            
            # Convert dates back to datetime objects
            cv_data = self._deserialize_dates(cv_data)
            
            cv_profile = CVProfile(**cv_data)
            logger.info("CV profile loaded from storage")
            return cv_profile
            
        except Exception as e:
            logger.error(f"Error loading CV from storage: {str(e)}")
            return None
    
    async def _save_cv_to_storage(self, cv_profile: CVProfile) -> bool:
        """Save CV profile to storage."""
        try:
            # Serialize dates for JSON storage
            cv_data = self._serialize_dates(cv_profile.dict())
            
            with open(self.cv_data_file, 'w', encoding='utf-8') as f:
                json.dump(cv_data, f, indent=2, ensure_ascii=False)
            
            logger.info("CV profile saved to storage")
            return True
            
        except Exception as e:
            logger.error(f"Error saving CV to storage: {str(e)}")
            return False
    
    def _serialize_dates(self, data: Any) -> Any:
        """Serialize datetime objects to ISO strings for JSON storage."""
        if isinstance(data, dict):
            return {key: self._serialize_dates(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._serialize_dates(item) for item in data]
        elif isinstance(data, datetime):
            return data.isoformat()
        else:
            return data
    
    def _deserialize_dates(self, data: Any) -> Any:
        """Deserialize ISO date strings back to datetime objects."""
        if isinstance(data, dict):
            return {key: self._deserialize_dates(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._deserialize_dates(item) for item in data]
        elif isinstance(data, str):
            # Try to parse as ISO date
            try:
                return datetime.fromisoformat(data.replace('Z', '+00:00'))
            except ValueError:
                return data
        else:
            return data
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Get CV sync status."""
        linkedin_status = linkedin_service.get_sync_status()
        
        return {
            "linkedin_service": linkedin_status,
            "cv_profile_available": self._current_profile is not None,
            "last_cv_update": self._current_profile.last_updated.isoformat() if self._current_profile else None,
            "supported_formats": self.supported_formats
        }


# Global instance for easy access
cv_service = CVService()

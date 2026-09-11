"""
CV data models for professional profile management.

These models define the structure for CV data that can be:
- Fetched from LinkedIn API
- Stored in the database
- Exported to multiple formats (PDF, JSON, MDX)
- Used by AI demo features
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from app.core.time import as_utc, utc_now


class SkillLevel(str, Enum):
    """Skill proficiency levels."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class PersonalInfo(BaseModel):
    """Personal information for CV."""

    first_name: str = Field(..., description="First name")
    last_name: str = Field(..., description="Last name")
    email: str = Field(..., description="Email address")
    phone: str | None = Field(None, description="Phone number")
    location: str = Field(..., description="City, Country")
    linkedin_url: HttpUrl = Field(..., description="LinkedIn profile URL")
    github_url: HttpUrl | None = Field(None, description="GitHub profile URL")
    website_url: HttpUrl | None = Field(None, description="Personal website")
    summary: str = Field(..., description="Professional summary")
    profile_picture_url: HttpUrl | None = Field(None, description="Profile picture URL")


class WorkExperience(BaseModel):
    """Work experience entry."""

    company: str = Field(..., description="Company name")
    position: str = Field(..., description="Job title")
    location: str = Field(..., description="Work location")
    start_date: datetime = Field(..., description="Start date")
    end_date: datetime | None = Field(None, description="End date (null if current)")
    description: str = Field(..., description="Job description")
    achievements: list[str] = Field(
        default_factory=list, description="Key achievements"
    )
    technologies: list[str] = Field(
        default_factory=list, description="Technologies used"
    )
    is_current: bool = Field(
        False, validate_default=True, description="Whether this is the current position"
    )

    @field_validator("is_current", mode="before")
    def set_is_current(cls, v, info):
        """Automatically set is_current based on end_date."""
        return info.data.get("end_date") is None


class Education(BaseModel):
    """Education entry."""

    institution: str = Field(..., description="Institution name")
    degree: str = Field(..., description="Degree obtained")
    field_of_study: str = Field(..., description="Field of study")
    start_date: datetime = Field(..., description="Start date")
    end_date: datetime | None = Field(None, description="End date")
    gpa: float | None = Field(None, description="GPA if available")
    honors: str | None = Field(None, description="Honors or awards")
    description: str | None = Field(None, description="Additional details")


class Skill(BaseModel):
    """Individual skill with proficiency level."""

    name: str = Field(..., description="Skill name")
    level: SkillLevel = Field(..., description="Proficiency level")
    category: str = Field(
        ..., description="Skill category (e.g., 'Programming', 'ML', 'Tools')"
    )
    years_experience: int | None = Field(None, description="Years of experience")
    description: str | None = Field(None, description="Skill description")


class Skills(BaseModel):
    """Collection of skills organized by category."""

    programming_languages: list[Skill] = Field(
        default_factory=list, description="Programming languages"
    )
    frameworks_libraries: list[Skill] = Field(
        default_factory=list, description="Frameworks and libraries"
    )
    machine_learning: list[Skill] = Field(
        default_factory=list, description="ML/AI skills"
    )
    databases: list[Skill] = Field(
        default_factory=list, description="Database technologies"
    )
    cloud_platforms: list[Skill] = Field(
        default_factory=list, description="Cloud platforms"
    )
    devops_tools: list[Skill] = Field(
        default_factory=list, description="DevOps and tools"
    )
    mathematical: list[Skill] = Field(
        default_factory=list, description="Mathematical skills"
    )
    soft_skills: list[Skill] = Field(default_factory=list, description="Soft skills")

    def get_all_skills(self) -> list[Skill]:
        """Get all skills as a flat list."""
        all_skills = []
        for field_name in type(self).model_fields:
            skills = getattr(self, field_name)
            if isinstance(skills, list):
                all_skills.extend(skills)
        return all_skills

    def get_skills_by_category(self, category: str) -> list[Skill]:
        """Get skills by category name."""
        category_map = {
            "programming_languages": self.programming_languages,
            "frameworks_libraries": self.frameworks_libraries,
            "machine_learning": self.machine_learning,
            "databases": self.databases,
            "cloud_platforms": self.cloud_platforms,
            "devops_tools": self.devops_tools,
            "mathematical": self.mathematical,
            "soft_skills": self.soft_skills,
        }
        return category_map.get(category, [])


class Certification(BaseModel):
    """Professional certification."""

    name: str = Field(..., description="Certification name")
    issuing_organization: str = Field(..., description="Issuing organization")
    issue_date: datetime = Field(..., description="Issue date")
    expiry_date: datetime | None = Field(None, description="Expiry date")
    credential_id: str | None = Field(None, description="Credential ID")
    credential_url: HttpUrl | None = Field(
        None, description="Credential verification URL"
    )
    description: str | None = Field(None, description="Certification description")


class Language(BaseModel):
    """Language proficiency."""

    name: str = Field(..., description="Language name")
    proficiency: str = Field(
        ..., description="Proficiency level (e.g., 'Native', 'Fluent', 'Intermediate')"
    )
    reading: str | None = Field(None, description="Reading proficiency")
    writing: str | None = Field(None, description="Writing proficiency")
    speaking: str | None = Field(None, description="Speaking proficiency")


class ProfileProject(BaseModel):
    """Public project evidence, including its stated limitations."""

    name: str
    url: HttpUrl
    description: str
    highlights: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    type: str | None = None


class ProfileAward(BaseModel):
    """Award with source date precision preserved."""

    title: str
    date: str | None = None
    awarder: str | None = None
    summary: str | None = None


class CVProfile(BaseModel):
    """Complete CV profile with all sections."""

    personal_info: PersonalInfo = Field(..., description="Personal information")
    experience: list[WorkExperience] = Field(
        default_factory=list, description="Work experience"
    )
    education: list[Education] = Field(default_factory=list, description="Education")
    skills: Skills = Field(..., description="Skills organized by category")
    certifications: list[Certification] = Field(
        default_factory=list, description="Professional certifications"
    )
    languages: list[Language] = Field(
        default_factory=list, description="Language proficiencies"
    )
    projects: list[ProfileProject] = Field(default_factory=list)
    awards: list[ProfileAward] = Field(default_factory=list)
    date_precision_note: str | None = Field(
        None, description="Source date precision and serialization placeholders"
    )
    last_updated: datetime = Field(
        default_factory=utc_now, description="Last update timestamp"
    )
    linkedin_url: HttpUrl = Field(..., description="LinkedIn profile URL")
    version: str = Field(default="1.0", description="CV version")

    @field_validator("last_updated", mode="after")
    @classmethod
    def normalize_last_updated(cls, value: datetime) -> datetime:
        """Normalize supplied and legacy CV timestamps to aware UTC."""
        return as_utc(value)

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "personal_info": {
                    "first_name": "Cristobal",
                    "last_name": "Cortinez",
                    "email": "cristobal@example.com",
                    "location": "Santiago, Chile",
                    "linkedin_url": "https://linkedin.com/in/cristobal-cortinez-duhalde",
                    "summary": "Data Scientist with expertise in ML, AI, and quantitative finance.",
                },
                "version": "1.0",
            }
        },
    )


class CVExportRequest(BaseModel):
    """Request for CV export in specific format."""

    format: str = Field(..., description="Export format (pdf, json, mdx)")
    include_scores: bool = Field(
        default=False, description="Include skill proficiency scores"
    )
    include_achievements: bool = Field(
        default=True, description="Include work achievements"
    )
    include_technologies: bool = Field(
        default=True, description="Include technologies used"
    )
    custom_sections: list[str] | None = Field(
        None, description="Custom sections to include"
    )


class CVExportResponse(BaseModel):
    """Response for CV export request."""

    format: str = Field(..., description="Export format")
    download_url: HttpUrl | None = Field(None, description="Download URL for file")
    content: str | None = Field(None, description="Content for inline display")
    file_size: int | None = Field(None, description="File size in bytes")
    expires_at: datetime | None = Field(
        None, description="Expiration time for download"
    )


class LinkedInSyncRequest(BaseModel):
    """Request to sync CV data from LinkedIn."""

    force_refresh: bool = Field(
        default=False, description="Force refresh even if recently updated"
    )
    include_connections: bool = Field(
        default=False, description="Include connection data"
    )
    include_recommendations: bool = Field(
        default=False, description="Include recommendations"
    )


class LinkedInSyncResponse(BaseModel):
    """Response for LinkedIn sync operation."""

    success: bool = Field(..., description="Whether sync was successful")
    message: str = Field(..., description="Sync result message")
    last_sync: datetime = Field(..., description="Last sync timestamp")
    data_updated: bool = Field(..., description="Whether data was actually updated")
    changes: dict[str, Any] | None = Field(None, description="Summary of changes made")

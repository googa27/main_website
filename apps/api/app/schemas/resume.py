"""Typed, immutable JSON Resume projection of the curated public CV contract.

This is the supported export subset, not a general JSON Resume input parser.
"""

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ResumeModel(BaseModel):
    """Projection values serialize with the published camel-case field names."""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


class ResumeLink(ResumeModel):
    network: str
    url: HttpUrl


class ResumeLocation(ResumeModel):
    # The source is free text; never infer a street, city or country code.
    general: str


class ResumeBasics(ResumeModel):
    name: str
    summary: str
    email: str
    phone: str | None = None
    url: HttpUrl | None = None
    location: ResumeLocation
    profiles: tuple[ResumeLink, ...] = ()


class ResumeWork(ResumeModel):
    name: str
    position: str
    location: str
    start_date: str = Field(alias="startDate")
    end_date: str | None = Field(None, alias="endDate")
    summary: str
    highlights: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()


class ResumeEducation(ResumeModel):
    institution: str
    area: str
    study_type: str = Field(alias="studyType")
    start_date: str = Field(alias="startDate")
    end_date: str | None = Field(None, alias="endDate")
    score: str | None = None
    summary: str | None = None


class ResumeCertificate(ResumeModel):
    name: str
    issuer: str
    date: str
    url: HttpUrl | None = None


class ResumeSkill(ResumeModel):
    name: str
    level: str | None = None
    keywords: tuple[str, ...] = ()


class ResumeLanguage(ResumeModel):
    language: str
    fluency: str


class ResumeProject(ResumeModel):
    name: str
    description: str
    url: HttpUrl
    highlights: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()
    type: str | None = None


class ResumeAward(ResumeModel):
    title: str
    date: str | None = None
    awarder: str | None = None
    summary: str | None = None


class ResumeMeta(ResumeModel):
    version: str
    last_modified: str = Field(alias="lastModified")
    date_precision_note: str = Field(alias="datePrecisionNote")


class PublicResume(ResumeModel):
    """Public JSON Resume document with stable tuples and no arbitrary extras."""

    basics: ResumeBasics
    work: tuple[ResumeWork, ...]
    education: tuple[ResumeEducation, ...]
    certificates: tuple[ResumeCertificate, ...]
    skills: tuple[ResumeSkill, ...]
    languages: tuple[ResumeLanguage, ...]
    projects: tuple[ResumeProject, ...]
    awards: tuple[ResumeAward, ...]
    meta: ResumeMeta

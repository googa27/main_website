"""Pure public CV projection and fixed, offline JSON Resume schema validation."""

import json
from functools import lru_cache
from importlib.resources import files

from jsonschema import Draft7Validator, FormatChecker
from jsonschema.exceptions import ValidationError

from app.schemas.cv import CVExportRequest, CVProfile
from app.schemas.resume import (
    PublicResume,
    ResumeAward,
    ResumeBasics,
    ResumeCertificate,
    ResumeEducation,
    ResumeLanguage,
    ResumeLink,
    ResumeLocation,
    ResumeMeta,
    ResumeProject,
    ResumeSkill,
    ResumeWork,
)


class ResumeProjectionError(ValueError):
    """The curated profile cannot satisfy the published export schema."""


@lru_cache(maxsize=1)
def _validator() -> Draft7Validator:
    resource = files("app").joinpath("static/schemas/jsonresume-1.3.1.json")
    schema = json.loads(resource.read_text(encoding="utf-8"))
    Draft7Validator.check_schema(schema)
    return Draft7Validator(schema, format_checker=FormatChecker())


def project_resume(
    profile: CVProfile, options: CVExportRequest | None = None
) -> PublicResume:
    """Project one snapshot without mutation, provider acquisition or persistence.

    Career/certificate dates are emitted at month precision; education at year
    precision. This conservative display policy never promotes placeholder days
    to exact evidence. Award date precision is retained and schema-validated.
    """
    request = options or CVExportRequest(format="jsonresume", custom_sections=None)
    personal = profile.personal_info
    links = [ResumeLink(network="LinkedIn", url=personal.linkedin_url)]
    if personal.github_url is not None:
        links.append(ResumeLink(network="GitHub", url=personal.github_url))
    resume = PublicResume(
        basics=ResumeBasics(
            name=f"{personal.first_name} {personal.last_name}",
            summary=personal.summary,
            email=personal.email,
            phone=personal.phone,
            url=personal.website_url,
            location=ResumeLocation(general=personal.location),
            profiles=tuple(links),
        ),
        work=tuple(
            ResumeWork(
                name=item.company,
                position=item.position,
                location=item.location,
                startDate=item.start_date.strftime("%Y-%m"),
                endDate=item.end_date.strftime("%Y-%m") if item.end_date else None,
                summary=item.description,
                highlights=tuple(item.achievements)
                if request.include_achievements
                else (),
                keywords=tuple(item.technologies)
                if request.include_technologies
                else (),
            )
            for item in profile.experience
        ),
        education=tuple(
            ResumeEducation(
                institution=item.institution,
                area=item.field_of_study,
                studyType=item.degree,
                startDate=item.start_date.strftime("%Y"),
                endDate=item.end_date.strftime("%Y") if item.end_date else None,
                score=str(item.gpa) if item.gpa is not None else None,
                summary="; ".join(filter(None, [item.honors, item.description]))
                or None,
            )
            for item in profile.education
        ),
        certificates=tuple(
            ResumeCertificate(
                name=item.name,
                issuer=item.issuing_organization,
                date=item.issue_date.strftime("%Y-%m"),
                url=item.credential_url,
            )
            for item in profile.certifications
        ),
        skills=tuple(
            ResumeSkill(
                name=item.name,
                level=item.level.value if request.include_scores else None,
                keywords=(item.category,),
            )
            for item in profile.skills.get_all_skills()
        ),
        languages=tuple(
            ResumeLanguage(language=item.name, fluency=item.proficiency)
            for item in profile.languages
        ),
        projects=tuple(
            ResumeProject(
                name=item.name,
                description=item.description,
                url=item.url,
                highlights=tuple(item.highlights),
                keywords=tuple(item.keywords),
                type=item.type,
            )
            for item in profile.projects
        ),
        awards=tuple(ResumeAward(**item.model_dump()) for item in profile.awards),
        meta=ResumeMeta(
            version=profile.version,
            lastModified=profile.last_updated.isoformat(),
            datePrecisionNote=profile.date_precision_note
            or "Export display precision: career/certificates month; education year.",
        ),
    )
    try:
        _validator().validate(
            resume.model_dump(mode="json", by_alias=True, exclude_none=True)
        )
    except ValidationError as error:
        # Diagnostics never interpolate the rejected profile value.
        raise ResumeProjectionError(
            "CV does not satisfy the public resume schema"
        ) from error
    return resume


def resume_json(resume: PublicResume) -> str:
    """Serialize deterministic UTF-8 JSON with published field aliases."""
    return resume.model_dump_json(by_alias=True, exclude_none=True, indent=2)

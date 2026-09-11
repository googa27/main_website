"""Read-only curated project projection with explicit non-provider provenance."""

from hashlib import sha256

from app.schemas.cv import CVProfile
from app.schemas.project import Project, ProjectList


def curated_project_page(
    profile: CVProfile | None, *, skip: int = 0, limit: int = 100
) -> ProjectList:
    """Order the complete curated snapshot before slicing; never acquire or write.

    Negative 48-bit URL-derived IDs are stable UI identities, not GitHub IDs.
    Existing numeric metrics use compatibility zeros; the collection explicitly
    marks them unavailable and its timestamp as the profile revision time.
    """
    if skip < 0 or not 1 <= limit <= 100:
        raise ValueError("skip must be nonnegative and limit between 1 and 100")
    projects = []
    if profile is not None:
        ordered = sorted(
            enumerate(profile.projects),
            key=lambda pair: (
                not pair[1].is_featured,
                pair[1].display_priority is None,
                pair[1].display_priority or 0,
                pair[0],
            ),
        )
        identifiers: set[int] = set()
        for _, item in ordered:
            identifier = -(
                int.from_bytes(sha256(str(item.url).encode()).digest()[:6], "big") + 1
            )
            if identifier in identifiers:
                raise ValueError(
                    "Curated project URLs must have unique display identities"
                )
            identifiers.add(identifier)
            projects.append(
                Project(
                    id=identifier,
                    name=item.name,
                    description=item.description,
                    url=item.url,
                    topics=item.keywords,
                    updated_at=profile.last_updated,
                    is_featured=item.is_featured,
                )
            )
    return ProjectList(
        projects=projects[skip : skip + limit],
        total=len(projects),
        source="curated_cv",
        metrics_available=False,
        timestamp_kind="profile_last_updated",
    )

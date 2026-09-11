import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.database import Project as StoredProject
from app.schemas.project import Project, ProjectList, ShowcaseResponse
from app.services.cv import cv_service
from app.services.cv.projects import curated_project_page
from app.services.github_service import GitHubService
from app.services.project_service import ProjectService
from app.services.scoring import scoring_service
from app.services.showcase_service import showcase_service

router = APIRouter()
github_service = GitHubService()


def _project_response(project: StoredProject | None) -> Project:
    """Project one stored row consistently across collection and detail reads."""
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return Project.model_validate(
        {
            "id": project.id,
            "github_id": project.github_id,
            "name": project.name,
            "description": project.description,
            "language": project.language,
            "url": project.url,
            "stars": project.stars,
            "forks": project.forks,
            "topics": json.loads(project.topics) if project.topics else [],
            "updated_at": project.updated_at,
            "is_featured": bool(project.is_featured),
        }
    )


@router.get("/projects", response_model=ProjectList)
async def get_projects(
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    db: Session = Depends(get_db),
):
    """Read a stable database page or an explicit curated fallback without sync."""
    try:
        try:
            total = ProjectService.count_projects(db)
            projects = ProjectService.get_all_projects(db, skip, limit) if total else []
        except SQLAlchemyError:
            total, projects = 0, []

        if total == 0:
            profile = await cv_service.get_current_cv()
            return curated_project_page(profile, skip=skip, limit=limit)

        # Sort projects by intelligent scoring algorithm
        sorted_projects = scoring_service.sort_projects_by_score(projects)
        sorted_projects.sort(key=lambda project: not bool(project.is_featured))

        project_list = [_project_response(project) for project in sorted_projects]

        return ProjectList(projects=project_list, total=total)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e!s}")


@router.get("/projects/showcase", response_model=ShowcaseResponse)
async def get_showcase_projects():
    """Get showcase projects with detailed information and demo links"""
    try:
        return showcase_service.get_showcase_response()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get showcase projects: {e!s}"
        )


@router.get("/projects/showcase/featured")
async def get_featured_showcase_projects(limit: int = 3):
    """Get featured showcase projects (top priority projects)"""
    try:
        featured = showcase_service.get_featured_projects(limit)
        return {"featured_projects": featured, "total": len(featured), "limit": limit}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get featured projects: {e!s}"
        )


@router.get("/projects/showcase/stats")
async def get_showcase_stats():
    """Get showcase statistics and metrics"""
    try:
        return showcase_service.get_showcase_stats()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get showcase stats: {e!s}"
        )


@router.get("/projects/showcase/{project_type}")
async def get_showcase_project_by_type(project_type: str):
    """Get a specific showcase project by type"""
    try:
        from app.schemas.project import ProjectType

        # Convert string to enum
        try:
            project_type_enum = ProjectType(project_type)
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"Invalid project type: {project_type}"
            )

        project = showcase_service.get_project_by_type(project_type_enum)
        if not project:
            raise HTTPException(
                status_code=404, detail=f"Project type {project_type} not found"
            )

        return project

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get project: {e!s}")


@router.get("/projects/featured")
async def get_featured_projects(limit: int = 6, db: Session = Depends(get_db)):
    """Get featured projects"""
    try:
        featured_projects = await github_service.get_featured_projects(db, limit)
        return {"projects": featured_projects, "total": len(featured_projects)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e!s}")


@router.get("/projects/by-id/{project_id}", response_model=Project)
async def get_project_by_id(
    project_id: Annotated[
        int, Path(gt=0, le=2**63 - 1, description="Local database project identifier")
    ],
    db: Session = Depends(get_db),
) -> Project:
    """Read a stored project using the id returned by the database collection."""
    try:
        return _project_response(ProjectService.get_project_by_id(db, project_id))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e!s}")


@router.get("/projects/by-github/{github_id}", response_model=Project)
async def get_project_by_github_id(
    github_id: Annotated[
        int, Path(gt=0, le=2**63 - 1, description="GitHub repository identifier")
    ],
    db: Session = Depends(get_db),
) -> Project:
    """Read a stored project using its explicitly named GitHub identity."""
    return await get_project(github_id, db)


@router.get("/projects/{project_id}", response_model=Project, deprecated=True)
async def get_project(
    project_id: Annotated[int, Path(description="Legacy GitHub repository identifier")],
    db: Session = Depends(get_db),
) -> Project:
    """Legacy GitHub lookup; use by-id or by-github to declare the namespace."""
    try:
        return _project_response(
            ProjectService.get_project_by_github_id(db, project_id)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e!s}")


@router.post("/projects/sync")
async def sync_projects(db: Session = Depends(get_db)):
    """Sync projects from GitHub to database"""
    try:
        result = await github_service.sync_projects_to_database(db)
        return {"message": "Projects synced successfully", "result": result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {e!s}")


@router.get("/projects/{project_id}/score")
async def get_project_score(project_id: int, db: Session = Depends(get_db)):
    """Get detailed scoring breakdown for a specific project"""
    try:
        project = ProjectService.get_project_by_id(db, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        score_breakdown = scoring_service.get_project_score_breakdown(project)
        return {
            "project_id": project_id,
            "project_name": project.name,
            "score_breakdown": score_breakdown,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e!s}")

from fastapi import APIRouter, HTTPException, Depends
from typing import List
import json
from sqlalchemy.orm import Session
from app.models.project import Project, ProjectList, ShowcaseResponse
from app.core.database import get_db
from app.services.github_service import GitHubService
from app.services.database_service import DatabaseService
from app.services.scoring import scoring_service
from app.services.showcase_service import showcase_service

router = APIRouter()
github_service = GitHubService()

@router.get("/projects", response_model=ProjectList)
async def get_projects(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all projects from database with intelligent ordering"""
    try:
        projects = DatabaseService.get_all_projects(db, skip, limit)
        
        # Sort projects by intelligent scoring algorithm
        sorted_projects = scoring_service.sort_projects_by_score(projects)
        
        # Transform database models to Pydantic models
        project_list = []
        for project in sorted_projects:
            project_data = {
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "language": project.language,
                "url": project.url,
                "stars": project.stars,
                "forks": project.forks,
                "topics": json.loads(project.topics) if project.topics else [],
                "updated_at": project.updated_at
            }
            project_list.append(Project(**project_data))
        
        return ProjectList(projects=project_list, total=len(project_list))
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/projects/showcase", response_model=ShowcaseResponse)
async def get_showcase_projects():
    """Get showcase projects with detailed information and demo links"""
    try:
        return showcase_service.get_showcase_response()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get showcase projects: {str(e)}")

@router.get("/projects/showcase/featured")
async def get_featured_showcase_projects(limit: int = 3):
    """Get featured showcase projects (top priority projects)"""
    try:
        featured = showcase_service.get_featured_projects(limit)
        return {
            "featured_projects": featured,
            "total": len(featured),
            "limit": limit
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get featured projects: {str(e)}")

@router.get("/projects/showcase/stats")
async def get_showcase_stats():
    """Get showcase statistics and metrics"""
    try:
        return showcase_service.get_showcase_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get showcase stats: {str(e)}")

@router.get("/projects/showcase/{project_type}")
async def get_showcase_project_by_type(project_type: str):
    """Get a specific showcase project by type"""
    try:
        from app.models.project import ProjectType
        
        # Convert string to enum
        try:
            project_type_enum = ProjectType(project_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid project type: {project_type}")
        
        project = showcase_service.get_project_by_type(project_type_enum)
        if not project:
            raise HTTPException(status_code=404, detail=f"Project type {project_type} not found")
        
        return project
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get project: {str(e)}")

@router.get("/projects/featured")
async def get_featured_projects(limit: int = 6, db: Session = Depends(get_db)):
    """Get featured projects"""
    try:
        featured_projects = await github_service.get_featured_projects(db, limit)
        return {"projects": featured_projects, "total": len(featured_projects)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/projects/{project_id}", response_model=Project)
async def get_project(project_id: int, db: Session = Depends(get_db)):
    """Get a specific project by ID"""
    try:
        project = DatabaseService.get_project_by_github_id(db, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        project_data = {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "language": project.language,
            "url": project.url,
            "stars": project.stars,
            "forks": project.forks,
            "topics": json.loads(project.topics) if project.topics else [],
            "updated_at": project.updated_at
        }
        
        return Project(**project_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/projects/sync")
async def sync_projects(db: Session = Depends(get_db)):
    """Sync projects from GitHub to database"""
    try:
        result = await github_service.sync_projects_to_database(db)
        return {
            "message": "Projects synced successfully",
            "result": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")

@router.get("/projects/{project_id}/score")
async def get_project_score(project_id: int, db: Session = Depends(get_db)):
    """Get detailed scoring breakdown for a specific project"""
    try:
        project = DatabaseService.get_project_by_id(db, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        score_breakdown = scoring_service.get_project_score_breakdown(project)
        return {
            "project_id": project_id,
            "project_name": project.name,
            "score_breakdown": score_breakdown
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

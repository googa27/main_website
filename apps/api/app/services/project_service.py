from datetime import datetime
import json
from typing import List, Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.database import Project


class ProjectService:
    """Service for project-related database operations."""

    @staticmethod
    def get_featured_projects(db: Session, limit: int = 6) -> List[Project]:
        """Return featured projects ordered by star count."""
        return (
            db.query(Project)
            .filter(Project.is_featured == True)  # noqa: E712
            .order_by(desc(Project.stars))
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_all_projects(db: Session, skip: int = 0, limit: int = 100) -> List[Project]:
        """Return all projects ordered by last update."""
        return (
            db.query(Project)
            .order_by(desc(Project.updated_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_project_by_github_id(db: Session, github_id: int) -> Optional[Project]:
        """Return a project matched by its GitHub identifier."""
        return db.query(Project).filter(Project.github_id == github_id).first()

    @staticmethod
    def get_project_by_id(db: Session, project_id: int) -> Optional[Project]:
        """Return a project matched by its database identifier."""
        return db.query(Project).filter(Project.id == project_id).first()

    @staticmethod
    def create_or_update_project(db: Session, project_data: dict) -> Project:
        """Create a new project or update an existing one."""
        github_id = project_data.get("github_id")
        existing_project = ProjectService.get_project_by_github_id(db, github_id)

        if existing_project:
            for key, value in project_data.items():
                if hasattr(existing_project, key) and key != "id":
                    if key == "topics" and isinstance(value, list):
                        setattr(existing_project, key, json.dumps(value))
                    else:
                        setattr(existing_project, key, value)
            existing_project.updated_at = datetime.utcnow()
            db.commit()
            return existing_project
        else:
            if "topics" in project_data and isinstance(project_data["topics"], list):
                project_data["topics"] = json.dumps(project_data["topics"])
            new_project = Project(**project_data)
            db.add(new_project)
            db.commit()
            db.refresh(new_project)
            return new_project

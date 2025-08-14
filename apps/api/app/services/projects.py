import json
import os
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from ..models.project import ProjectInDB, ProjectCreate, ProjectUpdate

# Path to the JSON data file
DATA_FILE = Path(__file__).parent.parent / "data" / "projects.json"

def ensure_data_file():
    """Ensure the data directory and file exist."""
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        with open(DATA_FILE, 'w') as f:
            json.dump([], f)

def get_projects() -> List[ProjectInDB]:
    """Get all projects from the data file."""
    ensure_data_file()
    with open(DATA_FILE, 'r') as f:
        projects_data = json.load(f)
    return [ProjectInDB(**project) for project in projects_data]

def get_project(project_id: str) -> Optional[ProjectInDB]:
    """Get a single project by ID."""
    projects = get_projects()
    for project in projects:
        if project.id == project_id:
            return project
    return None

def create_project(project: ProjectCreate) -> ProjectInDB:
    """Create a new project."""
    projects = get_projects()
    project_dict = project.model_dump()
    project_dict["id"] = str(len(projects) + 1)
    project_dict["created_at"] = datetime.utcnow().isoformat()
    project_dict["updated_at"] = datetime.utcnow().isoformat()
    
    new_project = ProjectInDB(**project_dict)
    projects.append(new_project)
    
    with open(DATA_FILE, 'w') as f:
        json.dump([p.model_dump() for p in projects], f, indent=2)
    
    return new_project

def update_project(project_id: str, project_update: ProjectUpdate) -> Optional[ProjectInDB]:
    """Update an existing project."""
    projects = get_projects()
    for i, project in enumerate(projects):
        if project.id == project_id:
            update_data = project_update.model_dump(exclude_unset=True)
            updated_project = project.model_copy(update=update_data)
            updated_project.updated_at = datetime.utcnow().isoformat()
            projects[i] = updated_project
            
            with open(DATA_FILE, 'w') as f:
                json.dump([p.model_dump() for p in projects], f, indent=2)
            
            return updated_project
    return None

def delete_project(project_id: str) -> bool:
    """Delete a project by ID."""
    projects = get_projects()
    for i, project in enumerate(projects):
        if project.id == project_id:
            del projects[i]
            with open(DATA_FILE, 'w') as f:
                json.dump([p.model_dump() for p in projects], f, indent=2)
            return True
    return False

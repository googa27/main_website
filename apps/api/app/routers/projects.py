from fastapi import APIRouter, HTTPException, status
from typing import List
import json
import os
from pathlib import Path

from ..models.project import Project

router = APIRouter()

@router.get("/", response_model=List[Project])
async def read_projects():
    """
    Retrieve all projects from data/projects.json
    """
    try:
        # Get the path to the data directory relative to this file
        current_dir = Path(__file__).parent
        data_file = current_dir.parent.parent / "data" / "projects.json"
        
        if not data_file.exists():
            # Return empty list if file doesn't exist
            return []
        
        with open(data_file, 'r') as f:
            projects_data = json.load(f)
        
        return [Project(**project) for project in projects_data]
    except Exception as e:
        # Log the error and return empty list for MVP
        print(f"Error loading projects: {e}")
        return []

import httpx
import asyncio
from typing import List, Dict, Any
from app.core.config import settings
from app.services.database_service import DatabaseService
from sqlalchemy.orm import Session
import json

class GitHubService:
    """Service for interacting with GitHub API"""
    
    def __init__(self):
        self.base_url = settings.GITHUB_API_URL
        self.username = settings.GITHUB_USERNAME
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Cristobal-Portfolio-Bot"
        }
    
    async def fetch_user_repos(self) -> List[Dict[str, Any]]:
        """Fetch all public repositories for the user"""
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}/users/{self.username}/repos"
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
    
    async def fetch_repo_details(self, repo_name: str) -> Dict[str, Any]:
        """Fetch detailed information about a specific repository"""
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}/repos/{self.username}/{repo_name}"
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
    
    async def fetch_repo_topics(self, repo_name: str) -> List[str]:
        """Fetch topics for a specific repository"""
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}/repos/{self.username}/{repo_name}/topics"
            headers = self.headers.copy()
            headers["Accept"] = "application/vnd.github.mercy-preview+json"
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data.get("names", [])
    
    def transform_repo_data(self, repo_data: Dict[str, Any], topics: List[str] = None) -> Dict[str, Any]:
        """Transform GitHub repository data to our database format"""
        return {
            "github_id": repo_data["id"],
            "name": repo_data["name"],
            "description": repo_data.get("description", ""),
            "language": repo_data.get("language", "Unknown"),
            "url": repo_data["html_url"],
            "stars": repo_data.get("stargazers_count", 0),
            "forks": repo_data.get("forks_count", 0),
            "topics": topics or [],
            "is_featured": self._is_featured_repo(repo_data, topics or []),
            "created_at": repo_data.get("created_at"),
            "updated_at": repo_data.get("updated_at")
        }
    
    def _is_featured_repo(self, repo_data: Dict[str, Any], topics: List[str]) -> bool:
        """Determine if a repository should be featured"""
        # Featured criteria: high stars, specific topics, or important names
        important_topics = {"machine-learning", "ml", "ai", "data-science", "quantitative-finance", "pde", "optimization"}
        important_names = {"options-pricing", "finite-difference", "optimization", "django", "mlflow"}
        
        # Check if it has important topics
        if any(topic.lower() in important_topics for topic in topics):
            return True
        
        # Check if it has important names
        repo_name = repo_data["name"].lower()
        if any(name in repo_name for name in important_names):
            return True
        
        # Check if it has significant engagement
        if repo_data.get("stargazers_count", 0) >= 5:
            return True
        
        return False
    
    async def sync_projects_to_database(self, db: Session) -> Dict[str, int]:
        """Sync all GitHub projects to the database"""
        try:
            # Fetch all repositories
            repos = await self.fetch_user_repos()
            
            # Filter only public repositories
            public_repos = [repo for repo in repos if not repo.get("private", True)]
            
            created_count = 0
            updated_count = 0
            
            for repo in public_repos:
                try:
                    # Fetch topics for the repository
                    topics = await self.fetch_repo_topics(repo["name"])
                    
                    # Transform the data
                    project_data = self.transform_repo_data(repo, topics)
                    
                    # Check if project already exists
                    existing_project = DatabaseService.get_project_by_github_id(db, repo["id"])
                    
                    if existing_project:
                        # Update existing project
                        DatabaseService.create_or_update_project(db, project_data)
                        updated_count += 1
                    else:
                        # Create new project
                        DatabaseService.create_or_update_project(db, project_data)
                        created_count += 1
                        
                except Exception as e:
                    print(f"Error processing repo {repo['name']}: {e}")
                    continue
            
            return {
                "total_repos": len(public_repos),
                "created": created_count,
                "updated": updated_count
            }
            
        except Exception as e:
            print(f"Error syncing projects: {e}")
            raise
    
    async def get_featured_projects(self, db: Session, limit: int = 6) -> List[Dict[str, Any]]:
        """Get featured projects from database"""
        projects = DatabaseService.get_featured_projects(db, limit)
        return [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "language": p.language,
                "url": p.url,
                "stars": p.stars,
                "forks": p.forks,
                "topics": json.loads(p.topics) if p.topics else [],
                "is_featured": p.is_featured,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None
            }
            for p in projects
        ]

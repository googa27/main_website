from datetime import UTC

from app.services.github_service import GitHubService
from app.services.project_service import ProjectService


class TestGitHubService:
    """Test GitHub service methods."""

    def test_featured_repo_detection(self):
        """Test featured repository detection logic."""
        service = GitHubService()

        repo_data = {"name": "test", "stargazers_count": 1}
        topics = ["machine-learning", "python"]
        assert service._is_featured_repo(repo_data, topics) is True

        repo_data = {"name": "options-pricing", "stargazers_count": 1}
        topics = []
        assert service._is_featured_repo(repo_data, topics) is True

        repo_data = {"name": "random-project", "stargazers_count": 10}
        topics = []
        assert service._is_featured_repo(repo_data, topics) is True

        repo_data = {"name": "random-project", "stargazers_count": 1}
        topics = []
        assert service._is_featured_repo(repo_data, topics) is False

    def test_repo_data_transformation(self, db_session):
        """GitHub timestamps become persistable aware UTC values."""
        service = GitHubService()

        repo_data = {
            "id": 12345,
            "name": "test-project",
            "description": "A test project",
            "language": "Python",
            "html_url": "https://github.com/test/test-project",
            "stargazers_count": 10,
            "forks_count": 5,
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-02T00:00:00Z",
        }

        topics = ["python", "test"]
        transformed = service.transform_repo_data(repo_data, topics)

        assert transformed["github_id"] == 12345
        assert transformed["name"] == "test-project"
        assert transformed["topics"] == ["python", "test"]
        assert transformed["is_featured"] is True
        assert transformed["created_at"].tzinfo is UTC
        assert transformed["updated_at"].tzinfo is UTC

        project = ProjectService.create_or_update_project(db_session, transformed)
        assert project.created_at.tzinfo is UTC
        assert project.updated_at.tzinfo is UTC

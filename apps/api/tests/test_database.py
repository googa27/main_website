import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.database import Base, Project, Contact, ChatSession, ChatMessage, CVDownload
from app.services.database_service import DatabaseService
from app.services.github_service import GitHubService
from datetime import datetime
import json

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db_session():
    """Create a test database session"""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def sample_project_data():
    """Sample project data for testing"""
    return {
        "github_id": 12345,
        "name": "test-project",
        "description": "A test project",
        "language": "Python",
        "url": "https://github.com/test/test-project",
        "stars": 10,
        "forks": 5,
        "topics": json.dumps(["python", "test"]),
        "is_featured": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

@pytest.fixture
def sample_contact_data():
    """Sample contact data for testing"""
    return {
        "name": "Test User",
        "email": "test@example.com",
        "message": "This is a test message",
        "ip_address": "127.0.0.1",
        "user_agent": "Test Browser"
    }

class TestDatabaseModels:
    """Test database models"""
    
    def test_project_model(self, db_session, sample_project_data):
        """Test Project model creation and retrieval"""
        project = Project(**sample_project_data)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)
        
        assert project.id is not None
        assert project.name == "test-project"
        assert project.github_id == 12345
        assert project.is_featured is True
    
    def test_contact_model(self, db_session, sample_contact_data):
        """Test Contact model creation and retrieval"""
        contact = Contact(**sample_contact_data)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)
        
        assert contact.id is not None
        assert contact.name == "Test User"
        assert contact.email == "test@example.com"
        assert contact.is_read is False
    
    def test_chat_session_model(self, db_session):
        """Test ChatSession model"""
        session = ChatSession(
            session_id="test-session-123",
            ip_address="127.0.0.1",
            user_agent="Test Browser"
        )
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)
        
        assert session.id is not None
        assert session.session_id == "test-session-123"
    
    def test_chat_message_model(self, db_session):
        """Test ChatMessage model with relationship"""
        # Create session first
        session = ChatSession(session_id="test-session-123")
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)
        
        # Create message
        message = ChatMessage(
            session_id=session.id,
            role="user",
            content="Hello, AI!"
        )
        db_session.add(message)
        db_session.commit()
        db_session.refresh(message)
        
        assert message.id is not None
        assert message.role == "user"
        assert message.session_id == session.id

class TestDatabaseService:
    """Test database service methods"""
    
    def test_create_or_update_project(self, db_session, sample_project_data):
        """Test project creation and update"""
        # Create new project
        project = DatabaseService.create_or_update_project(db_session, sample_project_data)
        assert project.id is not None
        assert project.name == "test-project"
        
        # Update existing project - use the same github_id but different data
        updated_data = sample_project_data.copy()
        updated_data["stars"] = 20
        updated_data["forks"] = 10
        updated_project = DatabaseService.create_or_update_project(db_session, updated_data)
        assert updated_project.stars == 20
        assert updated_project.forks == 10
        assert updated_project.id == project.id
    
    def test_get_featured_projects(self, db_session, sample_project_data):
        """Test getting featured projects"""
        # Create featured project
        project = DatabaseService.create_or_update_project(db_session, sample_project_data)
        
        # Create non-featured project
        non_featured_data = sample_project_data.copy()
        non_featured_data["github_id"] = 67890
        non_featured_data["name"] = "non-featured"
        non_featured_data["is_featured"] = False
        DatabaseService.create_or_update_project(db_session, non_featured_data)
        
        # Get featured projects
        featured = DatabaseService.get_featured_projects(db_session, limit=10)
        assert len(featured) == 1
        assert featured[0].name == "test-project"
    
    def test_contact_operations(self, db_session, sample_contact_data):
        """Test contact creation and retrieval"""
        # Create contact
        contact = DatabaseService.create_contact(db_session, sample_contact_data)
        assert contact.id is not None
        
        # Get contact by ID
        retrieved = DatabaseService.get_contact_by_id(db_session, contact.id)
        assert retrieved.name == "Test User"
        
        # Mark as read
        success = DatabaseService.mark_contact_as_read(db_session, contact.id)
        assert success is True
        
        # Verify it's marked as read
        retrieved = DatabaseService.get_contact_by_id(db_session, contact.id)
        assert retrieved.is_read is True
    
    def test_chat_operations(self, db_session):
        """Test chat session and message operations"""
        # Create session
        session = DatabaseService.create_chat_session(
            db_session, "test-session", "127.0.0.1", "Test Browser"
        )
        assert session.id is not None
        
        # Add message
        message = DatabaseService.add_chat_message(
            db_session, session.id, "user", "Hello!"
        )
        assert message.id is not None
        assert message.content == "Hello!"
        
        # Get chat history
        history = DatabaseService.get_chat_history(db_session, session.id)
        assert len(history) == 1
        assert history[0].content == "Hello!"
    
    def test_cv_download_tracking(self, db_session):
        """Test CV download tracking"""
        download = DatabaseService.record_cv_download(
            db_session, "127.0.0.1", "Test Browser", "https://example.com"
        )
        assert download.id is not None
        assert download.ip_address == "127.0.0.1"
        assert download.referrer == "https://example.com"

class TestGitHubService:
    """Test GitHub service methods"""
    
    def test_featured_repo_detection(self):
        """Test featured repository detection logic"""
        service = GitHubService()
        
        # Test with important topics
        repo_data = {"name": "test", "stargazers_count": 1}
        topics = ["machine-learning", "python"]
        assert service._is_featured_repo(repo_data, topics) is True
        
        # Test with important names
        repo_data = {"name": "options-pricing", "stargazers_count": 1}
        topics = []
        assert service._is_featured_repo(repo_data, topics) is True
        
        # Test with high stars
        repo_data = {"name": "random-project", "stargazers_count": 10}
        topics = []
        assert service._is_featured_repo(repo_data, topics) is True
        
        # Test with none of the above
        repo_data = {"name": "random-project", "stargazers_count": 1}
        topics = []
        assert service._is_featured_repo(repo_data, topics) is False
    
    def test_repo_data_transformation(self):
        """Test repository data transformation"""
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
            "updated_at": "2023-01-02T00:00:00Z"
        }
        
        topics = ["python", "test"]
        transformed = service.transform_repo_data(repo_data, topics)
        
        assert transformed["github_id"] == 12345
        assert transformed["name"] == "test-project"
        assert transformed["topics"] == ["python", "test"]
        assert transformed["is_featured"] is True

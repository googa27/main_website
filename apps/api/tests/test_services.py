from app.services.database_service import DatabaseService


class TestDatabaseService:
    """Test database service methods."""

    def test_create_or_update_project(self, db_session, sample_project_data):
        """Test project creation and update."""
        project = DatabaseService.create_or_update_project(db_session, sample_project_data)
        assert project.id is not None

        updated_data = sample_project_data.copy()
        updated_data["stars"] = 20
        updated_data["forks"] = 10
        updated_project = DatabaseService.create_or_update_project(db_session, updated_data)
        assert updated_project.stars == 20
        assert updated_project.forks == 10
        assert updated_project.id == project.id

    def test_get_featured_projects(self, db_session, sample_project_data):
        """Test getting featured projects."""
        DatabaseService.create_or_update_project(db_session, sample_project_data)

        non_featured_data = sample_project_data.copy()
        non_featured_data["github_id"] = 67890
        non_featured_data["name"] = "non-featured"
        non_featured_data["is_featured"] = False
        DatabaseService.create_or_update_project(db_session, non_featured_data)

        featured = DatabaseService.get_featured_projects(db_session, limit=10)
        assert len(featured) == 1
        assert featured[0].name == "test-project"

    def test_contact_operations(self, db_session, sample_contact_data):
        """Test contact creation and retrieval."""
        contact = DatabaseService.create_contact(db_session, sample_contact_data)
        assert contact.id is not None

        retrieved = DatabaseService.get_contact_by_id(db_session, contact.id)
        assert retrieved.name == "Test User"

        success = DatabaseService.mark_contact_as_read(db_session, contact.id)
        assert success is True

        retrieved = DatabaseService.get_contact_by_id(db_session, contact.id)
        assert retrieved.is_read is True

    def test_chat_operations(self, db_session):
        """Test chat session and message operations."""
        session = DatabaseService.create_chat_session(
            db_session, "test-session", "127.0.0.1", "Test Browser"
        )
        assert session.id is not None

        message = DatabaseService.add_chat_message(
            db_session, session.id, "user", "Hello!"
        )
        assert message.id is not None
        assert message.content == "Hello!"

        history = DatabaseService.get_chat_history(db_session, session.id)
        assert len(history) == 1
        assert history[0].content == "Hello!"

    def test_cv_download_tracking(self, db_session):
        """Test CV download tracking."""
        download = DatabaseService.record_cv_download(
            db_session, "127.0.0.1", "Test Browser", "https://example.com"
        )
        assert download.id is not None
        assert download.ip_address == "127.0.0.1"
        assert download.referrer == "https://example.com"


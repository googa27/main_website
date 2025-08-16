from app.models.database import Project, Contact, ChatSession, ChatMessage


class TestDatabaseModels:
    """Test database models."""

    def test_project_model(self, db_session, sample_project_data):
        """Test Project model creation and retrieval."""
        project = Project(**sample_project_data)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        assert project.id is not None
        assert project.name == "test-project"
        assert project.github_id == 12345
        assert project.is_featured is True

    def test_contact_model(self, db_session, sample_contact_data):
        """Test Contact model creation and retrieval."""
        contact = Contact(**sample_contact_data)
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)

        assert contact.id is not None
        assert contact.name == "Test User"
        assert contact.email == "test@example.com"
        assert contact.is_read is False

    def test_chat_session_model(self, db_session):
        """Test ChatSession model."""
        session = ChatSession(
            session_id="test-session-123",
            ip_address="127.0.0.1",
            user_agent="Test Browser",
        )
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)

        assert session.id is not None
        assert session.session_id == "test-session-123"

    def test_chat_message_model(self, db_session):
        """Test ChatMessage model with relationship."""
        # Create session first
        session = ChatSession(session_id="test-session-123")
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)

        # Create message
        message = ChatMessage(
            session_id=session.id,
            role="user",
            content="Hello, AI!",
        )
        db_session.add(message)
        db_session.commit()
        db_session.refresh(message)

        assert message.id is not None
        assert message.role == "user"
        assert message.session_id == session.id


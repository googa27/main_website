from typing import List

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.database import ChatSession, ChatMessage


class ChatService:
    """Service for chat session and message management."""

    @staticmethod
    def create_chat_session(
        db: Session, session_id: str, ip_address: str | None = None, user_agent: str | None = None
    ) -> ChatSession:
        """Create a new chat session."""
        new_session = ChatSession(
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        return new_session

    @staticmethod
    def add_chat_message(db: Session, session_id: int, role: str, content: str) -> ChatMessage:
        """Add a message to an existing session."""
        new_message = ChatMessage(session_id=session_id, role=role, content=content)
        db.add(new_message)
        db.commit()
        db.refresh(new_message)
        return new_message

    @staticmethod
    def get_chat_history(db: Session, session_id: int, limit: int = 10) -> List[ChatMessage]:
        """Retrieve chat history for a session."""
        return (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(desc(ChatMessage.timestamp))
            .limit(limit)
            .all()
        )

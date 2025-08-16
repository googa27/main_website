from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from typing import List, Optional
from app.models.database import Project, Contact, ChatSession, ChatMessage, CVDownload
from datetime import datetime
import json

class DatabaseService:
    """Service class for database operations"""
    
    @staticmethod
    def get_featured_projects(db: Session, limit: int = 6) -> List[Project]:
        """Get featured projects"""
        return db.query(Project).filter(Project.is_featured == True).order_by(desc(Project.stars)).limit(limit).all()
    
    @staticmethod
    def get_all_projects(db: Session, skip: int = 0, limit: int = 100) -> List[Project]:
        """Get all projects with pagination"""
        return db.query(Project).order_by(desc(Project.updated_at)).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_project_by_github_id(db: Session, github_id: int) -> Optional[Project]:
        """Get project by GitHub ID"""
        return db.query(Project).filter(Project.github_id == github_id).first()
    
    @staticmethod
    def get_project_by_id(db: Session, project_id: int) -> Optional[Project]:
        """Get project by database ID"""
        return db.query(Project).filter(Project.id == project_id).first()
    
    @staticmethod
    def create_or_update_project(db: Session, project_data: dict) -> Project:
        """Create or update a project from GitHub data"""
        github_id = project_data.get("github_id")
        existing_project = DatabaseService.get_project_by_github_id(db, github_id)
        
        if existing_project:
            # Update existing project
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
            # Create new project
            if "topics" in project_data and isinstance(project_data["topics"], list):
                project_data["topics"] = json.dumps(project_data["topics"])
            
            new_project = Project(**project_data)
            db.add(new_project)
            db.commit()
            db.refresh(new_project)
            return new_project
    
    @staticmethod
    def create_contact(db: Session, contact_data: dict) -> Contact:
        """Create a new contact form submission"""
        new_contact = Contact(**contact_data)
        db.add(new_contact)
        db.commit()
        db.refresh(new_contact)
        return new_contact
    
    @staticmethod
    def get_contact_by_id(db: Session, contact_id: int) -> Optional[Contact]:
        """Get contact by ID"""
        return db.query(Contact).filter(Contact.id == contact_id).first()
    
    @staticmethod
    def mark_contact_as_read(db: Session, contact_id: int) -> bool:
        """Mark a contact as read"""
        contact = DatabaseService.get_contact_by_id(db, contact_id)
        if contact:
            contact.is_read = True
            db.commit()
            return True
        return False
    
    @staticmethod
    def create_chat_session(db: Session, session_id: str, ip_address: str = None, user_agent: str = None) -> ChatSession:
        """Create a new chat session"""
        new_session = ChatSession(
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        return new_session
    
    @staticmethod
    def add_chat_message(db: Session, session_id: int, role: str, content: str) -> ChatMessage:
        """Add a message to a chat session"""
        new_message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content
        )
        db.add(new_message)
        db.commit()
        db.refresh(new_message)
        return new_message
    
    @staticmethod
    def get_chat_history(db: Session, session_id: int, limit: int = 10) -> List[ChatMessage]:
        """Get chat history for a session"""
        return db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(desc(ChatMessage.timestamp)).limit(limit).all()
    
    @staticmethod
    def record_cv_download(db: Session, ip_address: str = None, user_agent: str = None, referrer: str = None) -> CVDownload:
        """Record a CV download"""
        new_download = CVDownload(
            ip_address=ip_address,
            user_agent=user_agent,
            referrer=referrer
        )
        db.add(new_download)
        db.commit()
        db.refresh(new_download)
        return new_download

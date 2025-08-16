from typing import Optional

from sqlalchemy.orm import Session

from app.models.database import Contact


class ContactService:
    """Service for contact form database operations."""

    @staticmethod
    def create_contact(db: Session, contact_data: dict) -> Contact:
        """Create a new contact entry."""
        new_contact = Contact(**contact_data)
        db.add(new_contact)
        db.commit()
        db.refresh(new_contact)
        return new_contact

    @staticmethod
    def get_contact_by_id(db: Session, contact_id: int) -> Optional[Contact]:
        """Retrieve a contact by identifier."""
        return db.query(Contact).filter(Contact.id == contact_id).first()

    @staticmethod
    def mark_contact_as_read(db: Session, contact_id: int) -> bool:
        """Mark a contact as read if it exists."""
        contact = ContactService.get_contact_by_id(db, contact_id)
        if contact:
            contact.is_read = True
            db.commit()
            return True
        return False

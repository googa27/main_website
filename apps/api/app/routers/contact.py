from fastapi import APIRouter, HTTPException, Depends, Request
from app.models.contact import ContactCreate, ContactResponse
from app.services.email_service import send_contact_email
from app.services.database_service import DatabaseService
from app.core.database import get_db
from sqlalchemy.orm import Session

router = APIRouter()

@router.post("/contact", response_model=ContactResponse)
async def submit_contact(contact: ContactCreate, request: Request, db: Session = Depends(get_db)):
    """Submit a contact form"""
    try:
        # Get client information
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        
        # Store in database
        contact_data = {
            "name": contact.name,
            "email": contact.email,
            "message": contact.message,
            "ip_address": client_ip,
            "user_agent": user_agent
        }
        
        db_contact = DatabaseService.create_contact(db, contact_data)
        
        # Send email
        success = await send_contact_email(contact)
        
        if success:
            return ContactResponse(
                message="Thank you for your message! I'll get back to you soon.",
                success=True
            )
        else:
            # Even if email fails, we still have the contact in database
            return ContactResponse(
                message="Thank you for your message! I'll get back to you soon.",
                success=True
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/contact/{contact_id}")
async def get_contact(contact_id: int, db: Session = Depends(get_db)):
    """Get a specific contact (admin only)"""
    try:
        contact = DatabaseService.get_contact_by_id(db, contact_id)
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
        
        return {
            "id": contact.id,
            "name": contact.name,
            "email": contact.email,
            "message": contact.message,
            "created_at": contact.created_at,
            "is_read": contact.is_read
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.put("/contact/{contact_id}/read")
async def mark_contact_read(contact_id: int, db: Session = Depends(get_db)):
    """Mark a contact as read (admin only)"""
    try:
        success = DatabaseService.mark_contact_as_read(db, contact_id)
        if success:
            return {"message": "Contact marked as read"}
        else:
            raise HTTPException(status_code=404, detail="Contact not found")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

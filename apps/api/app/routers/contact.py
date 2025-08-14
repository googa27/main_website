from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from datetime import datetime

from ..models.contact import ContactCreate

router = APIRouter()

@router.post("/", status_code=status.HTTP_201_CREATED)
async def submit_contact_form(contact: ContactCreate):
    """
    Submit a contact form. For MVP, logs to stdout.
    """
    # Log the contact form submission
    timestamp = datetime.utcnow().isoformat()
    print(f"[{timestamp}] Contact Form Submission:")
    print(f"  Name: {contact.name}")
    print(f"  Email: {contact.email}")
    print(f"  Message: {contact.message}")
    print("  ---")
    
    # For MVP, just return success
    # In production, you'd save to database and send email
    return {
        "message": "Contact form submitted successfully",
        "timestamp": timestamp
    }

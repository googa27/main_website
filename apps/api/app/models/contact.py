from pydantic import BaseModel, EmailStr
from datetime import datetime

class ContactBase(BaseModel):
    name: str
    email: EmailStr
    message: str

class ContactCreate(ContactBase):
    pass

class Contact(ContactBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class ContactResponse(BaseModel):
    message: str
    success: bool

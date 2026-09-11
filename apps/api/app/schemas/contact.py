from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class ContactBase(BaseModel):
    name: str
    email: EmailStr
    message: str


class ContactCreate(ContactBase):
    pass


class Contact(ContactBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ContactResponse(BaseModel):
    message: str
    success: bool

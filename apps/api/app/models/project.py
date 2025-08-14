from pydantic import BaseModel, HttpUrl
from typing import List, Optional

class Project(BaseModel):
    id: str
    title: str
    summary: str
    tags: List[str]
    links: dict[str, Optional[str]] = {}
    
    class Config:
        from_attributes = True

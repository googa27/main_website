from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    # Project
    PROJECT_NAME: str = "Portfolio API"
    DEBUG: bool = True
    
    # API
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "your-secret-key-here"  # Change this in production
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",  # Next.js dev server
        "http://127.0.0.1:3000",
        "https://your-domain.vercel.app",  # Replace with your Vercel domain
    ]
    
    # Email settings (for contact form)
    SMTP_TLS: bool = True
    SMTP_PORT: int = 587
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_USER: str = "your-email@gmail.com"
    SMTP_PASSWORD: str = "your-email-password"
    EMAILS_FROM_EMAIL: str = "your-email@gmail.com"
    EMAILS_TO_EMAIL: str = "your-personal-email@gmail.com"
    
    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()

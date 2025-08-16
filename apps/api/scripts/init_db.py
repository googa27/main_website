#!/usr/bin/env python3
"""
Database initialization script for Cristobal Portfolio API
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.core.database import engine, SessionLocal
from app.models.database import Base
from app.services.github_service import GitHubService

def init_database():
    """Initialize the database with tables"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")

def sync_github_projects():
    """Sync projects from GitHub to database"""
    print("Syncing projects from GitHub...")
    
    # Create a session
    db = SessionLocal()
    
    try:
        github_service = GitHubService()
        result = github_service.sync_projects_to_database(db)
        print(f"✅ GitHub sync completed: {result}")
    except Exception as e:
        print(f"❌ GitHub sync failed: {e}")
    finally:
        db.close()

def main():
    """Main function"""
    print("🚀 Initializing Cristobal Portfolio Database...")
    
    # Initialize database
    init_database()
    
    # Sync GitHub projects (optional)
    try:
        sync_github_projects()
    except Exception as e:
        print(f"⚠️  GitHub sync skipped: {e}")
        print("You can run this manually later with: python scripts/sync_github.py")
    
    print("🎉 Database initialization completed!")

if __name__ == "__main__":
    main()

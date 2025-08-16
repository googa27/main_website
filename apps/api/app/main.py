from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.routers import health, projects, contact, ai, cv

app = FastAPI(
    title="Cristobal Portfolio API",
    description="Backend API for Cristobal Cortinez's portfolio website",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(projects.router, prefix="/api", tags=["projects"])
app.include_router(contact.router, prefix="/api", tags=["contact"])
app.include_router(ai.router, prefix="/api", tags=["ai"])
app.include_router(cv.router, prefix="/api", tags=["cv"])

@app.get("/")
async def root():
    return {
        "message": "Cristobal Portfolio API",
        "version": "1.0.0",
        "docs": "/docs"
    }

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API for portfolio website",
    version="1.0.0"
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers
from .routers import projects, contact

# Use the configured API prefix from settings to avoid hard-coded paths
api_prefix = settings.API_V1_STR
app.include_router(projects.router, prefix=f"{api_prefix}/projects", tags=["projects"])
app.include_router(contact.router, prefix=f"{api_prefix}/contact", tags=["contact"])

@app.get("/")
async def root():
    return {"message": "Welcome to the Portfolio API"}

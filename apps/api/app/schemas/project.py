from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ProjectType(str, Enum):
    """Types of projects for showcase."""

    FINITE_DIFFERENCE_OPTIONS = "finite_difference_options"
    DJANGO_OPTIMIZATION = "django_optimization"
    FINITE_ELEMENT_OPTIONS = "finite_element_options"
    ML_MLFLOW = "ml_mlflow"
    OTHER = "other"


class ProjectStatus(str, Enum):
    """Project development status."""

    ACTIVE = "active"
    COMPLETED = "completed"
    IN_PROGRESS = "in_progress"
    PLANNED = "planned"


class ProjectShowcase(BaseModel):
    """Enhanced project showcase information."""

    project_id: int
    name: str
    description: str
    long_description: str | None = None
    project_type: ProjectType
    status: ProjectStatus
    showcase_priority: int = Field(
        ..., ge=1, le=10, description="Priority for showcase (1-10)"
    )

    # Technical details
    technologies: list[str] = Field(default_factory=list)
    complexity_score: float = Field(..., ge=0, le=10)
    mathematical_complexity: str | None = None

    # Demo information
    has_live_demo: bool = False
    demo_url: HttpUrl | None = None
    demo_type: str | None = None  # "streamlit", "web", "api", etc.

    # Project outputs
    outputs: list[str] = Field(
        default_factory=list
    )  # ["pricing_models", "optimization_solver", "risk_metrics"]
    key_features: list[str] = Field(default_factory=list)

    # Links
    github_url: HttpUrl | None = None
    documentation_url: HttpUrl | None = None
    paper_url: HttpUrl | None = None

    # Metrics
    stars: int = 0
    forks: int = 0
    last_updated: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "project_id": 1,
                "name": "Finite Difference Options Pricing",
                "description": "Advanced PDE methods for financial derivatives pricing",
                "project_type": "finite_difference_options",
                "status": "active",
                "showcase_priority": 1,
                "technologies": ["Python", "NumPy", "SciPy", "Streamlit"],
                "complexity_score": 9.5,
                "mathematical_complexity": "Advanced PDE methods, finite difference schemes",
                "has_live_demo": True,
                "demo_url": "https://streamlit-app.example.com",
                "demo_type": "streamlit",
                "outputs": ["option_prices", "greeks", "risk_metrics"],
                "key_features": [
                    "Real-time pricing",
                    "Multiple models",
                    "Risk analysis",
                ],
            }
        },
    )


class ProjectBase(BaseModel):
    name: str
    description: str | None = None
    language: str | None = None
    url: HttpUrl
    stars: int = 0
    forks: int = 0
    topics: list[str] = []
    updated_at: datetime


class ProjectCreate(ProjectBase):
    pass


class Project(ProjectBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class ProjectList(BaseModel):
    projects: list[Project]
    total: int


class ShowcaseProject(BaseModel):
    """Project specifically formatted for showcase display."""

    id: int
    name: str
    description: str
    project_type: ProjectType
    status: ProjectStatus
    showcase_priority: int
    technologies: list[str]
    complexity_score: float
    has_live_demo: bool
    demo_url: HttpUrl | None
    demo_type: str | None
    outputs: list[str]
    key_features: list[str]
    github_url: HttpUrl | None
    stars: int
    forks: int
    last_updated: datetime

    # Computed fields
    is_featured: bool = Field(
        default=False, description="Whether this project is featured in showcase"
    )
    demo_status: str = Field(
        default="not_available", description="Demo availability status"
    )


class ShowcaseResponse(BaseModel):
    """Response for project showcase."""

    featured_projects: list[ShowcaseProject]
    all_projects: list[ShowcaseProject]
    total_featured: int
    total_projects: int
    showcase_updated: datetime

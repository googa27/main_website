"""
Project showcase service for portfolio website.

This service manages showcase information for key projects:
1. Finite Difference Options Pricing (Streamlit)
2. Django Optimization App
3. Finite Element Options (coming soon)
4. ML/MLflow Integration (coming soon)
"""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from app.models.project import (
    ProjectShowcase, ShowcaseProject, ProjectType, 
    ProjectStatus, ShowcaseResponse
)

logger = logging.getLogger(__name__)

class ShowcaseService:
    """Service for managing project showcase information."""
    
    def __init__(self):
        """Initialize the showcase service with key projects."""
        self.showcase_projects = self._initialize_showcase_projects()
        self.last_updated = datetime.now(timezone.utc)
    
    def _initialize_showcase_projects(self) -> List[ProjectShowcase]:
        """Initialize showcase projects with detailed information."""
        return [
            ProjectShowcase(
                project_id=1,
                name="Finite Difference Options Pricing",
                description="Advanced PDE methods for financial derivatives pricing using finite difference schemes",
                long_description="""
                A comprehensive library implementing finite difference methods for options pricing.
                This project demonstrates advanced mathematical modeling in quantitative finance,
                including implementation of various PDE schemes for European and American options.
                
                Key mathematical concepts:
                - Black-Scholes PDE discretization
                - Finite difference schemes (explicit, implicit, Crank-Nicolson)
                - Boundary condition handling
                - Greeks calculation
                - Risk metrics computation
                """,
                project_type=ProjectType.FINITE_DIFFERENCE_OPTIONS,
                status=ProjectStatus.ACTIVE,
                showcase_priority=1,
                technologies=["Python", "NumPy", "SciPy", "Streamlit", "Matplotlib", "Pandas"],
                complexity_score=9.5,
                mathematical_complexity="Advanced PDE methods, finite difference schemes, numerical analysis",
                has_live_demo=True,
                demo_url="https://finite-diff-options.streamlit.app",
                demo_type="streamlit",
                outputs=["option_prices", "greeks", "risk_metrics", "convergence_analysis"],
                key_features=[
                    "Real-time options pricing",
                    "Multiple PDE schemes",
                    "Greeks calculation",
                    "Risk analysis dashboard",
                    "Convergence studies",
                    "Interactive parameter adjustment"
                ],
                github_url="https://github.com/googa27/finite-difference-options",
                documentation_url="https://finite-diff-options.readthedocs.io",
                paper_url=None,
                stars=15,
                forks=3,
                last_updated=datetime(2024, 12, 15, tzinfo=timezone.utc)
            ),
            
            ProjectShowcase(
                project_id=2,
                name="Django Optimization App",
                description="Web-based optimization solver with linear programming capabilities",
                long_description="""
                A Django web application providing optimization problem solving capabilities.
                Users can input linear programming problems and get solutions with visualization.
                Demonstrates web development skills and mathematical optimization implementation.
                
                Features include:
                - Linear programming solver
                - Problem input forms
                - Solution visualization
                - Result export
                - User problem history
                """,
                project_type=ProjectType.DJANGO_OPTIMIZATION,
                status=ProjectStatus.ACTIVE,
                showcase_priority=2,
                technologies=["Python", "Django", "NumPy", "SciPy", "Bootstrap", "Chart.js"],
                complexity_score=7.5,
                mathematical_complexity="Linear programming, optimization algorithms, constraint handling",
                has_live_demo=True,
                demo_url="https://django-optimization.herokuapp.com",
                demo_type="web",
                outputs=["optimization_solutions", "feasibility_reports", "visualization_charts"],
                key_features=[
                    "Linear programming solver",
                    "Interactive problem input",
                    "Solution visualization",
                    "Feasibility analysis",
                    "Result export (CSV, PDF)",
                    "User authentication"
                ],
                github_url="https://github.com/googa27/django-optimization",
                documentation_url="https://django-optimization.readthedocs.io",
                paper_url=None,
                stars=8,
                forks=2,
                last_updated=datetime(2024, 11, 20, tzinfo=timezone.utc)
            ),
            
            ProjectShowcase(
                project_id=3,
                name="Finite Element Options Pricing",
                description="Finite element methods for complex derivative pricing problems",
                long_description="""
                Advanced implementation of finite element methods for options pricing.
                This project extends beyond standard finite difference approaches to handle
                complex geometries and boundary conditions in financial modeling.
                
                Mathematical approach:
                - Finite element discretization
                - Weak formulation of PDEs
                - Adaptive mesh refinement
                - Multi-dimensional problems
                - Complex boundary conditions
                """,
                project_type=ProjectType.FINITE_ELEMENT_OPTIONS,
                status=ProjectStatus.IN_PROGRESS,
                showcase_priority=3,
                technologies=["Python", "FEniCS", "NumPy", "SciPy", "Matplotlib"],
                complexity_score=9.8,
                mathematical_complexity="Finite element methods, weak formulations, adaptive meshing",
                has_live_demo=False,
                demo_url=None,
                demo_type=None,
                outputs=["finite_element_solutions", "mesh_visualizations", "convergence_analysis"],
                key_features=[
                    "Finite element discretization",
                    "Adaptive mesh refinement",
                    "Complex geometry handling",
                    "Multi-dimensional problems",
                    "Advanced boundary conditions",
                    "Performance optimization"
                ],
                github_url="https://github.com/googa27/finite-element-options",
                documentation_url=None,
                paper_url=None,
                stars=5,
                forks=1,
                last_updated=datetime(2024, 12, 10, tzinfo=timezone.utc)
            ),
            
            ProjectShowcase(
                project_id=4,
                name="ML/MLflow Integration",
                description="Machine learning pipeline management with MLflow integration",
                long_description="""
                Comprehensive MLOps solution integrating MLflow for experiment tracking,
                model versioning, and deployment automation. Demonstrates production ML
                pipeline development and best practices.
                
                MLOps features:
                - Experiment tracking
                - Model versioning
                - Automated deployment
                - Performance monitoring
                - A/B testing framework
                """,
                project_type=ProjectType.ML_MLFLOW,
                status=ProjectStatus.PLANNED,
                showcase_priority=4,
                technologies=["Python", "MLflow", "Docker", "Kubernetes", "FastAPI", "PostgreSQL"],
                complexity_score=8.5,
                mathematical_complexity="Machine learning algorithms, statistical modeling, optimization",
                has_live_demo=False,
                demo_url=None,
                demo_type=None,
                outputs=["ml_pipelines", "model_registry", "deployment_automation"],
                key_features=[
                    "Experiment tracking",
                    "Model versioning",
                    "Automated deployment",
                    "Performance monitoring",
                    "A/B testing",
                    "Scalable architecture"
                ],
                github_url="https://github.com/googa27/ml-mlflow-integration",
                documentation_url=None,
                paper_url=None,
                stars=0,
                forks=0,
                last_updated=datetime(2024, 12, 1, tzinfo=timezone.utc)
            )
        ]
    
    def get_showcase_projects(self, include_planned: bool = False) -> List[ShowcaseProject]:
        """Get all showcase projects, optionally including planned ones."""
        projects = []
        
        for project in self.showcase_projects:
            if not include_planned and project.status == ProjectStatus.PLANNED:
                continue
                
            showcase_project = ShowcaseProject(
                id=project.project_id,
                name=project.name,
                description=project.description,
                project_type=project.project_type,
                status=project.status,
                showcase_priority=project.showcase_priority,
                technologies=project.technologies,
                complexity_score=project.complexity_score,
                has_live_demo=project.has_live_demo,
                demo_url=project.demo_url,
                demo_type=project.demo_type,
                outputs=project.outputs,
                key_features=project.key_features,
                github_url=project.github_url,
                stars=project.stars,
                forks=project.forks,
                last_updated=project.last_updated,
                is_featured=project.showcase_priority <= 3,
                demo_status=self._get_demo_status(project)
            )
            projects.append(showcase_project)
        
        # Sort by showcase priority
        projects.sort(key=lambda x: x.showcase_priority)
        return projects
    
    def get_featured_projects(self, limit: int = 3) -> List[ShowcaseProject]:
        """Get featured projects for showcase."""
        all_projects = self.get_showcase_projects(include_planned=False)
        featured = [p for p in all_projects if p.is_featured]
        return featured[:limit]
    
    def get_project_by_type(self, project_type: ProjectType) -> Optional[ShowcaseProject]:
        """Get a specific project by type."""
        for project in self.showcase_projects:
            if project.project_type == project_type:
                return self._convert_to_showcase_project(project)
        return None
    
    def get_showcase_response(self) -> ShowcaseResponse:
        """Get complete showcase response."""
        featured = self.get_featured_projects()
        all_projects = self.get_showcase_projects(include_planned=False)
        
        return ShowcaseResponse(
            featured_projects=featured,
            all_projects=all_projects,
            total_featured=len(featured),
            total_projects=len(all_projects),
            showcase_updated=self.last_updated
        )
    
    def _get_demo_status(self, project: ProjectShowcase) -> str:
        """Get demo status for a project."""
        if not project.has_live_demo:
            return "not_available"
        elif project.status == ProjectStatus.ACTIVE:
            return "available"
        elif project.status == ProjectStatus.IN_PROGRESS:
            return "coming_soon"
        else:
            return "not_available"
    
    def _convert_to_showcase_project(self, project: ProjectShowcase) -> ShowcaseProject:
        """Convert ProjectShowcase to ShowcaseProject."""
        return ShowcaseProject(
            id=project.project_id,
            name=project.name,
            description=project.description,
            project_type=project.project_type,
            status=project.status,
            showcase_priority=project.showcase_priority,
            technologies=project.technologies,
            complexity_score=project.complexity_score,
            has_live_demo=project.has_live_demo,
            demo_url=project.demo_url,
            demo_type=project.demo_type,
            outputs=project.outputs,
            key_features=project.key_features,
            github_url=project.github_url,
            stars=project.stars,
            forks=project.forks,
            last_updated=project.last_updated,
            is_featured=project.showcase_priority <= 3,
            demo_status=self._get_demo_status(project)
        )
    
    def update_project_metrics(self, project_type: ProjectType, stars: int, forks: int):
        """Update GitHub metrics for a project."""
        for project in self.showcase_projects:
            if project.project_type == project_type:
                project.stars = stars
                project.forks = forks
                project.last_updated = datetime.now(timezone.utc)
                logger.info(f"Updated metrics for {project.name}: {stars} stars, {forks} forks")
                break
    
    def get_showcase_stats(self) -> Dict[str, Any]:
        """Get showcase statistics."""
        active_projects = [p for p in self.showcase_projects if p.status == ProjectStatus.ACTIVE]
        total_stars = sum(p.stars for p in self.showcase_projects)
        total_forks = sum(p.forks for p in self.showcase_projects)
        
        return {
            "total_projects": len(self.showcase_projects),
            "active_projects": len(active_projects),
            "total_stars": total_stars,
            "total_forks": total_forks,
            "average_complexity": sum(p.complexity_score for p in self.showcase_projects) / len(self.showcase_projects),
            "projects_with_demos": len([p for p in self.showcase_projects if p.has_live_demo]),
            "last_updated": self.last_updated.isoformat()
        }

# Global instance
showcase_service = ShowcaseService()

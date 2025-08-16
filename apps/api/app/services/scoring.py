"""
Project scoring service for intelligent project ordering.

This service implements a sophisticated scoring algorithm that considers:
- Technical Complexity (50%): ML/AI tools, production experience, mathematical complexity
- GitHub Metrics (30%): Stars, forks, and community engagement  
- Recency (20%): Recent updates and active development
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from app.models.database import Project as DBProject
from app.models.project import Project


class ProjectScoringService:
    """Service for calculating project scores based on multiple factors."""
    
    # Technical complexity indicators with weights
    ML_AI_TOOLS = {
        'tensorflow': 1.0, 'pytorch': 1.0, 'scikit-learn': 0.8, 'scikit': 0.8,
        'mlflow': 0.9, 'kubeflow': 0.9, 'automl': 0.8, 'opencv': 0.7,
        'nltk': 0.7, 'spacy': 0.7, 'transformers': 0.9, 'huggingface': 0.9,
        'xgboost': 0.8, 'lightgbm': 0.8, 'catboost': 0.8, 'keras': 0.8,
        'theano': 0.6, 'caffe': 0.6, 'torch': 0.9, 'tf': 0.9
    }
    
    PRODUCTION_TOOLS = {
        'docker': 1.0, 'kubernetes': 1.0, 'k8s': 1.0, 'ci/cd': 0.9,
        'github actions': 0.8, 'gitlab ci': 0.8, 'jenkins': 0.8,
        'aws': 0.9, 'gcp': 0.9, 'azure': 0.9, 'terraform': 0.9,
        'ansible': 0.8, 'prometheus': 0.8, 'grafana': 0.8, 'elk': 0.8,
        'nginx': 0.7, 'apache': 0.7, 'redis': 0.7, 'postgresql': 0.7,
        'mongodb': 0.7, 'elasticsearch': 0.8, 'kafka': 0.8, 'rabbitmq': 0.8
    }
    
    MATH_COMPLEXITY = {
        'pde': 1.0, 'partial differential': 1.0, 'optimization': 0.9,
        'numerical': 0.8, 'finite element': 0.9, 'finite difference': 0.9,
        'monte carlo': 0.8, 'stochastic': 0.8, 'bayesian': 0.8,
        'regression': 0.7, 'classification': 0.7, 'clustering': 0.7,
        'svm': 0.7, 'random forest': 0.7, 'neural network': 0.8,
        'deep learning': 0.9, 'reinforcement': 0.9, 'genetic': 0.8,
        'quantum': 1.0, 'cryptography': 0.8, 'statistics': 0.7
    }
    
    FRAMEWORKS = {
        'python': 0.6, 'javascript': 0.6, 'typescript': 0.6, 'java': 0.6,
        'cpp': 0.7, 'c++': 0.7, 'c#': 0.6, 'go': 0.7, 'rust': 0.8,
        'scala': 0.7, 'r': 0.7, 'matlab': 0.7, 'julia': 0.8,
        'react': 0.6, 'vue': 0.6, 'angular': 0.6, 'next.js': 0.6,
        'fastapi': 0.6, 'django': 0.6, 'flask': 0.6, 'express': 0.6
    }
    
    def __init__(self):
        """Initialize the scoring service."""
        pass
    
    def calculate_project_score(self, project: DBProject) -> float:
        """
        Calculate the overall project score using the weighted formula:
        
        Score = 0.5 × TechnicalComplexity + 0.3 × GitHubMetrics + 0.2 × RecencyScore
        
        Args:
            project: Database project model
            
        Returns:
            float: Project score between 0 and 10
        """
        # Technical Complexity (50% weight)
        tech_score = self._calculate_technical_complexity(project)
        
        # GitHub Metrics (30% weight)
        github_score = self._calculate_github_metrics(project)
        
        # Recency Score (20% weight)
        recency_score = self._calculate_recency_score(project)
        
        # Calculate weighted final score
        final_score = 0.5 * tech_score + 0.3 * github_score + 0.2 * recency_score
        
        return round(final_score, 2)
    
    def _calculate_technical_complexity(self, project: DBProject) -> float:
        """
        Calculate technical complexity score based on project content.
        
        Formula: Weighted sum of complexity indicators normalized to 0-10 scale.
        
        Args:
            project: Database project model
            
        Returns:
            float: Technical complexity score (0-10)
        """
        score = 0.0
        total_weight = 0.0
        
        # Combine all text fields for analysis
        text_content = f"{project.name} {project.description or ''} {project.language or ''}"
        text_content = text_content.lower()
        
        # ML/AI Tools (40% of tech score)
        ml_score = self._calculate_category_score(text_content, self.ML_AI_TOOLS)
        score += 0.4 * ml_score
        total_weight += 0.4
        
        # Production Tools (30% of tech score)
        prod_score = self._calculate_category_score(text_content, self.PRODUCTION_TOOLS)
        score += 0.3 * prod_score
        total_weight += 0.3
        
        # Mathematical Complexity (20% of tech score)
        math_score = self._calculate_category_score(text_content, self.MATH_COMPLEXITY)
        score += 0.2 * math_score
        total_weight += 0.2
        
        # Framework Diversity (10% of tech score)
        framework_score = self._calculate_category_score(text_content, self.FRAMEWORKS)
        score += 0.1 * framework_score
        total_weight += 0.1
        
        # Normalize to 0-10 scale
        if total_weight > 0:
            normalized_score = (score / total_weight) * 10
        else:
            normalized_score = 0.0
            
        return min(10.0, max(0.0, normalized_score))
    
    def _calculate_category_score(self, text_content: str, indicators: Dict[str, float]) -> float:
        """
        Calculate score for a specific category based on indicator presence.
        
        Args:
            text_content: Lowercase text content to analyze
            indicators: Dictionary of indicators and their weights
            
        Returns:
            float: Category score (0-10)
        """
        found_indicators = []
        
        for indicator, weight in indicators.items():
            if indicator in text_content:
                found_indicators.append(weight)
        
        if not found_indicators:
            return 0.0
        
        # Calculate average weight of found indicators
        avg_weight = sum(found_indicators) / len(found_indicators)
        
        # Bonus for diversity (more indicators = higher score)
        diversity_bonus = min(1.0, len(found_indicators) * 0.2)
        
        # Final category score
        category_score = avg_weight + diversity_bonus
        
        return min(10.0, category_score)
    
    def _calculate_github_metrics(self, project: DBProject) -> float:
        """
        Calculate GitHub metrics score based on stars, forks, and watchers.
        
        Formula: (Stars + 2×Forks + Watchers) / 100 × 10
        
        Args:
            project: Database project model
            
        Returns:
            float: GitHub metrics score (0-10)
        """
        stars = project.stars or 0
        forks = project.forks or 0
        watchers = getattr(project, 'watchers', 0) or 0
        
        # Calculate weighted GitHub score
        github_score = (stars + 2 * forks + watchers) / 100 * 10
        
        # Cap at 10 and ensure non-negative
        return min(10.0, max(0.0, github_score))
    
    def _calculate_recency_score(self, project: DBProject) -> float:
        """
        Calculate recency score based on last update date.
        
        Formula: max(0, 10 - DaysSinceLastUpdate / 30)
        
        Args:
            project: Database project model
            
        Returns:
            float: Recency score (0-10)
        """
        if not project.updated_at:
            return 0.0
        
        # Calculate days since last update
        now = datetime.now(timezone.utc)
        
        # Handle both naive and aware datetimes
        if project.updated_at.tzinfo is None:
            # If database datetime is naive, assume it's UTC
            updated_at = project.updated_at.replace(tzinfo=timezone.utc)
        else:
            updated_at = project.updated_at
        
        days_since_update = (now - updated_at).days
        
        # Calculate recency score
        recency_score = max(0.0, 10.0 - (days_since_update / 30.0))
        
        return min(10.0, recency_score)
    
    def sort_projects_by_score(self, projects: List[DBProject]) -> List[DBProject]:
        """
        Sort projects by their calculated scores in descending order.
        
        Args:
            projects: List of database project models
            
        Returns:
            List[DBProject]: Sorted projects (highest score first)
        """
        # Calculate scores for all projects
        scored_projects = []
        for project in projects:
            score = self.calculate_project_score(project)
            scored_projects.append((project, score))
        
        # Sort by score (descending) and return projects only
        scored_projects.sort(key=lambda x: x[1], reverse=True)
        return [project for project, score in scored_projects]
    
    def get_project_score_breakdown(self, project: DBProject) -> Dict[str, float]:
        """
        Get detailed breakdown of project scoring components.
        
        Args:
            project: Database project model
            
        Returns:
            Dict[str, float]: Detailed scoring breakdown
        """
        tech_score = self._calculate_technical_complexity(project)
        github_score = self._calculate_github_metrics(project)
        recency_score = self._calculate_recency_score(project)
        
        final_score = 0.5 * tech_score + 0.3 * github_score + 0.2 * recency_score
        
        return {
            'technical_complexity': round(tech_score, 2),
            'github_metrics': round(github_score, 2),
            'recency': round(recency_score, 2),
            'final_score': round(final_score, 2),
            'weights': {
                'technical_complexity': 0.5,
                'github_metrics': 0.3,
                'recency': 0.2
            }
        }


# Global instance for easy access
scoring_service = ProjectScoringService()

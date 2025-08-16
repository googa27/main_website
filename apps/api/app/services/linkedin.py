"""
LinkedIn API integration service for CV auto-sync.

This service handles:
- LinkedIn API authentication
- Profile data fetching
- Data transformation to CV models
- Automatic synchronization scheduling
"""

import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
import requests
from app.models.cv import (
    CVProfile, PersonalInfo, WorkExperience, Education, 
    Skills, Skill, SkillLevel, Certification, Language
)
from app.core.config import settings

logger = logging.getLogger(__name__)


class LinkedInService:
    """Service for LinkedIn API integration and CV data management."""
    
    def __init__(self):
        """Initialize LinkedIn service with configuration."""
        self.client_id = os.getenv("LINKEDIN_CLIENT_ID")
        self.client_secret = os.getenv("LINKEDIN_CLIENT_SECRET")
        self.access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
        self.api_base_url = "https://api.linkedin.com/v2"
        self.last_sync = None
        self.sync_interval = timedelta(hours=24)  # Sync every 24 hours
        
        if not self.client_id or not self.client_secret:
            logger.warning("LinkedIn credentials not configured. Auto-sync will be disabled.")
    
    def is_configured(self) -> bool:
        """Check if LinkedIn service is properly configured."""
        return bool(self.client_id and self.client_secret and self.access_token)
    
    def needs_sync(self, force_refresh: bool = False) -> bool:
        """Check if a sync is needed based on last sync time."""
        if force_refresh:
            return True
        
        if not self.last_sync:
            return True
        
        return datetime.now(timezone.utc) - self.last_sync > self.sync_interval
    
    async def sync_profile_data(self, force_refresh: bool = False) -> Optional[CVProfile]:
        """
        Sync LinkedIn profile data and return CV profile.
        
        Args:
            force_refresh: Force refresh even if recently synced
            
        Returns:
            CVProfile if successful, None otherwise
        """
        if not self.is_configured():
            logger.error("LinkedIn service not configured")
            return None
        
        if not self.needs_sync(force_refresh):
            logger.info("LinkedIn sync not needed - data is recent")
            return None
        
        try:
            logger.info("Starting LinkedIn profile sync")
            
            # Fetch profile data
            profile_data = await self._fetch_profile_data()
            if not profile_data:
                logger.error("Failed to fetch LinkedIn profile data")
                return None
            
            # Transform to CV profile
            cv_profile = await self._transform_to_cv_profile(profile_data)
            if not cv_profile:
                logger.error("Failed to transform LinkedIn data to CV profile")
                return None
            
            # Update last sync time
            self.last_sync = datetime.now(timezone.utc)
            
            logger.info("LinkedIn profile sync completed successfully")
            return cv_profile
            
        except Exception as e:
            logger.error(f"LinkedIn sync failed: {str(e)}")
            return None
    
    async def _fetch_profile_data(self) -> Optional[Dict[str, Any]]:
        """Fetch profile data from LinkedIn API."""
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            # Fetch basic profile information
            profile_url = f"{self.api_base_url}/me"
            profile_response = requests.get(profile_url, headers=headers)
            
            if profile_response.status_code != 200:
                logger.error(f"LinkedIn profile API error: {profile_response.status_code}")
                return None
            
            profile_data = profile_response.json()
            
            # Fetch additional profile sections
            additional_data = await self._fetch_additional_profile_data(headers)
            
            # Merge all data
            complete_profile = {**profile_data, **additional_data}
            
            return complete_profile
            
        except Exception as e:
            logger.error(f"Error fetching LinkedIn profile: {str(e)}")
            return None
    
    async def _fetch_additional_profile_data(self, headers: Dict[str, str]) -> Dict[str, Any]:
        """Fetch additional profile sections (experience, education, skills)."""
        additional_data = {}
        
        try:
            # Fetch positions (work experience)
            positions_url = f"{self.api_base_url}/me/positions"
            positions_response = requests.get(positions_url, headers=headers)
            if positions_response.status_code == 200:
                additional_data['positions'] = positions_response.json()
            
            # Fetch education
            education_url = f"{self.api_base_url}/me/educations"
            education_response = requests.get(education_url, headers=headers)
            if education_response.status_code == 200:
                additional_data['educations'] = education_response.json()
            
            # Fetch skills
            skills_url = f"{self.api_base_url}/me/skills"
            skills_response = requests.get(skills_url, headers=headers)
            if skills_response.status_code == 200:
                additional_data['skills'] = skills_response.json()
            
            # Fetch certifications
            certifications_url = f"{self.api_base_url}/me/certifications"
            certifications_response = requests.get(certifications_url, headers=headers)
            if certifications_response.status_code == 200:
                additional_data['certifications'] = certifications_response.json()
            
        except Exception as e:
            logger.warning(f"Error fetching additional profile data: {str(e)}")
        
        return additional_data
    
    async def _transform_to_cv_profile(self, linkedin_data: Dict[str, Any]) -> Optional[CVProfile]:
        """Transform LinkedIn API data to CV profile model."""
        try:
            # Extract personal information
            personal_info = self._extract_personal_info(linkedin_data)
            if not personal_info:
                logger.error("Failed to extract personal information")
                return None
            
            # Extract work experience
            experience = self._extract_work_experience(linkedin_data.get('positions', {}))
            
            # Extract education
            education = self._extract_education(linkedin_data.get('educations', {}))
            
            # Extract skills
            skills = self._extract_skills(linkedin_data.get('skills', {}))
            
            # Extract certifications
            certifications = self._extract_certifications(linkedin_data.get('certifications', {}))
            
            # Extract languages (default to English and Spanish for Chile)
            languages = self._extract_languages(linkedin_data)
            
            # Create CV profile
            cv_profile = CVProfile(
                personal_info=personal_info,
                experience=experience,
                education=education,
                skills=skills,
                certifications=certifications,
                languages=languages,
                last_updated=datetime.now(timezone.utc),
                linkedin_url=personal_info.linkedin_url,
                version="1.0"
            )
            
            return cv_profile
            
        except Exception as e:
            logger.error(f"Error transforming LinkedIn data: {str(e)}")
            return None
    
    def _extract_personal_info(self, data: Dict[str, Any]) -> Optional[PersonalInfo]:
        """Extract personal information from LinkedIn data."""
        try:
            # Basic profile information
            profile = data.get('localizedFirstName', '') + ' ' + data.get('localizedLastName', '')
            first_name = data.get('localizedFirstName', '')
            last_name = data.get('localizedLastName', '')
            
            # Contact information
            email = data.get('emailAddress', '')
            phone = data.get('phoneNumbers', {}).get('values', [{}])[0].get('phoneNumber', '')
            
            # Location
            location = data.get('location', {}).get('name', 'Santiago, Chile')
            
            # LinkedIn URL
            linkedin_url = f"https://linkedin.com/in/{data.get('id', '')}"
            
            # Summary (headline)
            summary = data.get('headline', 'Data Scientist and ML Engineer')
            
            # Profile picture
            profile_picture_url = data.get('profilePicture', {}).get('displayImage', '')
            
            return PersonalInfo(
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone if phone else None,
                location=location,
                linkedin_url=linkedin_url,
                github_url=None,  # Will be filled from other sources
                website_url=None,  # Will be filled from other sources
                summary=summary,
                profile_picture_url=profile_picture_url if profile_picture_url else None
            )
            
        except Exception as e:
            logger.error(f"Error extracting personal info: {str(e)}")
            return None
    
    def _extract_work_experience(self, positions_data: Dict[str, Any]) -> List[WorkExperience]:
        """Extract work experience from LinkedIn positions data."""
        experience = []
        
        try:
            positions = positions_data.get('values', [])
            
            for position in positions:
                try:
                    company = position.get('companyName', '')
                    position_title = position.get('title', '')
                    location = position.get('locationName', '')
                    
                    # Date handling
                    start_date = self._parse_linkedin_date(position.get('startDate', {}))
                    end_date = self._parse_linkedin_date(position.get('endDate', {}))
                    
                    description = position.get('summary', '')
                    
                    # Extract achievements and technologies (if available)
                    achievements = []
                    technologies = []
                    
                    # Try to extract from description
                    if description:
                        # Simple extraction - in real implementation, you might use NLP
                        tech_keywords = ['python', 'tensorflow', 'pytorch', 'docker', 'aws', 'mlflow']
                        for tech in tech_keywords:
                            if tech.lower() in description.lower():
                                technologies.append(tech.title())
                    
                    work_exp = WorkExperience(
                        company=company,
                        position=position_title,
                        location=location,
                        start_date=start_date,
                        end_date=end_date,
                        description=description,
                        achievements=achievements,
                        technologies=technologies,
                        is_current=end_date is None
                    )
                    
                    experience.append(work_exp)
                    
                except Exception as e:
                    logger.warning(f"Error processing position: {str(e)}")
                    continue
            
        except Exception as e:
            logger.error(f"Error extracting work experience: {str(e)}")
        
        return experience
    
    def _extract_education(self, education_data: Dict[str, Any]) -> List[Education]:
        """Extract education from LinkedIn education data."""
        education = []
        
        try:
            educations = education_data.get('values', [])
            
            for edu in educations:
                try:
                    institution = edu.get('schoolName', '')
                    degree = edu.get('degree', '')
                    field_of_study = edu.get('fieldOfStudy', '')
                    
                    start_date = self._parse_linkedin_date(edu.get('startDate', {}))
                    end_date = self._parse_linkedin_date(edu.get('endDate', {}))
                    
                    # GPA and honors (if available)
                    gpa = None
                    honors = None
                    
                    # Description
                    description = edu.get('activities', '')
                    
                    edu_entry = Education(
                        institution=institution,
                        degree=degree,
                        field_of_study=field_of_study,
                        start_date=start_date,
                        end_date=end_date,
                        gpa=gpa,
                        honors=honors,
                        description=description if description else None
                    )
                    
                    education.append(edu_entry)
                    
                except Exception as e:
                    logger.warning(f"Error processing education: {str(e)}")
                    continue
            
        except Exception as e:
            logger.error(f"Error extracting education: {str(e)}")
        
        return education
    
    def _extract_skills(self, skills_data: Dict[str, Any]) -> Skills:
        """Extract and categorize skills from LinkedIn skills data."""
        try:
            # Initialize skill categories
            programming_languages = []
            frameworks_libraries = []
            machine_learning = []
            databases = []
            cloud_platforms = []
            devops_tools = []
            mathematical = []
            soft_skills = []
            
            skills = skills_data.get('values', [])
            
            for skill_info in skills:
                try:
                    skill_name = skill_info.get('skill', {}).get('name', '')
                    if not skill_name:
                        continue
                    
                    # Categorize skill based on name and description
                    category, level = self._categorize_skill(skill_name)
                    
                    skill = Skill(
                        name=skill_name,
                        level=level,
                        category=category,
                        years_experience=None,  # LinkedIn doesn't provide this
                        description=None
                    )
                    
                    # Add to appropriate category
                    if category == 'programming_languages':
                        programming_languages.append(skill)
                    elif category == 'frameworks_libraries':
                        frameworks_libraries.append(skill)
                    elif category == 'machine_learning':
                        machine_learning.append(skill)
                    elif category == 'databases':
                        databases.append(skill)
                    elif category == 'cloud_platforms':
                        cloud_platforms.append(skill)
                    elif category == 'devops_tools':
                        devops_tools.append(skill)
                    elif category == 'mathematical':
                        mathematical.append(skill)
                    else:
                        soft_skills.append(skill)
                        
                except Exception as e:
                    logger.warning(f"Error processing skill: {str(e)}")
                    continue
            
            return Skills(
                programming_languages=programming_languages,
                frameworks_libraries=frameworks_libraries,
                machine_learning=machine_learning,
                databases=databases,
                cloud_platforms=cloud_platforms,
                devops_tools=devops_tools,
                mathematical=mathematical,
                soft_skills=soft_skills
            )
            
        except Exception as e:
            logger.error(f"Error extracting skills: {str(e)}")
            return Skills()
    
    def _categorize_skill(self, skill_name: str) -> tuple[str, SkillLevel]:
        """Categorize a skill and assign proficiency level."""
        skill_lower = skill_name.lower()
        
        # Programming languages
        if skill_lower in ['python', 'javascript', 'typescript', 'java', 'cpp', 'c++', 'c#', 'go', 'rust', 'scala', 'r', 'matlab', 'julia']:
            return 'programming_languages', SkillLevel.ADVANCED
        
        # ML/AI frameworks
        elif skill_lower in ['tensorflow', 'pytorch', 'scikit-learn', 'keras', 'opencv', 'nltk', 'spacy', 'transformers', 'mlflow', 'kubeflow']:
            return 'machine_learning', SkillLevel.ADVANCED
        
        # Databases
        elif skill_lower in ['postgresql', 'mongodb', 'redis', 'elasticsearch', 'mysql', 'sqlite']:
            return 'databases', SkillLevel.INTERMEDIATE
        
        # Cloud platforms
        elif skill_lower in ['aws', 'gcp', 'azure', 'docker', 'kubernetes', 'terraform']:
            return 'cloud_platforms', SkillLevel.INTERMEDIATE
        
        # DevOps tools
        elif skill_lower in ['git', 'jenkins', 'github actions', 'gitlab ci', 'ansible', 'prometheus', 'grafana']:
            return 'devops_tools', SkillLevel.INTERMEDIATE
        
        # Mathematical skills
        elif skill_lower in ['statistics', 'optimization', 'numerical analysis', 'machine learning', 'deep learning', 'pde', 'finite element']:
            return 'mathematical', SkillLevel.ADVANCED
        
        # Frameworks and libraries
        elif skill_lower in ['react', 'vue', 'angular', 'next.js', 'fastapi', 'django', 'flask', 'express']:
            return 'frameworks_libraries', SkillLevel.INTERMEDIATE
        
        # Default to soft skills
        else:
            return 'soft_skills', SkillLevel.INTERMEDIATE
    
    def _extract_certifications(self, certifications_data: Dict[str, Any]) -> List[Certification]:
        """Extract certifications from LinkedIn data."""
        certifications = []
        
        try:
            certs = certifications_data.get('values', [])
            
            for cert in certs:
                try:
                    name = cert.get('name', '')
                    issuing_organization = cert.get('issuingOrganization', {}).get('name', '')
                    
                    # Date handling
                    issue_date = self._parse_linkedin_date(cert.get('issueDate', {}))
                    expiry_date = self._parse_linkedin_date(cert.get('expirationDate', {}))
                    
                    credential_id = cert.get('authority', '')
                    description = cert.get('licenseNumber', '')
                    
                    cert_entry = Certification(
                        name=name,
                        issuing_organization=issuing_organization,
                        issue_date=issue_date,
                        expiry_date=expiry_date,
                        credential_id=credential_id if credential_id else None,
                        credential_url=None,
                        description=description if description else None
                    )
                    
                    certifications.append(cert_entry)
                    
                except Exception as e:
                    logger.warning(f"Error processing certification: {str(e)}")
                    continue
            
        except Exception as e:
            logger.error(f"Error extracting certifications: {str(e)}")
        
        return certifications
    
    def _extract_languages(self, data: Dict[str, Any]) -> List[Language]:
        """Extract language proficiencies."""
        # Default languages for Chile
        languages = [
            Language(
                name="Spanish",
                proficiency="Native",
                reading="Native",
                writing="Native",
                speaking="Native"
            ),
            Language(
                name="English",
                proficiency="Fluent",
                reading="Fluent",
                writing="Fluent",
                speaking="Fluent"
            )
        ]
        
        # Try to extract from LinkedIn data if available
        try:
            language_data = data.get('languages', {}).get('values', [])
            
            for lang in language_data:
                try:
                    name = lang.get('language', {}).get('name', '')
                    proficiency = lang.get('proficiency', {}).get('level', 'Intermediate')
                    
                    # Map LinkedIn proficiency to our levels
                    if proficiency.lower() in ['native', 'native or bilingual']:
                        level = "Native"
                    elif proficiency.lower() in ['full professional', 'professional working']:
                        level = "Fluent"
                    elif proficiency.lower() in ['limited working', 'elementary']:
                        level = "Intermediate"
                    else:
                        level = "Intermediate"
                    
                    # Check if language already exists
                    existing_lang = next((l for l in languages if l.name.lower() == name.lower()), None)
                    if existing_lang:
                        existing_lang.proficiency = level
                        existing_lang.reading = level
                        existing_lang.writing = level
                        existing_lang.speaking = level
                    else:
                        languages.append(Language(
                            name=name,
                            proficiency=level,
                            reading=level,
                            writing=level,
                            speaking=level
                        ))
                        
                except Exception as e:
                    logger.warning(f"Error processing language: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.warning(f"Error extracting languages: {str(e)}")
        
        return languages
    
    def _parse_linkedin_date(self, date_data: Dict[str, Any]) -> Optional[datetime]:
        """Parse LinkedIn date format to datetime."""
        try:
            if not date_data:
                return None
            
            year = date_data.get('year')
            month = date_data.get('month', 1)
            
            if not year:
                return None
            
            return datetime(year=year, month=month, day=1, tzinfo=timezone.utc)
            
        except Exception as e:
            logger.warning(f"Error parsing LinkedIn date: {str(e)}")
            return None
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status."""
        return {
            "configured": self.is_configured(),
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "next_sync": (self.last_sync + self.sync_interval).isoformat() if self.last_sync else None,
            "sync_interval_hours": self.sync_interval.total_seconds() / 3600
        }


# Global instance for easy access
linkedin_service = LinkedInService()

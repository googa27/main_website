"""
CV management API endpoints.

This router provides endpoints for:
- CV data retrieval and management
- LinkedIn auto-sync functionality
- Multiple format exports (PDF, JSON, MDX)
- CV sync status and monitoring
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from app.models.cv import (
    CVProfile, CVExportRequest, CVExportResponse,
    LinkedInSyncRequest, LinkedInSyncResponse
)
from app.services.cv import cv_service
from app.services.linkedin import linkedin_service

router = APIRouter()


@router.get("/cv/profile", response_model=CVProfile)
async def get_cv_profile():
    """Get the current CV profile."""
    try:
        cv_profile = await cv_service.get_current_cv()
        if not cv_profile:
            raise HTTPException(
                status_code=404, 
                detail="No CV profile available. Please sync from LinkedIn first."
            )
        return cv_profile
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to retrieve CV profile: {str(e)}"
        )


@router.post("/cv/sync/linkedin", response_model=LinkedInSyncResponse)
async def sync_cv_from_linkedin(request: LinkedInSyncRequest):
    """Sync CV data from LinkedIn profile."""
    try:
        response = await cv_service.sync_from_linkedin(request)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"LinkedIn sync failed: {str(e)}"
        )


@router.post("/cv/export", response_model=CVExportResponse)
async def export_cv(request: CVExportRequest):
    """Export CV in the requested format."""
    try:
        response = await cv_service.export_cv(request)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"CV export failed: {str(e)}"
        )


@router.get("/cv/export/{format}")
async def export_cv_simple(
    format: str,
    include_scores: bool = Query(False, description="Include skill proficiency scores"),
    include_achievements: bool = Query(True, description="Include work achievements"),
    include_technologies: bool = Query(True, description="Include technologies used")
):
    """Export CV in the specified format with query parameters."""
    try:
        request = CVExportRequest(
            format=format,
            include_scores=include_scores,
            include_achievements=include_achievements,
            include_technologies=include_technologies
        )
        
        response = await cv_service.export_cv(request)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"CV export failed: {str(e)}"
        )


@router.get("/cv/status")
async def get_cv_status():
    """Get CV sync and export status."""
    try:
        status = cv_service.get_sync_status()
        return status
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to get CV status: {str(e)}"
        )


@router.get("/cv/formats")
async def get_supported_formats():
    """Get list of supported CV export formats."""
    try:
        formats = cv_service.supported_formats
        return {
            "supported_formats": formats,
            "description": "Available export formats for CV data"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to get supported formats: {str(e)}"
        )


@router.get("/cv/linkedin/status")
async def get_linkedin_status():
    """Get LinkedIn service status and sync information."""
    try:
        status = linkedin_service.get_sync_status()
        return status
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to get LinkedIn status: {str(e)}"
        )


@router.get("/cv/download")
async def download_cv(
    format: str = Query("json", description="Export format"),
    include_scores: bool = Query(False, description="Include skill proficiency scores"),
    include_achievements: bool = Query(True, description="Include work achievements"),
    include_technologies: bool = Query(True, description="Include technologies used")
):
    """
    Download CV in the specified format.
    
    This endpoint provides a simple way to download CV data
    with configurable export options.
    """
    try:
        request = CVExportRequest(
            format=format,
            include_scores=include_scores,
            include_achievements=include_achievements,
            include_technologies=include_technologies
        )
        
        response = await cv_service.export_cv(request)
        
        # For now, return the content directly
        # In a real implementation, you might want to:
        # 1. Generate actual files (especially for PDF)
        # 2. Store them temporarily with download URLs
        # 3. Implement proper file download handling
        
        return {
            "format": response.format,
            "content": response.content,
            "file_size": response.file_size,
            "download_note": "Content is returned directly. For file downloads, use the /cv/export endpoint."
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"CV download failed: {str(e)}"
        )

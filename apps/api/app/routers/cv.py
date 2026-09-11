"""
CV management API endpoints.

This router provides endpoints for:
- CV data retrieval and management
- LinkedIn auto-sync functionality
- Multiple format exports (PDF, JSON, MDX)
- CV sync status and monitoring
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.schemas.cv import (
    CVExportRequest,
    CVExportResponse,
    CVProfile,
    LinkedInSyncRequest,
    LinkedInSyncResponse,
)
from app.schemas.resume import PublicResume
from app.services.cv import CVProfileUnavailableError, cv_service
from app.services.cv.pdf import PDFUnavailableError
from app.services.cv.resume import ResumeProjectionError, resume_json
from app.services.linkedin import linkedin_service

router = APIRouter()


@router.get("/cv/resume", response_model=PublicResume, response_model_exclude_none=True)
async def get_public_resume() -> PublicResume:
    """Return JSON Resume from the current curated public CV snapshot."""
    try:
        return await cv_service.get_public_resume()
    except CVProfileUnavailableError as error:
        raise HTTPException(status_code=404, detail="Public CV unavailable") from error
    except ResumeProjectionError as error:
        raise HTTPException(
            status_code=422, detail="Public CV export is invalid"
        ) from error


@router.get("/cv/resume/download")
async def download_public_resume() -> Response:
    """Download the same JSON Resume document as a UTF-8 attachment."""
    resume = await get_public_resume()
    return Response(
        content=resume_json(resume),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="resume.json"'},
    )


@router.get("/cv/pdf")
async def download_public_pdf(
    include_scores: bool = False,
    include_achievements: bool = True,
    include_technologies: bool = True,
) -> Response:
    """Return a real PDF, or an explicit unavailable/error HTTP response."""
    options = CVExportRequest(
        format="pdf",
        include_scores=include_scores,
        include_achievements=include_achievements,
        include_technologies=include_technologies,
    )
    try:
        content = await cv_service.render_public_pdf(options)
    except CVProfileUnavailableError as error:
        raise HTTPException(status_code=404, detail="Public CV unavailable") from error
    except PDFUnavailableError as error:
        raise HTTPException(
            status_code=503, detail="PDF export is unavailable"
        ) from error
    except ResumeProjectionError as error:
        raise HTTPException(
            status_code=422, detail="Public CV export is invalid"
        ) from error
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="resume.pdf"'},
    )


@router.get("/cv/profile", response_model=CVProfile)
async def get_cv_profile():
    """Get the current CV profile."""
    try:
        cv_profile = await cv_service.get_current_cv()
        if not cv_profile:
            raise HTTPException(
                status_code=404,
                detail="No CV profile available. Please sync from LinkedIn first.",
            )
        return cv_profile
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve CV profile: {e!s}"
        )


@router.post("/cv/sync/linkedin", response_model=LinkedInSyncResponse)
async def sync_cv_from_linkedin(request: LinkedInSyncRequest):
    """Sync CV data from LinkedIn profile."""
    try:
        response = await cv_service.sync_from_linkedin(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LinkedIn sync failed: {e!s}")


@router.post("/cv/export", response_model=CVExportResponse)
async def export_cv(request: CVExportRequest):
    """Export CV in the requested format."""
    try:
        response = await cv_service.export_cv(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CV export failed: {e!s}")


@router.get("/cv/export/{format}")
async def export_cv_simple(
    format: str,
    include_scores: bool = Query(False, description="Include skill proficiency scores"),
    include_achievements: bool = Query(True, description="Include work achievements"),
    include_technologies: bool = Query(True, description="Include technologies used"),
):
    """Export CV in the specified format with query parameters."""
    try:
        request = CVExportRequest(
            format=format,
            include_scores=include_scores,
            include_achievements=include_achievements,
            include_technologies=include_technologies,
        )

        response = await cv_service.export_cv(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CV export failed: {e!s}")


@router.get("/cv/status")
async def get_cv_status():
    """Get CV sync and export status."""
    try:
        status = cv_service.get_sync_status()
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get CV status: {e!s}")


@router.get("/cv/formats")
async def get_supported_formats():
    """Get list of supported CV export formats."""
    try:
        formats = cv_service.supported_formats
        return {
            "supported_formats": formats,
            "description": "Available export formats for CV data",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get supported formats: {e!s}"
        )


@router.get("/cv/linkedin/status")
async def get_linkedin_status():
    """Get LinkedIn service status and sync information."""
    try:
        status = linkedin_service.get_sync_status()
        return status
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get LinkedIn status: {e!s}"
        )


@router.get("/cv/download")
async def download_cv(
    format: str = Query("json", description="Export format"),
    include_scores: bool = Query(False, description="Include skill proficiency scores"),
    include_achievements: bool = Query(True, description="Include work achievements"),
    include_technologies: bool = Query(True, description="Include technologies used"),
):
    """
    Download CV in the specified format.

    This endpoint provides a simple way to download CV data
    with configurable export options.
    """
    if format.lower() == "pdf":
        return await download_public_pdf(
            include_scores=include_scores,
            include_achievements=include_achievements,
            include_technologies=include_technologies,
        )
    try:
        request = CVExportRequest(
            format=format,
            include_scores=include_scores,
            include_achievements=include_achievements,
            include_technologies=include_technologies,
        )

        response = await cv_service.export_cv(request)

        # Preserve legacy text envelopes; binary PDF dispatch happens above.
        return {
            "format": response.format,
            "content": response.content,
            "file_size": response.file_size,
            "download_path": response.download_path,
            "download_note": "Text content is returned directly. JSON Resume attachments use /cv/resume/download.",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CV download failed: {e!s}")

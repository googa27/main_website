"""Independent schema/PDF oracles and public route boundaries for CV exports."""

import asyncio
import builtins
import json
from concurrent.futures import ThreadPoolExecutor
from importlib.resources import files
from io import BytesIO
from pathlib import Path

import httpx
import pytest
from jsonschema import Draft7Validator, FormatChecker
from pydantic import ValidationError
from pypdf import PdfReader

from app.main import app
from app.schemas.cv import CVExportRequest, CVProfile
from app.schemas.resume import PublicResume
from app.services.cv import CVService
from app.services.cv.pdf import PDFUnavailableError, render_pdf
from app.services.cv.resume import ResumeProjectionError, project_resume, resume_json


@pytest.fixture
def profile():
    return CVProfile.model_validate_json(
        (Path(__file__).parent / "fixtures/public_cv.json").read_text()
    )


def test_projection_matches_official_schema_preserves_evidence_and_precision(profile):
    before = profile.model_dump_json()
    resume = project_resume(profile)
    payload = json.loads(resume_json(resume))
    schema = json.loads(
        files("app").joinpath("static/schemas/jsonresume-1.3.1.json").read_text()
    )
    Draft7Validator(schema, format_checker=FormatChecker()).validate(payload)
    assert payload["work"][0]["startDate"] == "2024-03"
    assert "endDate" not in payload["work"][0]
    assert payload["education"][0]["startDate"] == "2020"
    assert payload["awards"][0]["date"] == "2024-02"
    assert payload["projects"][0]["highlights"] == ["Not calibrated or deployed."]
    assert "phone" not in payload["basics"]
    assert "level" not in payload["skills"][0]
    assert "Day01" in payload["meta"]["datePrecisionNote"]
    assert PublicResume.model_validate_json(resume_json(resume)) == resume
    assert resume_json(project_resume(profile)) == resume_json(resume)
    assert profile.model_dump_json() == before
    with pytest.raises(ValidationError):
        resume.basics.name = "mutation"


def test_options_and_invalid_award_date_are_explicit(profile):
    resume = project_resume(
        profile,
        CVExportRequest(
            format="jsonresume",
            include_scores=True,
            include_achievements=False,
            include_technologies=False,
        ),
    )
    assert resume.skills[0].level == "advanced"
    assert not resume.work[0].highlights and not resume.work[0].keywords
    profile.awards[0].date = "SYNTHETIC_REJECTED_DATE"
    with pytest.raises(ResumeProjectionError) as error:
        project_resume(profile)
    assert "SYNTHETIC_REJECTED_DATE" not in str(error.value)


def test_optional_pdf_absence_does_not_disable_json_resume(profile, monkeypatch):
    original = builtins.__import__

    def without_pdf(name, *args, **kwargs):
        if name == "reportlab" or name.startswith("reportlab."):
            raise ImportError("synthetic missing optional extra")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", without_pdf)
    resume = project_resume(profile)
    assert json.loads(resume_json(resume))["basics"]["name"] == "Éva Example"
    with pytest.raises(PDFUnavailableError, match=r"portfolio-api\[pdf\]"):
        render_pdf(resume)


def test_actual_pdf_escapes_markup_retains_unicode_and_evidence(profile, monkeypatch):
    import reportlab.lib.utils

    def reject_image(*args, **kwargs):
        raise AssertionError("PDF text attempted asset loading")

    monkeypatch.setattr(reportlab.lib.utils, "ImageReader", reject_image)
    marker = '<img src="https://example.test/forbidden"/> & <b>literal</b>'
    profile.personal_info.summary = marker
    resume = project_resume(profile)
    pdf = render_pdf(resume)
    assert pdf == render_pdf(resume)
    reader = PdfReader(BytesIO(pdf), strict=True)
    text = "\n".join(page.extract_text() for page in reader.pages)
    assert "Éva Example" in text and "École Example" in text
    assert marker in text
    assert "Not calibrated or deployed." in text
    assert "2024-03" in text and "Day01" in text
    assert reader.metadata.title == "Public professional resume"
    assert all(not page.get("/Annots") for page in reader.pages)


def test_pdf_concurrent_documents_do_not_mix_text(profile):
    first = project_resume(profile)
    profile.personal_info.first_name = "Other"
    second = project_resume(profile)
    with ThreadPoolExecutor(max_workers=2) as pool:
        pdfs = list(pool.map(render_pdf, [first, second]))
    texts = [
        "\n".join(p.extract_text() for p in PdfReader(BytesIO(pdf)).pages)
        for pdf in pdfs
    ]
    assert "Éva Example" in texts[0] and "Other Example" not in texts[0]
    assert "Other Example" in texts[1] and "Éva Example" not in texts[1]


async def test_routes_return_schema_and_binary_without_acquisition(
    profile, monkeypatch
):
    from app.routers import cv

    service = CVService()
    service._current_profile = profile
    monkeypatch.setattr(cv, "cv_service", service)
    before = profile.model_dump_json()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/cv/resume")
        assert response.status_code == 200
        assert response.json()["work"][0]["startDate"] == "2024-03"
        downloaded = await client.get("/api/cv/resume/download")
        assert downloaded.json() == response.json()
        assert 'filename="resume.json"' in downloaded.headers["content-disposition"]
        pdf = await client.get("/api/cv/pdf")
        assert (
            pdf.status_code == 200 and pdf.headers["content-type"] == "application/pdf"
        )
        assert len(PdfReader(BytesIO(pdf.content)).pages) >= 1
    assert profile.model_dump_json() == before


async def test_pdf_route_absence_and_export_descriptor(profile, monkeypatch):
    from app.routers import cv

    service = CVService()
    service._current_profile = profile
    monkeypatch.setattr(cv, "cv_service", service)
    descriptor = await service.export_cv(
        CVExportRequest(format="pdf", include_scores=True)
    )
    assert (
        descriptor.content is None and "include_scores=true" in descriptor.download_path
    )
    assert descriptor.file_size is None

    async def unavailable(options):
        raise PDFUnavailableError("missing dependency")

    monkeypatch.setattr(service, "render_public_pdf", unavailable)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/cv/pdf")
    assert response.status_code == 503
    assert response.json() == {"detail": "PDF export is unavailable"}


async def test_pdf_generation_yields_to_event_loop(profile, monkeypatch):
    from threading import Event

    from app.services.cv import service as owner

    started, release = Event(), Event()

    def render(resume):
        started.set()
        assert release.wait(2)
        return b"synthetic PDF"

    service = CVService()
    service._current_profile = profile
    monkeypatch.setattr(owner, "render_pdf", render)
    task = asyncio.create_task(service.render_public_pdf())
    assert await asyncio.to_thread(started.wait, 2)
    assert not task.done()
    release.set()
    assert await task == b"synthetic PDF"


def test_cli_refusal_preserves_previous_output(tmp_path, monkeypatch, capsys):
    from app.services.cv import export

    output = tmp_path / "previous.pdf"
    output.write_bytes(b"previous valid artifact")

    async def unavailable(format_name):
        raise PDFUnavailableError("missing")

    monkeypatch.setattr(export, "_content", unavailable)
    assert export.main(["--format", "pdf", "--output", str(output)]) == 2
    assert output.read_bytes() == b"previous valid artifact"
    assert json.loads(capsys.readouterr().err)["error"] == "PDF renderer unavailable"


def test_cli_atomic_replacement_failure_preserves_previous_output(
    tmp_path, monkeypatch
):
    from app.services.cv.export import _write_atomic

    output = tmp_path / "resume.json"
    output.write_bytes(b"previous")

    def failed_replace(self, target):
        raise OSError("synthetic replace failure")

    monkeypatch.setattr(Path, "replace", failed_replace)
    with pytest.raises(OSError):
        _write_atomic(output, b"new")
    assert output.read_bytes() == b"previous"
    assert list(tmp_path.iterdir()) == [output]

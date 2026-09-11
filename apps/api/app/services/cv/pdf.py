"""Optional text-only PDF rendering of a validated public résumé."""

from html import escape
from importlib.resources import as_file, files
from io import BytesIO
from threading import Lock

from app.schemas.resume import PublicResume

_FONT_LOCK = Lock()
_FONT_NAME = "PortfolioVera"


class PDFUnavailableError(RuntimeError):
    """The optional PDF renderer is unavailable in this installation."""


def render_pdf(resume: PublicResume) -> bytes:
    """Render escaped literal text; no caller markup, links or assets are loaded."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import Paragraph, SimpleDocTemplate
    except ImportError as error:
        raise PDFUnavailableError(
            "Install portfolio-api[pdf] to enable PDF exports"
        ) from error

    # The font ships with the pinned renderer; do not read host fonts or download.
    with _FONT_LOCK:
        if _FONT_NAME not in pdfmetrics.getRegisteredFontNames():
            with as_file(files("reportlab").joinpath("fonts/Vera.ttf")) as path:
                pdfmetrics.registerFont(TTFont(_FONT_NAME, str(path)))

    styles = getSampleStyleSheet()
    for name in ("Normal", "Title", "Heading2"):
        styles[name].fontName = _FONT_NAME
        styles[name].leading = styles[name].fontSize * 1.4
        styles[name].spaceAfter = 6
    styles.add(
        ParagraphStyle("Metadata", parent=styles["Normal"], fontSize=8, leading=11)
    )
    styles.add(ParagraphStyle("Entry", parent=styles["Normal"], keepWithNext=True))
    story = []

    def paragraph(text: str, style: str = "Normal") -> None:
        # Paragraph accepts XML, including img tags. Only our constant line breaks
        # are markup: escaping happens before newline substitution for every field.
        literal = escape(text, quote=True).replace("\n", "<br/>")
        story.append(Paragraph(literal, styles[style]))

    def section(title: str) -> None:
        paragraph(title, "Heading2")

    basics = resume.basics
    paragraph(basics.name, "Title")
    paragraph(basics.location.general)
    paragraph(" | ".join(value for value in (basics.email, basics.phone) if value))
    paragraph(basics.summary)
    for link in basics.profiles:
        paragraph(f"{link.network}: {link.url}", "Metadata")

    if resume.work:
        section("Experience")
        for job in resume.work:
            paragraph(f"{job.position} - {job.name}", "Entry")
            paragraph(
                f"{job.start_date} - {job.end_date or 'Present'} | {job.location}",
                "Metadata",
            )
            paragraph(job.summary)
            for highlight in job.highlights:
                paragraph(f"- {highlight}")
            if job.keywords:
                paragraph("Technologies: " + ", ".join(job.keywords), "Metadata")
    if resume.education:
        section("Education")
        for education in resume.education:
            paragraph(
                f"{education.institution} - {education.study_type}, {education.area}",
                "Entry",
            )
            paragraph(
                " - ".join(
                    value
                    for value in (education.start_date, education.end_date)
                    if value
                ),
                "Metadata",
            )
            if education.summary:
                paragraph(education.summary)
    if resume.projects:
        section("Projects and evidence")
        for project in resume.projects:
            paragraph(project.name, "Entry")
            paragraph(project.description)
            for highlight in project.highlights:
                paragraph(f"- {highlight}")
            paragraph(str(project.url), "Metadata")
    if resume.skills:
        section("Skills")
        paragraph(
            "; ".join(
                f"{item.name} ({item.level})" if item.level else item.name
                for item in resume.skills
            )
        )
    if resume.certificates:
        section("Certificates")
        for certificate in resume.certificates:
            paragraph(f"{certificate.name} - {certificate.issuer} ({certificate.date})")
    if resume.awards:
        section("Awards")
        for award in resume.awards:
            paragraph(
                " - ".join(
                    value for value in (award.title, award.awarder, award.date) if value
                )
            )
            if award.summary:
                paragraph(award.summary)
    if resume.languages:
        section("Languages")
        paragraph(
            "; ".join(f"{item.language}: {item.fluency}" for item in resume.languages)
        )
    paragraph(resume.meta.date_precision_note, "Metadata")
    paragraph(f"Profile last updated: {resume.meta.last_modified}", "Metadata")
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=42,
        rightMargin=42,
        topMargin=42,
        bottomMargin=42,
        title="Public professional resume",
        author=basics.name,
        invariant=1,
    )
    document.build(story)
    return buffer.getvalue()

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_react_folio_consolidation_evidence_is_static_first() -> None:
    copied_resume = ROOT / "apps/web/src/data/react-folio-resume.json"
    content_adapter = ROOT / "apps/web/src/lib/content.ts"
    projects_page = ROOT / "apps/web/src/app/projects/page.tsx"
    evidence_doc = ROOT / "docs/REACT_FOLIO_CONSOLIDATION.md"
    next_config = ROOT / "apps/web/next.config.ts"

    assert copied_resume.is_file()
    assert content_adapter.is_file()
    assert evidence_doc.is_file()
    assert "one-way consolidation" in evidence_doc.read_text(encoding="utf-8")
    assert "FastAPI remains optional" in evidence_doc.read_text(encoding="utf-8")
    assert 'output: "export"' in next_config.read_text(encoding="utf-8")
    assert "fetch(" not in projects_page.read_text(encoding="utf-8")


def test_react_folio_resume_copy_is_redacted_and_structured() -> None:
    copied_resume = ROOT / "apps/web/src/data/react-folio-resume.json"
    content_adapter = ROOT / "apps/web/src/lib/content.ts"
    resume = json.loads(copied_resume.read_text(encoding="utf-8"))
    content = content_adapter.read_text(encoding="utf-8")

    assert "phone" not in resume["basics"]
    assert len(resume["work"]) == 14
    assert len(resume["education"]) == 4
    assert len(resume["skills"]) >= 100
    assert len(resume["awards"]) == 2
    assert len(resume["certificates"]) == 2
    assert "awards:" in content
    assert "certificates:" in content
    assert "volunteer:" in content


def test_public_adapter_renders_all_migrated_work_and_skills() -> None:
    copied_resume = ROOT / "apps/web/src/data/react-folio-resume.json"
    content_adapter = ROOT / "apps/web/src/lib/content.ts"
    about_page = ROOT / "apps/web/src/app/about/page.tsx"

    resume = json.loads(copied_resume.read_text(encoding="utf-8"))
    content = content_adapter.read_text(encoding="utf-8")
    about = about_page.read_text(encoding="utf-8")

    assert len(resume["work"]) == 14
    assert len(resume["skills"]) == 100
    assert "work: (resume.work ?? []).map" in content
    assert ".slice(0, 8).map((job)" not in content
    assert "Migrated React-folio skills" in content
    assert ".filter((name, index, names)" not in content
    assert "group.keywords.map((skill, index)" in about

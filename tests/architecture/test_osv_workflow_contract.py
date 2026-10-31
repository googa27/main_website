"""Protect the repository's scanner inputs at the maintained workflow boundary."""

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("job_name", ["osv-pr-scan", "osv-full-scan"])
def test_scan_results_use_artifacts_without_weakening_the_security_gate(job_name):
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())
    job = workflow["jobs"][job_name]
    inputs = job.get("with", {})

    # The old exporter serialized multi-megabyte JSON into GitHub's 1 MB
    # output channel. Neither caller consumes those optional string outputs.
    assert inputs.get("export-results") is False
    assert inputs.get("fail-on-vuln") is True
    assert inputs.get("upload-sarif") is True
    assert "scan-args" not in inputs  # Preserve the upstream recursive root scan.
    assert not job.get("continue-on-error", False)
    assert job["needs"] == "quality-checks"
    event = "pull_request" if job_name == "osv-pr-scan" else "push"
    assert job["if"] == "${{ github.event_name == '" + event + "' }}"
    assert job["permissions"] == {
        "actions": "read",
        "contents": "read",
        "security-events": "write",
    }

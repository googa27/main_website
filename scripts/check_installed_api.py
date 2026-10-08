"""Verify the optional API's installed public fixture without source-tree imports."""

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

DIAGNOSTIC_TAIL_BYTES = 4096

PROBE = """
import asyncio
import hashlib
import json
import sys
import subprocess
from pathlib import Path

import app.main
from app.schemas.cv import CVExportRequest
from app.services.ai_service import ai_service
from app.services.cv import CVService
from app.services.cv.projects import curated_project_page
from app.services.cv.resume import resume_json

assert Path(app.main.__file__).is_relative_to(Path(sys.prefix))
async def verify():
    service = CVService()
    profile = await service.get_current_cv()
    assert profile is not None and profile.personal_info.first_name
    exported = await service.export_cv(CVExportRequest(format="json"))
    payload = json.loads(exported.content)
    assert payload["personal_info"]["first_name"] == profile.personal_info.first_name
    context = json.loads(ai_service.cv_context)["personal_info"]
    assert not ({"phone", "email", "profile_picture_url"} & context.keys())
    resume = await service.get_public_resume()
    public_payload = json.loads(resume_json(resume))
    assert len(public_payload["projects"]) == len(profile.projects)
    projects = curated_project_page(profile)
    assert projects.source == "curated_cv" and not projects.metrics_available
    assert projects.total == len(profile.projects)
    capabilities = json.loads(subprocess.check_output(
        [str(Path(sys.prefix) / "bin/portfolio-cv"), "--capabilities"],
        text=True, timeout=10))
    assert capabilities["jsonresume_schema"] == "1.3.1"
    assert capabilities["network_acquisition"] is False
    cli = Path(sys.prefix) / "bin/portfolio-cv"
    cli_json = subprocess.check_output([str(cli)], text=True, timeout=10)
    assert json.loads(cli_json) == public_payload
    if not capabilities["pdf_dependency_installed"]:
        unavailable = subprocess.run([str(cli), "--format", "pdf", "--output", "missing.pdf"],
            text=True, capture_output=True, timeout=10)
        assert unavailable.returncode == 2
        assert not Path("missing.pdf").exists()
        assert '"error": "PDF renderer unavailable"' in unavailable.stderr
    print(json.dumps({"status": "passed", "application_file": app.main.__file__,
        "projects": len(profile.projects), "contact_fields_omitted": True,
        "jsonresume_schema": "1.3.1", "installed_cli": capabilities,
        "cv_sha256": hashlib.sha256(exported.content.encode()).hexdigest()}))
asyncio.run(verify())
"""


def _captured_tail(output: bytes | str | None) -> dict[str, str | int | bool]:
    """Retain the final error context without printing unbounded diagnostics."""
    raw = output.encode("utf-8") if isinstance(output, str) else output or b""
    return {
        "text": raw[-DIAGNOSTIC_TAIL_BYTES:].decode("utf-8", errors="replace"),
        "captured_bytes": len(raw),
        "truncated": len(raw) > DIAGNOSTIC_TAIL_BYTES,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", type=Path, required=True)
    args = parser.parse_args()
    # Preserve a venv symlink's identity; resolving it selects the base interpreter.
    interpreter = args.python.absolute()
    try:
        with tempfile.TemporaryDirectory(prefix="portfolio-api-wheel-") as cwd:
            result = subprocess.run(
                [str(interpreter), "-I", "-c", PROBE],
                cwd=cwd,
                capture_output=True,
                timeout=30,
                check=True,
            )
        # Match text=True's strict decoding of both successful output streams.
        stdout = result.stdout.decode("utf-8")
        result.stderr.decode("utf-8")
        print(stdout, end="")
    except subprocess.CalledProcessError as exc:
        print(
            json.dumps(
                {
                    "status": "failed",
                    "exit_code": exc.returncode,
                    "stdout": _captured_tail(exc.stdout),
                    "stderr": _captured_tail(exc.stderr),
                }
            )
        )
        return 1
    except subprocess.TimeoutExpired as exc:
        print(
            json.dumps(
                {
                    "status": "failed",
                    "error_type": type(exc).__name__,
                    "timeout_seconds": exc.timeout,
                    "stdout": _captured_tail(exc.stdout),
                    "stderr": _captured_tail(exc.stderr),
                }
            )
        )
        return 1
    except UnicodeDecodeError as exc:
        print(json.dumps({"status": "failed", "error_type": type(exc).__name__}))
        return 1
    except OSError as exc:
        print(
            json.dumps(
                {
                    "status": "failed",
                    "error_type": type(exc).__name__,
                    "errno": exc.errno,
                }
            )
        )
        return 1
    except subprocess.SubprocessError as exc:
        print(json.dumps({"status": "failed", "error_type": type(exc).__name__}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

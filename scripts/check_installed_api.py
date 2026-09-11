"""Verify the optional API's installed public fixture without source-tree imports."""

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

PROBE = """
import asyncio
import hashlib
import json
import sys
from pathlib import Path

import app.main
from app.schemas.cv import CVExportRequest
from app.services.ai_service import ai_service
from app.services.cv import CVService

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
    print(json.dumps({"status": "passed", "application_file": app.main.__file__,
        "projects": len(profile.projects), "contact_fields_omitted": True,
        "cv_sha256": hashlib.sha256(exported.content.encode()).hexdigest()}))
asyncio.run(verify())
"""


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
                text=True,
                timeout=30,
                check=True,
            )
        print(result.stdout, end="")
    except subprocess.CalledProcessError as exc:
        print(json.dumps({"status": "failed", "exit_code": exc.returncode}))
        return 1
    except (OSError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "failed", "error_type": type(exc).__name__}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

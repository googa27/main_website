"""Public CV export CLI: deterministic, packaged input and explicit output writes."""

import argparse
import asyncio
import json
import sys
from importlib.util import find_spec
from pathlib import Path
from tempfile import NamedTemporaryFile

from .pdf import PDFUnavailableError
from .resume import ResumeProjectionError, resume_json
from .service import CVService


def _write_atomic(path: Path, content: bytes) -> None:
    temporary: Path | None = None
    try:
        with NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content)
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


async def _content(format_name: str) -> bytes:
    service = CVService()
    if format_name == "pdf":
        return await service.render_public_pdf()
    return resume_json(await service.get_public_resume()).encode("utf-8")


def main(argv: list[str] | None = None) -> int:
    """Export the current packaged public CV; never acquire provider data."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=["jsonresume", "pdf"], default="jsonresume")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--capabilities", action="store_true")
    args = parser.parse_args(argv)
    if args.capabilities:
        print(
            json.dumps(
                {
                    "source": "curated-public-CVProfile",
                    "jsonresume_schema": "1.3.1",
                    "pdf_dependency_installed": find_spec("reportlab") is not None,
                    "network_acquisition": False,
                }
            )
        )
        return 0
    if args.format == "pdf" and args.output is None:
        parser.error("--output is required for binary PDF export")
    try:
        content = asyncio.run(_content(args.format))
        if args.output is None:
            print(content.decode("utf-8"))
        else:
            _write_atomic(args.output, content)
    except PDFUnavailableError:
        print(
            json.dumps({"status": "failed", "error": "PDF renderer unavailable"}),
            file=sys.stderr,
        )
        return 2
    except (ResumeProjectionError, LookupError, OSError):
        print(
            json.dumps({"status": "failed", "error": "Public CV export failed"}),
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

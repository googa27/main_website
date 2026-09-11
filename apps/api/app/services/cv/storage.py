"""Typed CV snapshots and atomic filesystem replacement."""

import json
import logging
from pathlib import Path
from tempfile import NamedTemporaryFile

from app.schemas.cv import CVProfile

logger = logging.getLogger(__name__)


def load_profile(path: Path) -> CVProfile | None:
    """Load CV profile from storage."""
    try:
        if not path.exists():
            logger.info("No CV profile found in storage")
            return None

        with open(path, encoding="utf-8") as f:
            cv_data = json.load(f)

        cv_profile = CVProfile.model_validate(cv_data)
        logger.info("CV profile loaded from storage")
        return cv_profile

    except Exception as e:
        logger.error(f"Error loading CV from storage: {e!s}")
        return None


def save_profile(cv_profile: CVProfile, directory: Path, path: Path) -> bool:
    """Atomically persist typed JSON, retaining the previous file on failure."""
    temporary_path: Path | None = None
    try:
        content = cv_profile.model_dump_json(indent=2)
        with NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=directory, delete=False
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(content)
        temporary_path.replace(path)
        logger.info("CV profile saved to storage")
        return True
    except Exception as e:
        logger.error(f"Error saving CV to storage: {e!s}")
        return False
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

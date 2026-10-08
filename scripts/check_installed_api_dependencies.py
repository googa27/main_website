"""Audit a normal API environment separately from its first-party wheel checks."""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import tomllib
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = """
import importlib.metadata as metadata
import json, sys
from pathlib import Path
rows = []
for dist in metadata.distributions():
    direct = json.loads(dist.read_text('direct_url.json') or '{}')
    rows.append({'name': dist.metadata['Name'], 'version': dist.version,
                 'location': str(Path(dist.locate_file('')).resolve()),
                 'editable': direct.get('dir_info', {}).get('editable', False)})
print(json.dumps({'isolated': sys.flags.isolated, 'prefix': sys.prefix,
                  'base_prefix': sys.base_prefix, 'distributions': rows}))
"""


def collect_snapshot(interpreter: Path) -> dict:
    """Preserve the venv symlink; discover metadata in a real isolated child."""
    with tempfile.TemporaryDirectory(prefix="portfolio-api-metadata-") as cwd:
        result = subprocess.run(
            [str(interpreter.absolute()), "-I", "-c", SNAPSHOT],
            cwd=cwd,
            capture_output=True,
            timeout=30,
            check=True,
        )
    return json.loads(result.stdout.decode("utf-8"))


def exact_pin(declaration: str) -> tuple[str, str]:
    requirement = Requirement(declaration)
    pins = list(requirement.specifier)
    if (
        requirement.url
        or requirement.marker
        or requirement.extras
        or len(pins) != 1
        or pins[0].operator != "=="
        or "*" in pins[0].version
    ):
        raise ValueError("expected one unconditional exact published pin")
    version = Version(pins[0].version)
    if version.is_prerelease or version.is_devrelease or version.local:
        raise ValueError("expected a stable published version")
    return canonicalize_name(requirement.name, validate=True), str(version)


def published_requirements(
    snapshot: dict, installer_version: str, api_name: str, api_version: str
) -> str:
    prefix = Path(snapshot["prefix"])
    if snapshot["isolated"] != 1 or prefix == Path(snapshot["base_prefix"]):
        raise ValueError("expected an isolated virtual environment")
    expected_api = canonicalize_name(api_name, validate=True)
    installed = {}
    for row in snapshot["distributions"]:
        name = canonicalize_name(row["name"], validate=True)
        if name in installed:
            raise ValueError(f"duplicate installed distribution: {name}")
        if not Path(row["location"]).is_relative_to(prefix) or row["editable"]:
            raise ValueError(f"non-normal installation: {name}")
        # Report installer drift before generic version diagnostics.
        if name == "pip" and row["version"] != installer_version:
            raise ValueError(
                f"installer must be pip=={installer_version}; found {row['version']}"
            )
        _, version = exact_pin(f"{name}=={row['version']}")
        installed[name] = version
    for required in ("pip", expected_api):
        if required not in installed:
            raise ValueError(f"missing installed distribution: {required}")
    if installed[expected_api] != api_version:
        raise ValueError("first-party version does not match the wheel project")
    return "".join(
        f"{name}=={version}\n"
        for name, version in sorted(installed.items())
        if name != expected_api
    )


def check_audit_coverage(report: dict, requirements: str) -> None:
    expected = dict(exact_pin(line) for line in requirements.splitlines())
    actual = {}
    for row in report["dependencies"]:
        name, version = exact_pin(f"{row['name']}=={row['version']}")
        if name in actual or row.get("skip_reason") or row["vulns"]:
            raise ValueError(
                "audit contains a duplicate, skipped package or vulnerability"
            )
        actual[name] = version
    if actual != expected:
        raise ValueError("audit does not cover every installed published pin")


def recorded_command(directory: Path, name: str, argv: list[str]) -> None:
    result = subprocess.run(
        argv, cwd=directory, capture_output=True, timeout=180, check=False
    )
    (directory / f"{name}.stdout").write_bytes(result.stdout)
    (directory / f"{name}.stderr").write_bytes(result.stderr)
    (directory / f"{name}.command.json").write_text(
        json.dumps(
            {"argv": argv, "cwd": str(directory), "exit_code": result.returncode}
        )
        + "\n"
    )
    result.check_returncode()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--audit-python", type=Path, default=Path(sys.executable))
    parser.add_argument("--report-dir", type=Path, required=True)
    args = parser.parse_args()
    phase = "collection"
    try:
        directory = args.report_dir.absolute()
        directory.mkdir(parents=True, exist_ok=False)
        # Bootstrap policy is one pip pin; separate tooling pins live elsewhere.
        installer_name, installer_version = exact_pin(
            (ROOT / "requirements-bootstrap.txt").read_text().strip()
        )
        if installer_name != "pip":
            raise ValueError("bootstrap policy must pin pip")
        project = tomllib.loads((ROOT / "apps/api/pyproject.toml").read_text())[
            "project"
        ]
        snapshot = collect_snapshot(args.python)
        (directory / "installed-metadata.json").write_text(
            json.dumps(snapshot, indent=2) + "\n"
        )
        phase = "profile"
        requirements = published_requirements(
            snapshot, installer_version, project["name"], project["version"]
        )
        (directory / "published-requirements.txt").write_text(requirements)
        phase = "dependency-consistency"
        recorded_command(
            directory,
            "pip-check",
            [str(args.python.absolute()), "-I", "-m", "pip", "check"],
        )
        phase = "published-audit"
        recorded_command(
            directory,
            "pip-audit",
            [
                str(args.audit_python.absolute()),
                "-I",
                "-m",
                "pip_audit",
                "--strict",
                "--no-deps",
                "--disable-pip",
                "--vulnerability-service",
                "pypi",
                "--progress-spinner",
                "off",
                "--format",
                "json",
                "--cache-dir",
                str(directory / "http-cache"),
                "--requirement",
                str(directory / "published-requirements.txt"),
                "--output",
                str(directory / "pip-audit.json"),
            ],
        )
        phase = "audit-coverage"
        check_audit_coverage(
            json.loads((directory / "pip-audit.json").read_text()), requirements
        )
        print(
            json.dumps(
                {
                    "status": "passed",
                    "report_dir": str(directory),
                    "installed_distributions": len(snapshot["distributions"]),
                    "audited_published_distributions": len(requirements.splitlines()),
                    "first_party_not_on_PyPI": {
                        "name": project["name"],
                        "version": project["version"],
                        "acceptance": "separate built-wheel identity and check_installed_api.py required",
                    },
                }
            )
        )
        return 0
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        subprocess.SubprocessError,
    ) as exc:
        result = {
            "status": "failed",
            "phase": phase,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        if isinstance(exc, subprocess.CalledProcessError):
            result["exit_code"] = exc.returncode
        if isinstance(exc, subprocess.TimeoutExpired):
            result["timeout_seconds"] = exc.timeout
        print(json.dumps(result))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

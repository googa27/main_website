"""Installed metadata controls; live PyPI audits belong to artifact acceptance."""

import importlib.util
import json
import sys
import tempfile
import venv
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "installed_dependency_gate", ROOT / "scripts/check_installed_api_dependencies.py"
)
assert SPEC is not None and SPEC.loader is not None
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


def snapshot():
    return {
        "isolated": 1,
        "prefix": "/isolated/env",
        "base_prefix": "/base/python",
        "distributions": [
            {
                "name": name,
                "version": version,
                "location": "/isolated/env/lib",
                "editable": False,
            }
            for name, version in [
                ("pip", "26.2.1"),
                ("portfolio-api", "0.1.0"),
                ("Mako", "1.4.2"),
            ]
        ],
    }


def requirements(value):
    return gate.published_requirements(value, "26.2.1", "portfolio-api", "0.1.0")


def test_every_published_distribution_including_installer_is_pinned():
    assert requirements(snapshot()) == "mako==1.4.2\npip==26.2.1\n"


@pytest.mark.parametrize("version", ["24.0", "26.2.0", "26.2.1rc1", "26.2.1+local"])
def test_old_or_unreviewed_installer_is_refused(version):
    value = snapshot()
    value["distributions"][0]["version"] = version
    with pytest.raises(ValueError, match="installer"):
        requirements(value)


@pytest.mark.parametrize("missing", ["pip", "portfolio-api"])
def test_missing_installer_or_firstparty_is_not_a_complete_profile(missing):
    value = snapshot()
    value["distributions"] = [x for x in value["distributions"] if x["name"] != missing]
    with pytest.raises(ValueError, match="missing"):
        requirements(value)


def test_normalized_duplicates_are_not_silently_overwritten():
    value = snapshot()
    value["distributions"].append(dict(value["distributions"][1], name="Portfolio_API"))
    with pytest.raises(ValueError, match="duplicate"):
        requirements(value)


@pytest.mark.parametrize(
    "field,bad",
    [
        ("name", "bad\n--ignore-vuln ALL"),
        ("version", "1.0; python_version > '3'"),
        ("version", "1.0+local"),
        ("version", "1.0rc1"),
    ],
)
def test_unsafe_or_unpublished_metadata_cannot_become_a_requirement(field, bad):
    value = snapshot()
    value["distributions"][2][field] = bad
    with pytest.raises(ValueError):
        requirements(value)


@pytest.mark.parametrize(
    "field,bad", [("location", "/isolated/env-lookalike/lib"), ("editable", True)]
)
def test_source_or_editable_installation_is_not_normal_acceptance(field, bad):
    value = snapshot()
    value["distributions"][2][field] = bad
    with pytest.raises(ValueError, match="installation"):
        requirements(value)


def test_firstparty_exclusion_is_bound_to_actual_expected_version():
    value = snapshot()
    value["distributions"][1]["version"] = "0.2.0"
    with pytest.raises(ValueError, match="first-party"):
        requirements(value)


@pytest.mark.parametrize(
    "field,bad", [("isolated", 0), ("base_prefix", "/isolated/env")]
)
def test_ambient_interpreter_is_refused(field, bad):
    value = snapshot()
    value[field] = bad
    with pytest.raises(ValueError, match="isolated"):
        requirements(value)


def audit_report():
    return {
        "dependencies": [
            {"name": "Mako", "version": "1.4.2", "vulns": []},
            {"name": "pip", "version": "26.2.1", "vulns": []},
        ],
        "fixes": [],
    }


def test_complete_no_findings_report_matches_every_installed_published_pin():
    gate.check_audit_coverage(audit_report(), requirements(snapshot()))


@pytest.mark.parametrize(
    "mutation",
    ["omission", "extra", "duplicate", "wrong-version", "skipped", "vulnerability"],
)
def test_incomplete_or_vulnerable_audit_never_counts_as_success(mutation):
    report = audit_report()
    rows = report["dependencies"]
    if mutation == "omission":
        rows.pop()
    elif mutation == "extra":
        rows.append({"name": "other", "version": "1.0", "vulns": []})
    elif mutation == "duplicate":
        rows.append(dict(rows[0]))
    elif mutation == "wrong-version":
        rows[0]["version"] = "1.4.1"
    elif mutation == "skipped":
        rows[0]["skip_reason"] = "unpublished"
    else:
        rows[0]["vulns"] = [{"id": "PUBLIC-SYNTHETIC-FINDING"}]
    with pytest.raises(ValueError):
        gate.check_audit_coverage(report, requirements(snapshot()))


def test_actual_isolated_child_reads_only_selected_venv_metadata():
    with tempfile.TemporaryDirectory() as folder:
        target = Path(folder) / "normal-env"
        venv.EnvBuilder(with_pip=False, symlinks=True).create(target)
        site = (
            target
            / "lib"
            / f"python{sys.version_info.major}.{sys.version_info.minor}"
            / "site-packages"
        )
        # Public synthetic installed metadata exercises importlib's real discovery;
        # it is not an API wheel or vulnerability-service acceptance claim.
        for name, version in [
            ("pip", "26.2.1"),
            ("portfolio_api", "0.1.0"),
            ("extra", "2.0"),
        ]:
            dist = site / f"{name}-{version}.dist-info"
            dist.mkdir()
            (dist / "METADATA").write_text(
                f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n"
            )
        python = target / "bin/python"
        assert python.is_symlink()
        actual = gate.collect_snapshot(python)
        assert Path(actual["prefix"]) == target
        assert actual["isolated"] == 1
        assert requirements(actual) == "extra==2.0\npip==26.2.1\n"
        (site / "extra-2.0.dist-info/direct_url.json").write_text(
            json.dumps({"dir_info": {"editable": True}})
        )
        with pytest.raises(ValueError, match="installation"):
            requirements(gate.collect_snapshot(python))

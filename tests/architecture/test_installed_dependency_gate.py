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


def test_timeout_keeps_partial_streams_and_attempt_metadata(tmp_path, monkeypatch):
    import subprocess

    real_run = subprocess.run

    def real_run_with_short_deadline(argv, **kwargs):
        # Only shorten the deadline; execution and timeout handling stay real.
        kwargs["timeout"] = 1
        return real_run(argv, **kwargs)

    monkeypatch.setattr(gate.subprocess, "run", real_run_with_short_deadline)
    argv = [
        sys.executable,
        "-I",
        "-c",
        "import os, sys, time; "
        "print('partial:' + str(os.getpid()), flush=True); "
        "sys.stderr.buffer.write(b'partial-error\\xff'); "
        "sys.stderr.buffer.flush(); time.sleep(30)",
    ]
    with pytest.raises(subprocess.TimeoutExpired) as caught:
        gate.recorded_command(tmp_path, "probe", argv)
    pid = int(caught.value.stdout.decode().strip().split(":")[1])
    if sys.platform == "linux":
        assert not Path("/proc", str(pid)).exists()
    assert (tmp_path / "probe.stdout").read_bytes() == caught.value.stdout
    assert (tmp_path / "probe.stderr").read_bytes() == caught.value.stderr
    record = json.loads((tmp_path / "probe.command.json").read_text())
    assert record["argv"] == argv and record["cwd"] == str(tmp_path)
    assert record["status"] == "timed_out"
    assert record["exit_code"] is None
    assert record["error_type"] == "TimeoutExpired"
    assert record["timeout_seconds"] == 1


def test_launch_failure_keeps_attempt_without_inventing_exit(tmp_path):
    argv = [str(tmp_path / "absent-public-fixture-executable")]
    with pytest.raises(FileNotFoundError):
        gate.recorded_command(tmp_path, "probe", argv)
    record = json.loads((tmp_path / "probe.command.json").read_text())
    assert record["argv"] == argv and record["cwd"] == str(tmp_path)
    assert record["status"] == "execution_error"
    assert record["exit_code"] is None
    assert record["error_type"] == "FileNotFoundError"
    assert record["errno"] == 2
    assert (tmp_path / "probe.stdout").read_bytes() == b""
    assert (tmp_path / "probe.stderr").read_bytes() == b""


def test_nonzero_command_keeps_raw_streams_and_real_exit(tmp_path):
    import subprocess

    argv = [
        sys.executable,
        "-I",
        "-c",
        "import os, sys; os.write(1, b'public-out\\xff'); "
        "os.write(2, b'public-error\\xfe'); sys.exit(7)",
    ]
    with pytest.raises(subprocess.CalledProcessError) as caught:
        gate.recorded_command(tmp_path, "probe", argv)
    assert caught.value.returncode == 7
    assert (tmp_path / "probe.stdout").read_bytes() == b"public-out\xff"
    assert (tmp_path / "probe.stderr").read_bytes() == b"public-error\xfe"
    record = json.loads((tmp_path / "probe.command.json").read_text())
    assert record["argv"] == argv and record["cwd"] == str(tmp_path)
    assert record["status"] == "completed" and record["exit_code"] == 7

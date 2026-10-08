"""Exercise the installed gate with real, finite public child processes."""

import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
import venv
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


class InstalledAPIGateTests(unittest.TestCase):
    def setUp(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "installed_api_gate", ROOT / "scripts/check_installed_api.py"
        )
        assert spec is not None and spec.loader is not None
        self.gate = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.gate)

    def invoke(self, probe: str, python: Path | None = None) -> tuple[int, str]:
        output = io.StringIO()
        argv = ["check_installed_api.py", "--python", str(python or sys.executable)]
        # Only the public-synthetic probe and CLI arguments change. The actual
        # subprocess, isolated interpreter, temporary cwd and timeout execute.
        with (
            patch.object(self.gate, "PROBE", probe),
            patch.object(sys, "argv", argv),
            contextlib.redirect_stdout(output),
        ):
            code = self.gate.main()
        return code, output.getvalue()

    def test_nonzero_exit_retains_both_streams_and_real_exit(self) -> None:
        code, output = self.invoke(
            "import sys; print('public stdout evidence', flush=True); "
            "print('public stderr cause', file=sys.stderr, flush=True); sys.exit(7)"
        )
        self.assertEqual(code, 1)
        result = json.loads(output)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["exit_code"], 7)
        self.assertEqual(result["stdout"]["text"], "public stdout evidence\n")
        self.assertEqual(result["stderr"]["text"], "public stderr cause\n")
        self.assertFalse(result["stderr"]["truncated"])

    def test_diagnostics_retain_bounded_tail_and_original_byte_counts(self) -> None:
        code, output = self.invoke(
            "import sys; "
            "sys.stdout.buffer.write(b'A'*12000+b' stdout tail'); "
            "sys.stderr.buffer.write(b'B'*13000+b' stderr cause'); sys.exit(9)"
        )
        self.assertEqual(code, 1)
        result = json.loads(output)
        self.assertEqual(result["exit_code"], 9)
        for stream, count, suffix in [
            ("stdout", 12012, " stdout tail"),
            ("stderr", 13013, " stderr cause"),
        ]:
            self.assertEqual(result[stream]["captured_bytes"], count)
            self.assertEqual(len(result[stream]["text"]), 4096)
            self.assertTrue(result[stream]["text"].endswith(suffix))
            self.assertTrue(result[stream]["truncated"])

    def test_undecodable_child_output_preserves_primary_nonzero_exit(self) -> None:
        code, output = self.invoke(
            "import sys; sys.stdout.buffer.write(b'public stdout \\xff'); "
            "sys.stderr.buffer.write(b'public error \\xfe'); sys.exit(7)"
        )
        self.assertEqual(code, 1)
        result = json.loads(output)
        self.assertEqual(result["exit_code"], 7)
        self.assertIn("public stdout \ufffd", result["stdout"]["text"])
        self.assertIn("public error \ufffd", result["stderr"]["text"])
        self.assertEqual(result["stdout"]["captured_bytes"], 15)

    def test_actual_timeout_retains_output_and_timeout_identity(self) -> None:
        code, output = self.invoke(
            "import threading,sys; print('before timeout', flush=True); "
            "print('timeout stderr', file=sys.stderr, flush=True); "
            "threading.Event().wait(31)"
        )
        self.assertEqual(code, 1)
        result = json.loads(output)
        self.assertEqual(result["error_type"], "TimeoutExpired")
        self.assertEqual(result["timeout_seconds"], 30)
        self.assertIn("before timeout", result["stdout"]["text"])
        self.assertIn("timeout stderr", result["stderr"]["text"])
        self.assertNotIn("exit_code", result)

    def test_missing_interpreter_preserves_os_error_without_env_dump(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            code, output = self.invoke("pass", Path(folder) / "missing-python")
        self.assertEqual(code, 1)
        result = json.loads(output)
        self.assertEqual(result["error_type"], "FileNotFoundError")
        self.assertEqual(result["errno"], 2)
        self.assertNotIn("environment", result)
        self.assertNotIn("exit_code", result)

    def test_success_keeps_output_and_real_venv_symlink_identity(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "normal-env"
            venv.EnvBuilder(with_pip=False, symlinks=True).create(target)
            python = target / "bin/python"
            self.assertTrue(python.is_symlink())
            code, output = self.invoke(
                "import json,sys; from pathlib import Path; "
                "print(json.dumps({'status':'passed', 'prefix':sys.prefix, "
                "'isolated':sys.flags.isolated, 'cwd':str(Path.cwd())}))",
                python,
            )
            self.assertEqual(code, 0)
            result = json.loads(output)
            self.assertEqual(result["status"], "passed")
            self.assertEqual(Path(result["prefix"]), target)
            self.assertEqual(result["isolated"], 1)
            self.assertNotEqual(Path(result["cwd"]), ROOT)
            self.assertFalse(Path(result["cwd"]).exists())

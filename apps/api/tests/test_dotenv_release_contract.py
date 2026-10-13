"""Executable release laws for the maintained dotenv parser and CLI.

Runs in pytest and directly under an isolated normal wheel interpreter.
All values and files are synthetic; no host .env file is consulted.
"""

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from dotenv import dotenv_values


class DotenvReleaseContract(unittest.TestCase):
    def cli(self, directory, *arguments, extra_env=None):
        environment = {
            key: os.environ[key]
            for key in ("PATH", "SYSTEMROOT", "TMPDIR", "LANG")
            if key in os.environ
        }
        environment.update(extra_env or {})
        return subprocess.run(
            [
                sys.executable,
                "-I",
                "-B",
                "-m",
                "dotenv",
                "-f",
                str(Path(directory) / ".env"),
                *arguments,
            ],
            cwd=directory,
            env=environment,
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )

    def test_empty_unquoted_value_with_comment_stays_empty(self):
        values = dotenv_values(
            stream=io.StringIO(
                "EMPTY= # synthetic explanation longer than thirty two characters\n"
            )
        )
        self.assertEqual(values["EMPTY"], "")

    def test_cli_get_empty_value_is_success(self):
        with tempfile.TemporaryDirectory(prefix="dotenv-get-") as directory:
            (Path(directory) / ".env").write_text("EMPTY=\n", encoding="utf-8")
            result = self.cli(directory, "get", "EMPTY")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), "")

    def test_cli_no_override_interpolation_uses_existing_environment(self):
        with tempfile.TemporaryDirectory(prefix="dotenv-run-") as directory:
            (Path(directory) / ".env").write_text(
                "BASE=synthetic-file\nCHILD=${BASE}\n", encoding="utf-8"
            )
            for flag, expected in [
                ("--no-override", "synthetic-environment"),
                ("--override", "synthetic-file"),
            ]:
                with self.subTest(flag=flag):
                    result = self.cli(
                        directory,
                        "run",
                        flag,
                        sys.executable,
                        "-I",
                        "-B",
                        "-c",
                        "import json,os;print(json.dumps(os.environ['CHILD']))",
                        extra_env={"BASE": "synthetic-environment"},
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(json.loads(result.stdout), expected)

    def test_missing_bare_and_quoted_values_remain_distinct(self):
        values = dotenv_values(
            stream=io.StringIO("BARE\nQUOTED='synthetic#literal'\nEMPTY=\n")
        )
        self.assertIsNone(values["BARE"])
        self.assertNotIn("MISSING", values)
        self.assertEqual(values["QUOTED"], "synthetic#literal")
        self.assertEqual(values["EMPTY"], "")
        with tempfile.TemporaryDirectory(prefix="dotenv-missing-") as directory:
            (Path(directory) / ".env").write_text("EMPTY=\n", encoding="utf-8")
            self.assertEqual(self.cli(directory, "get", "MISSING").returncode, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)

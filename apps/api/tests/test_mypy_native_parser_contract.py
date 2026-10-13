"""The selected development checker must enforce explicit control-flow annotations."""

import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from mypy.api import run

CONFIG = Path(__file__).resolve().parents[1] / "mypy.ini"
PRELUDE = "def consume_str(value: str) -> None:\n    pass\n"


class NativeParserContract(unittest.TestCase):
    def check_source(self, source: str) -> tuple[str, str, int]:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "parser_contract.py"
            path.write_text(source, encoding="utf-8")
            return run(
                [
                    "--config-file",
                    str(CONFIG),
                    "--strict",
                    "--no-incremental",
                    "--cache-dir",
                    os.devnull,
                    "--no-site-packages",
                    "--python-version",
                    "3.12",
                    str(path),
                ]
            )

    def test_for_comment_does_not_supply_the_native_variable_type(self) -> None:
        source = PRELUDE + (
            'for item in ["text"]:  # type: int\n'
            "    consume_str(item)\n"
        )
        stdout, stderr, status = self.check_source(source)
        self.assertEqual((stderr, status), ("", 0), stdout)

    def test_with_comment_does_not_supply_the_native_variable_type(self) -> None:
        source = (
            "from contextlib import nullcontext\n"
            + PRELUDE
            + 'with nullcontext("text") as item:  # type: int\n'
            "    consume_str(item)\n"
        )
        stdout, stderr, status = self.check_source(source)
        self.assertEqual((stderr, status), ("", 0), stdout)

    def test_incompatible_explicit_annotations_are_still_refused(self) -> None:
        sources = [
            PRELUDE + 'item: int\nfor item in ["text"]:\n    consume_str(item)\n',
            "from contextlib import nullcontext\n"
            + PRELUDE
            + 'item: int\nwith nullcontext("text") as item:\n    consume_str(item)\n',
        ]
        for source in sources:
            with self.subTest(source=source):
                stdout, stderr, status = self.check_source(source)
                self.assertEqual((stderr, status), ("", 1), stdout)
                self.assertIn("[assignment]", stdout)

    def test_compatible_explicit_annotations_remain_accepted(self) -> None:
        sources = [
            PRELUDE + 'item: str\nfor item in ["text"]:\n    consume_str(item)\n',
            "from contextlib import nullcontext\n"
            + PRELUDE
            + 'item: str\nwith nullcontext("text") as item:\n    consume_str(item)\n',
        ]
        for source in sources:
            with self.subTest(source=source):
                stdout, stderr, status = self.check_source(source)
                self.assertEqual((stderr, status), ("", 0), stdout)


if __name__ == "__main__":
    unittest.main()

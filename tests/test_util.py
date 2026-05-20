from __future__ import annotations

import sys
import unittest
from pathlib import Path

from cursor_fleet.util import run_cmd


class UtilTests(unittest.TestCase):
    def test_run_cmd_replaces_invalid_utf8_output(self) -> None:
        result = run_cmd(
            [sys.executable, "-c", "import sys; sys.stdout.buffer.write(b'\\x93')"],
            Path("."),
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "\ufffd")


if __name__ == "__main__":
    unittest.main()

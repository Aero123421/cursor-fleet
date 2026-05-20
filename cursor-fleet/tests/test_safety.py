from __future__ import annotations

import unittest

from cursor_fleet.safety import denied_files, out_of_scope_files


class SafetyTests(unittest.TestCase):
    def test_denied_files(self) -> None:
        self.assertEqual(denied_files([".env", "src/app.py"], [".env", "**/*.pem"]), [".env"])
        self.assertEqual(denied_files(["keys/prod.pem"], ["**/*.pem"]), ["keys/prod.pem"])

    def test_out_of_scope_files(self) -> None:
        self.assertEqual(out_of_scope_files(["apps/web/a.ts", "apps/api/b.ts"], ["apps/web"]), ["apps/api/b.ts"])
        self.assertEqual(out_of_scope_files(["anything"], ["."]), [])


if __name__ == "__main__":
    unittest.main()

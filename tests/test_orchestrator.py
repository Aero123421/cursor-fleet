from __future__ import annotations

import unittest

from cursor_fleet.orchestrator import new_run_id


class OrchestratorTests(unittest.TestCase):
    def test_new_run_id_has_subsecond_precision(self) -> None:
        run_id = new_run_id()
        self.assertTrue(run_id.endswith("Z"))
        self.assertEqual(len(run_id), len("20260520T120747621996Z"))


if __name__ == "__main__":
    unittest.main()

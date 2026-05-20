from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cursor_fleet.planner import build_plan, route_mode


class PlannerTests(unittest.TestCase):
    def test_route_mode_keywords(self) -> None:
        self.assertEqual(route_mode("fix CI failure", "auto"), "fix-ci")
        self.assertEqual(route_mode("migrate old API", "auto"), "migrate")
        self.assertEqual(route_mode("add tests", "auto"), "test")
        self.assertEqual(route_mode("update docs", "auto"), "docs")
        self.assertEqual(route_mode("review for security", "auto"), "review")
        self.assertEqual(route_mode("why does checkout fail", "auto"), "investigate")

    def test_build_verify_plan(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            plan = build_plan(task="verify", requested_mode="verify", project=Path(d), max_workers=4, verify_commands=["echo ok"])
            self.assertEqual(plan.mode, "verify")
            self.assertFalse(plan.write)
            self.assertEqual(plan.verify_commands, ["echo ok"])


if __name__ == "__main__":
    unittest.main()

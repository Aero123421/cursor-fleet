from __future__ import annotations

import unittest
from pathlib import Path


class TemplateTests(unittest.TestCase):
    def test_codex_agent_template_is_generic_task_worker(self) -> None:
        root = Path(__file__).resolve().parents[1]
        template = (root / "templates" / "codex" / "cursor-fleet.toml").read_text(encoding="utf-8")
        self.assertIn('name = "task-worker"', template)
        self.assertIn("delegate --task-file", template)
        self.assertNotIn("fast-implementer", template)


if __name__ == "__main__":
    unittest.main()

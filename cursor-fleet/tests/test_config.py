from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cursor_fleet.config import AppConfig, load_config, write_default_config
from cursor_fleet.models import WorkerSpec
from cursor_fleet.runner import CursorRunner


class ConfigTests(unittest.TestCase):
    def test_default_config_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            path = root / ".cursor-fleet" / "config.toml"
            self.assertTrue(write_default_config(path))
            cfg = load_config(root)
            self.assertEqual(cfg.cursor.bin, "agent")
            self.assertEqual(cfg.cursor.model, "auto")
            self.assertGreaterEqual(cfg.fleet.max_workers, 1)

    def test_default_command_uses_auto_model(self) -> None:
        runner = CursorRunner(AppConfig())
        runner.resolve_binary = lambda: "agent"  # type: ignore[method-assign]
        cmd = runner.build_command(Path("."), WorkerSpec(id="w", title="Worker", prompt="Do it"), "prompt")
        model_index = cmd.index("--model")
        self.assertEqual(cmd[model_index + 1], "auto")

    def test_read_only_command_uses_ask_mode(self) -> None:
        runner = CursorRunner(AppConfig())
        runner.resolve_binary = lambda: "agent"  # type: ignore[method-assign]
        cmd = runner.build_command(
            Path("."),
            WorkerSpec(id="w", title="Worker", prompt="Do it", cursor_mode="ask", write=False),
            "prompt",
        )
        self.assertIn("--mode", cmd)
        self.assertEqual(cmd[cmd.index("--mode") + 1], "ask")


if __name__ == "__main__":
    unittest.main()

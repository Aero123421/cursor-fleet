from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cursor_fleet.config import load_config, write_default_config


class ConfigTests(unittest.TestCase):
    def test_default_config_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            path = root / ".cursor-fleet" / "config.toml"
            self.assertTrue(write_default_config(path))
            cfg = load_config(root)
            self.assertEqual(cfg.cursor.bin, "agent")
            self.assertEqual(cfg.cursor.model, "composer-2.5")
            self.assertGreaterEqual(cfg.fleet.max_workers, 1)


if __name__ == "__main__":
    unittest.main()

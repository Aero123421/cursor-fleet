from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cursor_fleet.config import AppConfig
from cursor_fleet.direct import run_direct
from cursor_fleet.util import run_cmd


def _git(cwd: Path, *args: str) -> None:
    result = run_cmd(["git", *args], cwd)
    if result.returncode != 0:
        raise AssertionError(result.stderr or result.stdout)


class DirectTests(unittest.TestCase):
    def test_direct_dry_run_reports_planned_worker(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            _git(repo, "init")
            _git(repo, "config", "user.email", "test@example.invalid")
            _git(repo, "config", "user.name", "Test")
            (repo / "README.md").write_text("# test\n", encoding="utf-8")
            _git(repo, "add", "README.md")
            _git(repo, "commit", "-m", "init")

            report = run_direct(
                project=repo,
                task="Implement something",
                config=AppConfig(),
                run_id="test-run",
                run_dir=repo / ".cursor-fleet" / "runs" / "test-run",
                dry_run=True,
            )

            self.assertEqual(report.status, "dry-run")
            self.assertEqual(report.mode, "delegate")
            self.assertEqual(report.workers[0].status, "planned")

    def test_direct_dry_run_does_not_refuse_dirty_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            _git(repo, "init")
            _git(repo, "config", "user.email", "test@example.invalid")
            _git(repo, "config", "user.name", "Test")
            (repo / "README.md").write_text("# test\n", encoding="utf-8")
            _git(repo, "add", "README.md")
            _git(repo, "commit", "-m", "init")
            (repo / "README.md").write_text("# dirty\n", encoding="utf-8")

            report = run_direct(
                project=repo,
                task="Implement something",
                config=AppConfig(),
                run_id="test-run",
                run_dir=repo / ".cursor-fleet" / "runs" / "test-run",
                dry_run=True,
            )

            self.assertEqual(report.status, "dry-run")
            self.assertEqual(report.errors, [])

    def test_direct_write_refuses_dirty_workspace_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            _git(repo, "init")
            _git(repo, "config", "user.email", "test@example.invalid")
            _git(repo, "config", "user.name", "Test")
            (repo / "README.md").write_text("# test\n", encoding="utf-8")
            _git(repo, "add", "README.md")
            _git(repo, "commit", "-m", "init")
            (repo / "README.md").write_text("# dirty\n", encoding="utf-8")

            report = run_direct(
                project=repo,
                task="Implement something",
                config=AppConfig(),
                run_id="test-run",
                run_dir=repo / ".cursor-fleet" / "runs" / "test-run",
            )

            self.assertEqual(report.status, "failed")
            self.assertIn("uncommitted changes", report.errors[0])


if __name__ == "__main__":
    unittest.main()

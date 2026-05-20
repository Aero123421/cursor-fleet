#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

EXCLUDE_DIRS = {
    ".git",
    ".cursor-fleet",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "build",
    "dist",
}
EXCLUDE_SUFFIXES = {".pyc", ".pyo"}


def copytree_filtered(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    def ignore(path: str, names: list[str]) -> set[str]:
        ignored: set[str] = set()
        for name in names:
            p = Path(path) / name
            if name in EXCLUDE_DIRS:
                ignored.add(name)
            elif p.suffix in EXCLUDE_SUFFIXES:
                ignored.add(name)
        return ignored
    shutil.copytree(src, dst, ignore=ignore)


def copy_file(src: Path, dst: Path, *, force: bool) -> bool:
    if dst.exists() and not force:
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    try:
        dst.chmod(src.stat().st_mode)
    except OSError:
        pass
    return True


def append_gitignore(target: Path) -> None:
    gitignore = target / ".gitignore"
    lines = gitignore.read_text(encoding="utf-8").splitlines() if gitignore.exists() else []
    additions = [".cursor-fleet/runs/", ".cursor-fleet/worktrees/", ".cursor-fleet/tasks/", ".cursor-fleet/tmp/"]
    changed = False
    for item in additions:
        if item not in lines:
            if not changed:
                lines.append("")
                lines.append("# cursor-fleet runtime data")
            lines.append(item)
            changed = True
    if changed:
        gitignore.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Install cursor-fleet into a target project as a self-contained Codex subagent.")
    parser.add_argument("--target", default=".", help="Target project repository")
    parser.add_argument("--force", action="store_true", help="Overwrite existing agent/config/launcher files")
    args = parser.parse_args()

    source = Path(__file__).resolve().parents[1]
    target = Path(args.target).resolve()
    target.mkdir(parents=True, exist_ok=True)

    vendor = target / ".cursor-fleet" / "vendor" / "cursor-fleet"
    config_dst = target / ".cursor-fleet" / "config.toml"
    agent_dst = target / ".codex" / "agents" / "cursor-fleet.toml"
    launcher_dst = target / ".codex" / "tools" / "cursor_fleet.py"

    copytree_filtered(source, vendor)
    copied = [str(vendor)]

    if copy_file(source / "templates" / "config" / "cursor-fleet.toml", config_dst, force=args.force):
        copied.append(str(config_dst))
    if copy_file(source / "templates" / "codex" / "cursor-fleet.toml", agent_dst, force=args.force):
        copied.append(str(agent_dst))
    if copy_file(source / "templates" / "tools" / "cursor_fleet.py", launcher_dst, force=args.force):
        copied.append(str(launcher_dst))

    (target / ".cursor-fleet" / "tasks").mkdir(parents=True, exist_ok=True)
    append_gitignore(target)

    print("cursor-fleet installed into", target)
    print("installed/copied:")
    for item in copied:
        print("  -", item)
    print("\nNext:")
    print("  python3 .codex/tools/cursor_fleet.py doctor")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

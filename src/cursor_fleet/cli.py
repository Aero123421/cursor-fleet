from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from . import __version__
from .config import apply_env_overrides, load_config, write_default_config
from .git import GitError, repo_root, status_porcelain
from .orchestrator import run_plan
from .planner import ALL_MODES, build_plan, load_plan, save_plan
from .report import print_report
from .runner import CursorRunner
from .util import write_text

PACKAGE_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_CODEX_AGENT_TOML = 'name = "cursor-fleet"\ndescription = "Delegates large tasks to Cursor CLI workers, manages worktrees, integrates changes, verifies results, and returns one final report."\nsandbox_mode = "workspace-write"\nmodel_reasoning_effort = "medium"\nnickname_candidates = ["Fleet", "Foreman", "Harbor", "Relay", "Yard"]\n\ndeveloper_instructions = """\nYou are cursor-fleet, a Codex subagent that orchestrates Cursor CLI workers through the local cursor-fleet runner.\n\nWrite the task to .cursor-fleet/tasks/, run python3 .codex/tools/cursor_fleet.py run with the appropriate mode, and return only the final summary, changed files, verification results, final patch status, and remaining risks.\n\nAvailable modes: auto, investigate, review, implement, migrate, test, docs, verify, fix-ci.\n\nSafety rules:\n- Never pass secrets, .env contents, private keys, tokens, or credentials to Cursor.\n- Do not expose individual worker worktree paths unless debugging a failure.\n- Prefer read-only modes for investigation/review and worktrees for write-heavy tasks.\n- Do not commit or push unless explicitly asked.\n"""\n'


def _template(path: str) -> Path:
    # Works from editable/source installs. Project install uses scripts/install_project.py.
    return PACKAGE_ROOT / path


def _copy_template(src: Path, dst: Path, force: bool) -> bool:
    if dst.exists() and not force:
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    return True


def _append_gitignore(project: Path) -> None:
    gitignore = project / ".gitignore"
    lines = []
    if gitignore.exists():
        lines = gitignore.read_text(encoding="utf-8").splitlines()
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


def cmd_init(args: argparse.Namespace) -> int:
    project = Path(args.project).resolve()
    project.mkdir(parents=True, exist_ok=True)
    try:
        project = repo_root(project)
    except GitError:
        if not args.allow_non_git:
            print("error: target is not a git repository. Pass --allow-non-git to scaffold anyway.", file=sys.stderr)
            return 2
    created: list[str] = []
    skipped: list[str] = []

    agent_dst = project / ".codex" / "agents" / "cursor-fleet.toml"
    agent_src = _template("templates/codex/cursor-fleet.toml")
    if agent_src.exists():
        if _copy_template(agent_src, agent_dst, args.force):
            created.append(str(agent_dst))
        else:
            skipped.append(str(agent_dst))
    elif not agent_dst.exists() or args.force:
        write_text(agent_dst, DEFAULT_CODEX_AGENT_TOML)
        created.append(str(agent_dst))
    else:
        skipped.append(str(agent_dst))

    config_dst = project / ".cursor-fleet" / "config.toml"
    if write_default_config(config_dst, force=args.force):
        created.append(str(config_dst))
    else:
        skipped.append(str(config_dst))

    tasks_dir = project / ".cursor-fleet" / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    readme = project / ".cursor-fleet" / "README.md"
    if not readme.exists() or args.force:
        write_text(readme, "# cursor-fleet runtime directory\n\nPut task files and temporary CI logs here. Runtime runs and worktrees are gitignored.\n")
        created.append(str(readme))

    _append_gitignore(project)

    print("cursor-fleet init complete")
    if created:
        print("created:")
        for item in created:
            print(f"  - {item}")
    if skipped:
        print("skipped existing files:")
        for item in skipped:
            print(f"  - {item}")
    print("\nNext: cursor-fleet doctor --project", project)
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    project = Path(args.project).resolve()
    try:
        root = repo_root(project)
        print(f"ok: git repository: {root}")
        status = status_porcelain(root)
        if status.strip():
            print("warn: workspace has uncommitted changes")
        else:
            print("ok: workspace is clean")
    except Exception as exc:  # noqa: BLE001
        print(f"error: git check failed: {exc}")
        return 2

    config = load_config(root, args.config)
    apply_env_overrides(config)
    if args.model:
        config.cursor.model = args.model
    if args.cursor_bin:
        config.cursor.bin = args.cursor_bin
    print(f"ok: cursor model configured: {config.cursor.model}")
    for line in CursorRunner(config).doctor():
        print(line)
    return 0


def _read_task(args: argparse.Namespace) -> str:
    parts: list[str] = []
    if args.task:
        parts.append(args.task)
    if args.task_file:
        parts.append(Path(args.task_file).read_text(encoding="utf-8"))
    if not parts and not args.plan:
        raise SystemExit("error: provide --task, --task-file, or --plan")
    return "\n\n".join(parts).strip()


def _load_config_with_overrides(project: Path, args: argparse.Namespace):
    config = load_config(project, args.config)
    apply_env_overrides(config)
    if args.model:
        config.cursor.model = args.model
    if args.cursor_bin:
        config.cursor.bin = args.cursor_bin
    if args.max_workers:
        config.fleet.max_workers = args.max_workers
    if args.verify_cmd:
        config.verification.commands = list(args.verify_cmd)
    return config


def cmd_plan(args: argparse.Namespace) -> int:
    project = repo_root(Path(args.project).resolve())
    config = _load_config_with_overrides(project, args)
    task = _read_task(args)
    plan = build_plan(
        task=task,
        requested_mode=args.mode,
        project=project,
        max_workers=config.fleet.max_workers,
        verify_commands=config.verification.commands,
        ci_log_path=Path(args.ci_log).resolve() if args.ci_log else None,
    )
    if args.output:
        save_plan(Path(args.output), plan)
        print(f"wrote plan: {args.output}")
    else:
        import json
        print(json.dumps(plan.to_dict(), indent=2, ensure_ascii=False))
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    project = repo_root(Path(args.project).resolve())
    config = _load_config_with_overrides(project, args)
    task = _read_task(args) if not args.plan else ""
    if args.plan:
        plan = load_plan(Path(args.plan))
        if task:
            plan.task = task
        if args.verify_cmd:
            plan.verify_commands = list(args.verify_cmd)
    else:
        plan = build_plan(
            task=task,
            requested_mode=args.mode,
            project=project,
            max_workers=config.fleet.max_workers,
            verify_commands=config.verification.commands,
            ci_log_path=Path(args.ci_log).resolve() if args.ci_log else None,
        )
    apply_flag = None if not args.no_apply_final_patch else False
    report = run_plan(
        project=project,
        plan=plan,
        config=config,
        dry_run=args.dry_run,
        apply_final_patch_flag=apply_flag,
        apply_on_verify_failure=args.apply_on_verify_failure,
        keep_runs=args.keep_runs,
    )
    print_report(report, as_json=args.json)
    return 0 if report.status in {"ok", "dry-run"} else 1


def cmd_clean(args: argparse.Namespace) -> int:
    project = repo_root(Path(args.project).resolve())
    run_root = project / ".cursor-fleet" / "runs"
    wt_root = project / ".cursor-fleet" / "worktrees"
    removed = 0
    for root in (run_root, wt_root):
        if root.exists():
            if args.dry_run:
                print(f"would remove {root}")
            else:
                shutil.rmtree(root)
                print(f"removed {root}")
            removed += 1
    if removed == 0:
        print("nothing to clean")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cursor-fleet", description="Orchestrate Cursor CLI workers from a Codex subagent.")
    parser.add_argument("--version", action="version", version=f"cursor-fleet {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="Install project-scoped Codex agent template and config")
    p.add_argument("--project", default=".")
    p.add_argument("--force", action="store_true")
    p.add_argument("--allow-non-git", action="store_true")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("doctor", help="Check git, config, Cursor CLI binary, and auth basics")
    p.add_argument("--project", default=".")
    p.add_argument("--config")
    p.add_argument("--model")
    p.add_argument("--cursor-bin")
    p.set_defaults(func=cmd_doctor)

    def add_common_run_args(p: argparse.ArgumentParser) -> None:
        p.add_argument("--project", default=".")
        p.add_argument("--config")
        p.add_argument("--mode", default="auto", choices=ALL_MODES)
        p.add_argument("--task")
        p.add_argument("--task-file")
        p.add_argument("--ci-log")
        p.add_argument("--model")
        p.add_argument("--cursor-bin")
        p.add_argument("--max-workers", type=int)
        p.add_argument("--verify-cmd", action="append", default=[])

    p = sub.add_parser("plan", help="Create a task plan without running Cursor workers")
    add_common_run_args(p)
    p.add_argument("--output", "-o")
    p.set_defaults(func=cmd_plan)

    p = sub.add_parser("run", help="Run a cursor-fleet plan")
    add_common_run_args(p)
    p.add_argument("--plan")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--no-apply-final-patch", action="store_true")
    p.add_argument("--apply-on-verify-failure", action="store_true")
    p.add_argument("--keep-runs", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("clean", help="Remove local cursor-fleet runtime directories")
    p.add_argument("--project", default=".")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_clean)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

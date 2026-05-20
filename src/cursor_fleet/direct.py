from __future__ import annotations

from pathlib import Path

from .config import AppConfig
from .git import changed_files, current_head, has_uncommitted_changes, repo_root, require_git
from .models import FleetReport, TaskPlan, WorkerResult, WorkerSpec
from .report import write_report
from .runner import CursorRunner
from .safety import denied_files
from .util import write_json
from .verify import run_verification, verification_ok


def run_direct(
    *,
    project: Path,
    task: str,
    config: AppConfig,
    run_id: str,
    run_dir: Path,
    read_only: bool = False,
    dry_run: bool = False,
    allow_dirty: bool = False,
) -> FleetReport:
    require_git()
    project = repo_root(project)
    run_dir.mkdir(parents=True, exist_ok=True)
    base_sha = current_head(project)
    warnings: list[str] = []
    errors: list[str] = []
    preexisting_changes = changed_files(project)

    if preexisting_changes and not read_only and not dry_run:
        msg = "Original workspace has uncommitted changes."
        if config.safety.require_clean_tree or (config.safety.protect_user_changes and not allow_dirty):
            errors.append(msg + " Commit/stash them first, or pass --allow-dirty.")
        else:
            warnings.append(msg + " Direct mode may mix new edits with existing changes.")

    spec = WorkerSpec(
        id="delegate",
        title="Task execution" if not read_only else "Read-only investigation",
        prompt=(
            "Complete the task directly in this workspace. Keep the change small, "
            "inspect your diff before finishing, and run targeted verification when practical."
            if not read_only
            else "Investigate the task directly in this workspace. Do not edit files."
        ),
        paths=["."],
        cursor_mode="ask" if read_only else "agent",
        write=not read_only,
    )
    plan = TaskPlan(
        mode="delegate-readonly" if read_only else "delegate",
        task=task,
        summary=(
            "Single in-place read-only delegation."
            if read_only
            else "Single in-place implementation delegation."
        ),
        workers=[spec],
        verify_commands=config.verification.commands,
        write=not read_only,
        apply_final_patch=False,
        warnings=warnings,
        metadata={"base_sha": base_sha, "preexisting_changes": preexisting_changes},
    )
    write_json(
        run_dir / "manifest.json",
        {"base_sha": base_sha, "plan": plan.to_dict(), "config_path": str(config.path) if config.path else None},
    )

    report = FleetReport(
        run_id=run_id,
        mode=plan.mode,
        task=task,
        status="dry-run" if dry_run else "running",
        project=str(project),
        run_dir=str(run_dir),
        summary=plan.summary,
        warnings=warnings,
        errors=errors,
    )

    if dry_run or errors:
        report.workers = [
            WorkerResult(
                id=spec.id,
                title=spec.title,
                status="planned" if dry_run else "skipped",
                workspace=str(project),
                changed_files=[],
            )
        ]
        report.status = "dry-run" if dry_run else "failed"
        write_report(report, run_dir)
        return report

    result = CursorRunner(config).run_worker(
        spec=spec,
        task=task,
        workspace=project,
        worker_dir=run_dir / "workers" / spec.id,
    )
    if not read_only:
        result.changed_files = changed_files(project)
        result.denied_files = denied_files(result.changed_files, config.safety.deny_paths)
        if result.denied_files:
            result.status = "failed"
            result.error = "Denied-path changes detected in direct mode."
    report.workers = [result]
    report.changed_files = result.changed_files

    if result.status == "failed":
        report.errors.append(f"Worker {result.id} failed: {result.error}")

    if not read_only and config.verification.commands and not report.errors:
        report.verification = run_verification(config.verification.commands, project, run_dir / "verification")
        if not verification_ok(report.verification):
            report.errors.append("Verification failed.")

    report.status = "failed" if report.errors else "ok"
    write_report(report, run_dir)
    return report

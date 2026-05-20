from __future__ import annotations

import concurrent.futures
import datetime as dt
import shutil
from pathlib import Path

from .config import AppConfig
from .git import (
    GitError,
    apply_patch,
    branch_delete,
    changed_files,
    commit_all,
    conflicted_files,
    current_head,
    diff_binary,
    diff_name_only,
    git,
    has_uncommitted_changes,
    merge_branch,
    repo_root,
    require_git,
    worktree_add,
    worktree_remove,
)
from .models import FleetReport, TaskPlan, WorkerResult, WorkerSpec
from .prompts import conflict_resolver_prompt
from .report import write_report
from .runner import CursorRunner
from .safety import denied_files, out_of_scope_files
from .util import safe_id, write_json, write_text
from .verify import run_verification, verification_ok


def new_run_id() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _resolve_run_dir(project: Path, config: AppConfig, run_id: str) -> Path:
    run_root = Path(config.fleet.run_dir)
    if not run_root.is_absolute():
        run_root = project / run_root
    return run_root / run_id


def _worker_branch(run_id: str, worker_id: str) -> str:
    return f"cursor-fleet/{run_id}/{safe_id(worker_id)}"


def _write_manifest(run_dir: Path, plan: TaskPlan, config: AppConfig, base_sha: str | None) -> None:
    write_json(run_dir / "manifest.json", {"base_sha": base_sha, "plan": plan.to_dict(), "config_path": str(config.path) if config.path else None})


def _read_only_run(project: Path, run_dir: Path, plan: TaskPlan, config: AppConfig) -> list[WorkerResult]:
    runner = CursorRunner(config)
    results: list[WorkerResult] = []
    workers_dir = run_dir / "workers"
    workers_dir.mkdir(parents=True, exist_ok=True)
    max_workers = max(1, min(config.fleet.max_workers, len(plan.workers) or 1))
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = []
        for spec in plan.workers:
            futures.append(pool.submit(runner.run_worker, spec=spec, task=plan.task, workspace=project, worker_dir=workers_dir / spec.id))
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
    return sorted(results, key=lambda r: r.id)


def _run_write_worker(
    *,
    repo: Path,
    base_sha: str,
    run_id: str,
    run_dir: Path,
    spec: WorkerSpec,
    plan: TaskPlan,
    config: AppConfig,
) -> WorkerResult:
    branch = _worker_branch(run_id, spec.id)
    wt_path = run_dir / "worktrees" / spec.id
    result = WorkerResult(id=spec.id, title=spec.title, status="starting", workspace=str(wt_path), branch=branch)
    try:
        worktree_add(repo, wt_path, branch, base_sha)
        cursor_result = CursorRunner(config).run_worker(spec=spec, task=plan.task, workspace=wt_path, worker_dir=run_dir / "workers" / spec.id)
        result.returncode = cursor_result.returncode
        result.duration_seconds = cursor_result.duration_seconds
        result.stdout_path = cursor_result.stdout_path
        result.stderr_path = cursor_result.stderr_path
        result.prompt_path = cursor_result.prompt_path
        result.error = cursor_result.error
        changed = changed_files(wt_path)
        result.changed_files = changed
        result.denied_files = denied_files(changed, config.safety.deny_paths)
        result.out_of_scope_files = out_of_scope_files(changed, spec.paths)
        diff = diff_binary(wt_path)
        diff_path = run_dir / "patches" / f"{spec.id}.patch"
        write_text(diff_path, diff)
        result.diff_path = str(diff_path)
        if result.denied_files:
            result.status = "failed"
            result.error = "Worker changed denied paths. Changes were not committed."
            return result
        if cursor_result.status != "ok":
            result.status = "failed"
            return result
        commit = commit_all(wt_path, f"cursor-fleet({spec.id}): {spec.title}")
        result.commit = commit
        result.status = "ok" if commit else "no_changes"
        return result
    except Exception as exc:  # noqa: BLE001
        result.status = "failed"
        result.error = str(exc)
        return result


def _resolve_conflicts(
    *,
    integration: Path,
    plan: TaskPlan,
    run_dir: Path,
    config: AppConfig,
    attempt: int,
) -> bool:
    conflicts = conflicted_files(integration)
    if not conflicts:
        return True
    spec = WorkerSpec(
        id=f"conflict-resolver-{attempt}",
        title=f"Resolve merge conflicts attempt {attempt}",
        prompt=conflict_resolver_prompt(plan.task, conflicts),
        paths=["."],
        cursor_mode="agent",
        write=True,
    )
    # runner.run_worker wraps the prompt again, so pass a compact task and use spec.prompt as detailed instructions.
    CursorRunner(config).run_worker(spec=spec, task="Resolve cursor-fleet integration conflicts.", workspace=integration, worker_dir=run_dir / "workers" / spec.id)
    return not conflicted_files(integration)


def _integrate_workers(
    *,
    repo: Path,
    base_sha: str,
    run_id: str,
    run_dir: Path,
    plan: TaskPlan,
    config: AppConfig,
    worker_results: list[WorkerResult],
    warnings: list[str],
    errors: list[str],
) -> Path:
    integration_branch = _worker_branch(run_id, "integration")
    integration = run_dir / "integration"
    worktree_add(repo, integration, integration_branch, base_sha)
    for result in worker_results:
        if result.status not in {"ok", "no_changes"}:
            if result.status == "failed" and result.error:
                errors.append(f"Worker {result.id} failed: {result.error}")
            continue
        if not result.commit:
            continue
        merge = merge_branch(integration, result.branch or "")
        if merge.returncode == 0:
            continue
        conflicts = conflicted_files(integration)
        if not conflicts:
            errors.append(f"Merge of {result.id} failed: {merge.stderr.strip()}")
            continue
        warnings.append(f"Merge conflict while integrating {result.id}: {', '.join(conflicts)}")
        resolved = False
        for attempt in range(1, config.fleet.conflict_resolver_attempts + 1):
            if _resolve_conflicts(integration=integration, plan=plan, run_dir=run_dir, config=config, attempt=attempt):
                try:
                    commit_all(integration, f"cursor-fleet: resolve conflicts for {result.id}")
                    resolved = True
                    break
                except GitError as exc:
                    errors.append(f"Conflict resolver could not commit resolution: {exc}")
                    break
        if not resolved:
            errors.append(f"Unresolved conflicts while integrating {result.id}: {', '.join(conflicts)}")
            break
    return integration


def _cleanup(repo: Path, paths: list[Path], branches: list[str]) -> None:
    for path in paths:
        if path.exists():
            worktree_remove(repo, path, force=True)
    for branch in branches:
        branch_delete(repo, branch, force=True)


def run_plan(
    *,
    project: Path,
    plan: TaskPlan,
    config: AppConfig,
    dry_run: bool = False,
    apply_final_patch_flag: bool | None = None,
    apply_on_verify_failure: bool = False,
    keep_runs: bool = False,
) -> FleetReport:
    require_git()
    project = repo_root(project)
    run_id = new_run_id()
    run_dir = _resolve_run_dir(project, config, run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    base_sha = current_head(project)
    warnings = list(plan.warnings)
    errors: list[str] = []

    dirty = has_uncommitted_changes(project)
    if dirty:
        msg = "Original workspace has uncommitted changes. Final patch application may fail or conflict."
        if config.safety.require_clean_tree:
            errors.append("Workspace is dirty and safety.require_clean_tree is true.")
        else:
            warnings.append(msg)

    _write_manifest(run_dir, plan, config, base_sha)

    report = FleetReport(
        run_id=run_id,
        mode=plan.mode,
        task=plan.task,
        status="dry-run" if dry_run else "running",
        project=str(project),
        run_dir=str(run_dir),
        summary=plan.summary,
        warnings=warnings,
        errors=errors,
    )

    if dry_run or errors:
        if dry_run:
            report.workers = [
                WorkerResult(
                    id=spec.id,
                    title=spec.title,
                    status="planned",
                    workspace=str(project if not spec.write else run_dir / "worktrees" / spec.id),
                    changed_files=[],
                )
                for spec in plan.workers
            ]
        write_report(report, run_dir)
        return report

    if plan.mode == "verify":
        report.verification = run_verification(plan.verify_commands, project, run_dir / "verification")
        report.status = "ok" if verification_ok(report.verification) else "failed"
        write_report(report, run_dir)
        return report

    if not plan.write:
        report.workers = _read_only_run(project, run_dir, plan, config)
        failed = [w for w in report.workers if w.status == "failed"]
        report.status = "failed" if failed else "ok"
        if failed:
            report.errors.extend(f"Worker {w.id} failed: {w.error}" for w in failed)
        write_report(report, run_dir)
        return report

    # Write-heavy flow.
    worker_results: list[WorkerResult] = []
    worktree_paths: list[Path] = []
    branches: list[str] = []
    max_workers = max(1, min(config.fleet.max_workers, len(plan.workers) or 1))
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = []
        for spec in plan.workers:
            branch = _worker_branch(run_id, spec.id)
            branches.append(branch)
            path = run_dir / "worktrees" / spec.id
            worktree_paths.append(path)
            futures.append(pool.submit(_run_write_worker, repo=project, base_sha=base_sha, run_id=run_id, run_dir=run_dir, spec=spec, plan=plan, config=config))
        for future in concurrent.futures.as_completed(futures):
            worker_results.append(future.result())
    report.workers = sorted(worker_results, key=lambda r: r.id)

    if any(w.status == "failed" and w.error for w in report.workers):
        report.errors.extend(f"Worker {w.id} failed: {w.error}" for w in report.workers if w.status == "failed" and w.error)

    integration: Path | None = None
    if not report.errors:
        try:
            branches.append(_worker_branch(run_id, "integration"))
            integration = _integrate_workers(repo=project, base_sha=base_sha, run_id=run_id, run_dir=run_dir, plan=plan, config=config, worker_results=report.workers, warnings=report.warnings, errors=report.errors)
            worktree_paths.append(integration)
        except Exception as exc:  # noqa: BLE001
            report.errors.append(f"Integration failed: {exc}")

    if integration and not report.errors:
        report.verification = run_verification(plan.verify_commands, integration, run_dir / "verification") if plan.verify_commands else []
        verify_passed = verification_ok(report.verification)
        if report.verification and not verify_passed:
            report.errors.append("Verification failed; final patch was not applied. Use --apply-on-verify-failure to override.")
        final_patch = diff_binary(integration, base_sha, "HEAD")
        patch_path = run_dir / "final.patch"
        write_text(patch_path, final_patch)
        report.final_patch_path = str(patch_path)
        report.changed_files = diff_name_only(integration, base_sha, "HEAD") if final_patch.strip() else []
        should_apply = plan.apply_final_patch if apply_final_patch_flag is None else apply_final_patch_flag
        if should_apply and final_patch.strip() and (verify_passed or not report.verification or apply_on_verify_failure):
            apply_result = apply_patch(project, patch_path, three_way=True)
            if apply_result.returncode == 0:
                report.final_patch_applied = True
            else:
                report.errors.append("Final patch apply failed: " + (apply_result.stderr.strip() or apply_result.stdout.strip()))

    report.status = "failed" if report.errors else "ok"
    write_report(report, run_dir)

    if report.status == "ok" and config.fleet.cleanup_successful_runs and not keep_runs:
        try:
            _cleanup(project, worktree_paths, branches)
        except Exception as exc:  # noqa: BLE001
            report.warnings.append(f"Cleanup failed: {exc}")
            write_report(report, run_dir)

    return report

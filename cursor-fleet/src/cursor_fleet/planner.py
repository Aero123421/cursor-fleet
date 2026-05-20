from __future__ import annotations

import json
from pathlib import Path

from .git import list_repo_areas
from .models import TaskPlan, WorkerSpec
from .safety import redact_for_prompt
from .util import read_json, safe_id, write_json

ALL_MODES = ["auto", "investigate", "review", "implement", "migrate", "test", "docs", "verify", "fix-ci"]
WRITE_MODES = {"implement", "migrate", "test", "docs", "fix-ci"}


def load_plan(path: Path) -> TaskPlan:
    data = read_json(path)
    if not isinstance(data, dict):
        raise ValueError("plan file must contain a JSON object")
    return TaskPlan.from_dict(data)


def save_plan(path: Path, plan: TaskPlan) -> None:
    write_json(path, plan.to_dict())


def route_mode(task: str, requested: str) -> str:
    if requested != "auto":
        if requested not in ALL_MODES:
            raise ValueError(f"unknown mode: {requested}")
        return requested
    lower = task.lower()
    if any(k in lower for k in ["ci", "github actions", "build failed", "workflow failed", "pipeline", "failed job"]):
        return "fix-ci"
    if any(k in lower for k in ["migrate", "migration", "upgrade", "codemod", "replace api", "deprecate", "deprecated"]):
        return "migrate"
    if any(k in lower for k in ["flaky", "test", "coverage", "spec", "unit test", "integration test"]):
        return "test"
    if any(k in lower for k in ["docs", "documentation", "readme", "manual", "guide", "changelog"]):
        return "docs"
    if any(k in lower for k in ["review", "audit", "security", "correctness", "race", "maintainability"]):
        return "review"
    if any(k in lower for k in ["investigate", "find", "why", "root cause", "explain", "trace", "map"]):
        return "investigate"
    return "implement"


def _cap(items: list[str], max_workers: int) -> list[str]:
    if max_workers <= 0:
        return []
    return items[:max_workers]


def _area_workers(project: Path, max_workers: int, *, task: str, mode: str, prompt_template: str) -> list[WorkerSpec]:
    areas = _cap(list_repo_areas(project), max(1, max_workers))
    if not areas:
        areas = ["."]
    workers: list[WorkerSpec] = []
    for area in areas:
        wid = safe_id(area.replace("/", "-"))
        workers.append(
            WorkerSpec(
                id=wid,
                title=f"{mode}: {area}",
                paths=[area],
                cursor_mode="agent",
                write=True,
                prompt=prompt_template.format(area=area, task=task),
            )
        )
    return workers


def build_plan(
    *,
    task: str,
    requested_mode: str,
    project: Path,
    max_workers: int,
    verify_commands: list[str] | None = None,
    ci_log_path: Path | None = None,
) -> TaskPlan:
    task = task.strip()
    mode = route_mode(task, requested_mode)
    verify_commands = list(verify_commands or [])
    warnings: list[str] = []
    metadata: dict[str, object] = {"requested_mode": requested_mode}

    if mode == "verify":
        return TaskPlan(
            mode=mode,
            task=task or "Verify the current workspace changes.",
            summary="Run configured verification commands without launching Cursor workers.",
            workers=[],
            verify_commands=verify_commands,
            write=False,
            apply_final_patch=False,
            warnings=warnings,
            metadata=metadata,
        )

    if mode == "investigate":
        workers = [
            WorkerSpec(
                id="code-map",
                title="Map relevant code paths",
                cursor_mode="ask",
                write=False,
                paths=["."],
                prompt="Map the relevant code paths, entry points, data flow, and likely owners. Do not edit files.",
            ),
            WorkerSpec(
                id="hypotheses",
                title="Generate evidence-backed hypotheses",
                cursor_mode="ask",
                write=False,
                paths=["."],
                prompt="Investigate likely causes and return evidence-backed hypotheses with file/symbol references. Do not edit files.",
            ),
        ][: max(1, min(max_workers, 2))]
        return TaskPlan(mode=mode, task=task, summary="Read-only investigation split across focused Cursor ask-mode workers.", workers=workers, verify_commands=[], write=False, apply_final_patch=False, warnings=warnings, metadata=metadata)

    if mode == "review":
        focuses = [
            ("correctness", "Look for correctness bugs, behavior regressions, edge cases, and broken invariants."),
            ("security", "Look for security, privacy, injection, authz/authn, secret-handling, and unsafe command risks."),
            ("tests", "Look for missing, weak, flaky, or misleading test coverage. Recommend concrete tests."),
            ("performance", "Look for avoidable performance, scalability, caching, N+1, and concurrency risks."),
            ("maintainability", "Look for maintainability, API design, coupling, migration, and operational risks."),
        ]
        workers = [WorkerSpec(id=fid, title=f"Review: {fid}", cursor_mode="ask", write=False, paths=["."], prompt=prompt + " Do not edit files.") for fid, prompt in focuses[: max(1, min(max_workers, len(focuses)))]]
        return TaskPlan(mode=mode, task=task, summary="Read-only review split by risk area.", workers=workers, verify_commands=[], write=False, apply_final_patch=False, warnings=warnings, metadata=metadata)

    if mode == "implement":
        workers = _area_workers(
            project,
            max_workers,
            task=task,
            mode="implement",
            prompt_template="Implement the requested change for assigned area `{area}`. Coordinate with likely contracts in other areas, but edit outside `{area}` only if unavoidable and explain why.",
        )
        return TaskPlan(mode=mode, task=task, summary="Write-heavy implementation split by repository ownership area.", workers=workers, verify_commands=verify_commands, write=True, apply_final_patch=True, warnings=warnings, metadata=metadata)

    if mode == "migrate":
        workers = _area_workers(
            project,
            max_workers,
            task=task,
            mode="migrate",
            prompt_template="Perform the migration for assigned area `{area}`. Prefer mechanical, consistent changes. Preserve public behavior unless the task requires otherwise. Add compatibility notes if needed.",
        )
        return TaskPlan(mode=mode, task=task, summary="Large migration split by package/service/directory ownership.", workers=workers, verify_commands=verify_commands, write=True, apply_final_patch=True, warnings=warnings, metadata=metadata)

    if mode == "test":
        workers = _area_workers(
            project,
            max_workers,
            task=task,
            mode="test",
            prompt_template="Add or fix tests for assigned area `{area}`. For flaky tests, identify the race/timing/shared-state cause and prefer deterministic fixes over sleeps. Avoid unrelated refactors.",
        )
        return TaskPlan(mode=mode, task=task, summary="Testing/flaky-test work split by code ownership area.", workers=workers, verify_commands=verify_commands, write=True, apply_final_patch=True, warnings=warnings, metadata=metadata)

    if mode == "docs":
        # Docs often touch a smaller surface. Keep worker count conservative.
        areas = ["docs", ".github", "."]
        repo_areas = list_repo_areas(project)
        if "docs" not in repo_areas and not (project / "docs").exists():
            areas = ["."]
        workers = []
        for area in _cap(areas, max(1, min(max_workers, 2))):
            workers.append(WorkerSpec(
                id=safe_id(f"docs-{area}"),
                title=f"docs: {area}",
                paths=[area],
                cursor_mode="agent",
                write=True,
                prompt=f"Update documentation in `{area}` to match the requested task. Keep docs accurate, concise, and synced with code. Do not invent APIs; inspect code when needed.",
            ))
        return TaskPlan(mode=mode, task=task, summary="Documentation sync/generation with conservative write scope.", workers=workers, verify_commands=verify_commands, write=True, apply_final_patch=True, warnings=warnings, metadata=metadata)

    if mode == "fix-ci":
        ci_log = ""
        if ci_log_path:
            if ci_log_path.exists():
                ci_log = redact_for_prompt(ci_log_path.read_text(encoding="utf-8", errors="replace"))
                metadata["ci_log_path"] = str(ci_log_path)
            else:
                warnings.append(f"CI log path does not exist: {ci_log_path}")
        prompt = "Fix the CI failures described by the task. Identify the failing command/test first, make the smallest fix, and update tests if needed."
        if ci_log:
            prompt += "\n\nCI log excerpt:\n" + ci_log
        workers = [WorkerSpec(id="ci-fixer", title="Fix CI failure", paths=["."], cursor_mode="agent", write=True, prompt=prompt)]
        return TaskPlan(mode=mode, task=task, summary="CI failure repair using a focused write worker.", workers=workers, verify_commands=verify_commands, write=True, apply_final_patch=True, warnings=warnings, metadata=metadata)

    raise ValueError(f"unsupported mode: {mode}")

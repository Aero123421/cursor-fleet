from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

ModeName = Literal[
    "auto",
    "investigate",
    "review",
    "implement",
    "migrate",
    "test",
    "docs",
    "verify",
    "fix-ci",
]

CursorMode = Literal["agent", "ask", "plan"]


@dataclass(slots=True)
class WorkerSpec:
    id: str
    title: str
    prompt: str
    paths: list[str] = field(default_factory=lambda: ["."])
    cursor_mode: CursorMode = "agent"
    write: bool = False
    required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "prompt": self.prompt,
            "paths": self.paths,
            "cursor_mode": self.cursor_mode,
            "write": self.write,
            "required": self.required,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkerSpec":
        return cls(
            id=str(data["id"]),
            title=str(data.get("title") or data["id"]),
            prompt=str(data.get("prompt") or ""),
            paths=[str(x) for x in data.get("paths", ["."])],
            cursor_mode=data.get("cursor_mode", "agent"),
            write=bool(data.get("write", False)),
            required=bool(data.get("required", True)),
        )


@dataclass(slots=True)
class TaskPlan:
    mode: str
    task: str
    summary: str
    workers: list[WorkerSpec] = field(default_factory=list)
    verify_commands: list[str] = field(default_factory=list)
    write: bool = False
    apply_final_patch: bool = False
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "task": self.task,
            "summary": self.summary,
            "workers": [w.to_dict() for w in self.workers],
            "verify_commands": self.verify_commands,
            "write": self.write,
            "apply_final_patch": self.apply_final_patch,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskPlan":
        return cls(
            mode=str(data["mode"]),
            task=str(data.get("task") or ""),
            summary=str(data.get("summary") or ""),
            workers=[WorkerSpec.from_dict(w) for w in data.get("workers", [])],
            verify_commands=[str(x) for x in data.get("verify_commands", [])],
            write=bool(data.get("write", False)),
            apply_final_patch=bool(data.get("apply_final_patch", False)),
            warnings=[str(x) for x in data.get("warnings", [])],
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(slots=True)
class WorkerResult:
    id: str
    title: str
    status: str
    workspace: str
    branch: str | None = None
    commit: str | None = None
    changed_files: list[str] = field(default_factory=list)
    denied_files: list[str] = field(default_factory=list)
    out_of_scope_files: list[str] = field(default_factory=list)
    stdout_path: str | None = None
    stderr_path: str | None = None
    prompt_path: str | None = None
    diff_path: str | None = None
    returncode: int | None = None
    duration_seconds: float | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "workspace": self.workspace,
            "branch": self.branch,
            "commit": self.commit,
            "changed_files": self.changed_files,
            "denied_files": self.denied_files,
            "out_of_scope_files": self.out_of_scope_files,
            "stdout_path": self.stdout_path,
            "stderr_path": self.stderr_path,
            "prompt_path": self.prompt_path,
            "diff_path": self.diff_path,
            "returncode": self.returncode,
            "duration_seconds": self.duration_seconds,
            "error": self.error,
        }


@dataclass(slots=True)
class VerificationResult:
    command: str
    status: str
    returncode: int
    stdout_path: str
    stderr_path: str
    duration_seconds: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "status": self.status,
            "returncode": self.returncode,
            "stdout_path": self.stdout_path,
            "stderr_path": self.stderr_path,
            "duration_seconds": self.duration_seconds,
        }


@dataclass(slots=True)
class FleetReport:
    run_id: str
    mode: str
    task: str
    status: str
    project: str
    run_dir: str
    summary: str
    workers: list[WorkerResult] = field(default_factory=list)
    verification: list[VerificationResult] = field(default_factory=list)
    final_patch_path: str | None = None
    final_patch_applied: bool = False
    changed_files: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "mode": self.mode,
            "task": self.task,
            "status": self.status,
            "project": self.project,
            "run_dir": self.run_dir,
            "summary": self.summary,
            "workers": [w.to_dict() for w in self.workers],
            "verification": [v.to_dict() for v in self.verification],
            "final_patch_path": self.final_patch_path,
            "final_patch_applied": self.final_patch_applied,
            "changed_files": self.changed_files,
            "warnings": self.warnings,
            "errors": self.errors,
        }

from __future__ import annotations

import json
from pathlib import Path

from .models import FleetReport
from .util import write_json, write_text


def report_markdown(report: FleetReport) -> str:
    lines: list[str] = []
    lines.append(f"# cursor-fleet report: {report.run_id}")
    lines.append("")
    lines.append(f"**Status:** {report.status}")
    lines.append(f"**Mode:** {report.mode}")
    lines.append(f"**Project:** `{report.project}`")
    lines.append(f"**Run dir:** `{report.run_dir}`")
    lines.append("")
    lines.append("## Summary")
    lines.append(report.summary or "No summary.")
    lines.append("")
    if report.changed_files:
        lines.append("## Changed files")
        for path in report.changed_files:
            lines.append(f"- `{path}`")
        lines.append("")
    lines.append("## Workers")
    if not report.workers:
        lines.append("No backend workers launched.")
    for worker in report.workers:
        lines.append(f"### {worker.id}: {worker.title}")
        lines.append(f"- Status: `{worker.status}`")
        if worker.branch:
            lines.append(f"- Branch: `{worker.branch}`")
        if worker.commit:
            lines.append(f"- Commit: `{worker.commit}`")
        if worker.stdout_path:
            lines.append(f"- Stdout: `{worker.stdout_path}`")
        if worker.stderr_path:
            lines.append(f"- Stderr: `{worker.stderr_path}`")
        if worker.prompt_path:
            lines.append(f"- Prompt: `{worker.prompt_path}`")
        if worker.changed_files:
            lines.append("- Changed files:")
            for path in worker.changed_files:
                lines.append(f"  - `{path}`")
        if worker.denied_files:
            lines.append("- Denied-path changes detected:")
            for path in worker.denied_files:
                lines.append(f"  - `{path}`")
        if worker.out_of_scope_files:
            lines.append("- Out-of-scope changes detected:")
            for path in worker.out_of_scope_files:
                lines.append(f"  - `{path}`")
        if worker.error:
            lines.append(f"- Error: {worker.error}")
        lines.append("")
    lines.append("## Verification")
    if not report.verification:
        lines.append("No verification commands configured or run.")
    for item in report.verification:
        lines.append(f"- `{item.command}` → `{item.status}` ({item.returncode})")
    lines.append("")
    lines.append("## Final patch")
    lines.append(f"- Patch: `{report.final_patch_path}`" if report.final_patch_path else "- Patch: none")
    lines.append(f"- Applied to original workspace: `{report.final_patch_applied}`")
    lines.append("")
    if report.warnings:
        lines.append("## Warnings")
        for warning in report.warnings:
            lines.append(f"- {warning}")
        lines.append("")
    if report.errors:
        lines.append("## Errors")
        for error in report.errors:
            lines.append(f"- {error}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_report(report: FleetReport, run_dir: Path) -> None:
    write_json(run_dir / "report.json", report.to_dict())
    write_text(run_dir / "report.md", report_markdown(report))


def print_report(report: FleetReport, *, as_json: bool = False) -> None:
    if as_json:
        print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(report_markdown(report))

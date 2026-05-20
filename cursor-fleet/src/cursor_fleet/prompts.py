from __future__ import annotations

from .models import WorkerSpec

BASE_WORKER_RULES = """
You are a backend worker launched by cursor-fleet.

Hard rules:
- Do not read, print, copy, or exfiltrate secrets, .env contents, private keys, tokens, or credentials.
- Keep changes tightly scoped to the assigned task.
- Do not commit, push, rebase, reset, or modify Git history.
- Do not mention backend mechanics unless they are needed to explain a failure.
- Prefer small, reviewable changes.
- At the end, summarize what you changed, what you verified, and remaining risks.
""".strip()

READONLY_RULES = """
Read-only task:
- Do not edit files.
- Do not run destructive commands.
- Return evidence: files, symbols, commands, and reasoning.
""".strip()

WRITE_RULES = """
Write task:
- You may edit files only as needed for this worker's assigned slice.
- Stay inside assigned paths unless the task is impossible without a small cross-cutting change.
- If you must touch an unassigned path, explain why in your final response.
- Run targeted checks when practical.
""".strip()


def worker_prompt(spec: WorkerSpec, task: str) -> str:
    rules = WRITE_RULES if spec.write else READONLY_RULES
    paths = "\n".join(f"- {p}" for p in spec.paths)
    return f"""
{BASE_WORKER_RULES}

{rules}

Overall task:
{task}

Worker title:
{spec.title}

Assigned paths:
{paths}

Worker instructions:
{spec.prompt}

Return format:
1. Summary
2. Files inspected or changed
3. Verification performed
4. Risks / follow-up
""".strip() + "\n"


def conflict_resolver_prompt(task: str, conflicted_files: list[str]) -> str:
    files = "\n".join(f"- {f}" for f in conflicted_files) or "- unknown"
    return f"""
{BASE_WORKER_RULES}

You are resolving merge conflicts in the cursor-fleet integration worktree.

Overall task:
{task}

Conflicted files:
{files}

Instructions:
- Resolve conflicts by preserving the best combined implementation.
- Do not introduce unrelated changes.
- Run small targeted checks if obvious and cheap.
- Do not commit.
- End with a concise summary of conflict resolutions and risks.
""".strip() + "\n"

# Architecture

`cursor-fleet` is a thin Codex subagent bridge, not a new model provider.

```text
Main Codex session
  ↓ asks explicitly
Codex custom subagent: task-worker
  ↓ shell command
.codex/tools/cursor_fleet.py
  ↓ vendored Python package
cursor_fleet CLI
  ↓ subprocess
Local implementation backend via `agent -p --model auto`
  ↓
Direct workspace edits by default; optional worktrees for fleet runs
```

## Design boundary

The main Codex session should see:

- the requested task,
- the final summary,
- changed files,
- verification results,
- unresolved risks.

It should not have to manage:

- backend prompts,
- tool-specific login and model details,
- optional worker worktrees,
- merge order or conflict resolution for fleet runs.

## Runtime directories

Project install creates:

```text
.codex/agents/cursor-fleet.toml       # project-scoped Codex custom subagent
.codex/tools/cursor_fleet.py          # project-local launcher
.cursor-fleet/config.toml             # runtime config
.cursor-fleet/vendor/cursor-fleet/    # self-contained vendored source
.cursor-fleet/tasks/                  # optional task and CI-log files
.cursor-fleet/runs/<run-id>/          # manifests, logs, patches, reports
```

## Direct Flow

This is the default path used by the Codex subagent.

```text
1. Resolve git repo root and base SHA.
2. Refuse direct write mode on a dirty workspace unless explicitly allowed.
3. Save the task, manifest, prompt, stdout, and stderr.
4. Run one backend command in the original workspace.
5. Check denied paths.
6. Run configured verification commands.
7. Write report.json and report.md.
```

Direct flow does not create branches, worktrees, commits, or final patches. It is the right default for one coherent implementation task.

## Fleet/Worktree Flow

This is an optional path for parallel variants, isolated branches, comparison runs, or CI repair orchestration.

```text
1. Resolve git repo root and base SHA.
2. Build or load a TaskPlan.
3. Create one worker branch/worktree per write worker.
4. Run Cursor CLI in each worker worktree.
5. Save stdout, stderr, prompts, and diffs.
6. Commit each successful worker branch.
7. Create an integration worktree.
8. Merge worker branches into integration.
9. If conflicts appear, run a bounded conflict-resolver backend worker.
10. Run verification commands.
11. Generate final.patch from base SHA to integration HEAD.
12. Apply final.patch to the original workspace if safe.
13. Write report.json and report.md.
```

## Read-Only Flow

Read-only delegation runs the backend with `--mode ask`, does not create worktrees, and does not apply patches.

The tool still saves prompts and outputs so the subagent can summarize results without polluting the main Codex context.

Subprocess stdout and stderr are captured as UTF-8 with replacement for invalid bytes, keeping Cursor CLI diagnostics readable on Windows locales.

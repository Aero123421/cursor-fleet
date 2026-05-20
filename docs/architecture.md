# Architecture

`cursor-fleet` is a thin orchestration layer, not a new model provider.

```text
Main Codex session
  ↓ asks explicitly
Codex custom subagent: cursor-fleet
  ↓ shell command
.codex/tools/cursor_fleet.py
  ↓ vendored Python package
cursor_fleet CLI
  ↓ subprocess
Cursor CLI workers via `agent -p`
  ↓
Git worktrees, integration, verification, final patch
```

## Design boundary

The main Codex session should see:

- the requested task,
- the final summary,
- changed files,
- verification results,
- unresolved risks.

It should not have to manage:

- worker prompts,
- individual worker worktrees,
- merge order,
- conflict resolution attempts,
- final patch generation.

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

## Write-heavy flow

```text
1. Resolve git repo root and base SHA.
2. Build or load a TaskPlan.
3. Create one worker branch/worktree per write worker.
4. Run Cursor CLI in each worker worktree.
5. Save stdout, stderr, prompts, and diffs.
6. Commit each successful worker branch.
7. Create an integration worktree.
8. Merge worker branches into integration.
9. If conflicts appear, run a bounded conflict-resolver Cursor worker.
10. Run verification commands.
11. Generate final.patch from base SHA to integration HEAD.
12. Apply final.patch to the original workspace if safe.
13. Write report.json and report.md.
```

## Read-only flow

Read-only modes run Cursor CLI with `--mode ask` or `--mode plan`, do not create worktrees, and do not apply patches.

The tool still saves prompts and outputs so the subagent can summarize results without polluting the main Codex context.

# Modes

## `delegate`

Runs one direct in-place implementation by default:

```bash
cursor-fleet delegate --task-file .cursor-fleet/tasks/task.md
```

This is the default path for the Codex subagent. It does not create branches, worktrees, commits, or final patches. Direct write mode refuses a dirty workspace by default when user-change protection is enabled.

Use read-only delegation for investigation or review:

```bash
cursor-fleet delegate --read-only --task "Explain this subsystem."
```

The modes below belong to `cursor-fleet run` and are intended for explicit fleet/worktree orchestration.

## `auto`

Routes to a more specific mode using task text. The router is intentionally simple and deterministic. Codex can also pass an explicit mode when it already knows the task class.

This mode is separate from Cursor's model setting. By default, cursor-fleet invokes Cursor with `--model auto`.

## `investigate`

Read-only code exploration. Useful for root-cause analysis, architecture mapping, and “why does this happen?” questions.

Workers:

- `code-map`
- `hypotheses`

Cursor mode: `ask`.

## `review`

Read-only review split by risk area.

Workers, capped by `fleet.max_workers`:

- correctness
- security
- tests
- performance
- maintainability

Cursor mode: `ask`.

## `implement`

Write-heavy feature implementation or bug fixing. Splits by repository ownership area, using directories such as `apps/*`, `packages/*`, `services/*`, or top-level directories.

Cursor mode: default agent mode.

Uses worktrees.

## `migrate`

Large API, dependency, or code-style migration. Similar to `implement`, but worker prompts emphasize mechanical consistency and behavior preservation.

Cursor mode: default agent mode.

Uses worktrees.

## `test`

Test addition, flaky-test investigation, and coverage-gap work. Worker prompts prefer deterministic fixes over sleeps and avoid unrelated refactors.

Cursor mode: default agent mode.

Uses worktrees.

## `docs`

Documentation generation or synchronization. Conservative by default, usually one or two workers.

Cursor mode: default agent mode.

Uses worktrees.

## `verify`

Runs configured verification commands only. Does not launch backend workers.

Verification command output is captured as UTF-8 with invalid bytes replaced, matching backend worker output handling.

## `fix-ci`

Reads a CI log, redacts obvious token labels, asks a focused backend worker to patch the failure, then runs configured verification.

Cursor mode: default agent mode.

Uses worktrees.

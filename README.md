# bigfaster-worker

`bigfaster-worker` is a Codex subagent definition for fast or large implementation tasks.

It does one thing: orchestrate the official Cursor CLI command, using `agent --model auto --print` by default, and optionally Cursor CLI's built-in `--worktree` mode when isolation is useful.

## Files

- `bigfaster-worker.toml`: the Codex subagent definition.
- `LICENSE` / `NOTICE`: project license metadata.

## Install

Copy `bigfaster-worker.toml` into a Codex agents directory for the target workspace, for example:

```text
.codex/agents/bigfaster-worker.toml
```

Then ask Codex to use `bigfaster-worker` for a task.

## Cursor CLI Basis

The subagent is intentionally aligned with official Cursor CLI docs:

- CLI command: `agent`
- Headless/non-interactive mode: `--print` or `-p`
- Default model selection: `--model auto`
- Optional isolation: `--worktree`
- Explicit workspace targeting: `--workspace <REPO_PATH>`
- Headless trust prompt bypass: `--trust`
- Optional structured output: `--output-format json` or `--output-format stream-json`

References:

- <https://cursor.com/docs/cli/reference/parameters.md>
- <https://cursor.com/docs/cli/using.md>
- <https://cursor.com/docs/models-and-pricing.md>

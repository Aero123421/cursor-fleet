# bigfaster-worker

`bigfaster-worker` is a tiny Codex subagent definition for delegating large or fast-moving implementation tasks to the official Cursor CLI.

It is intentionally just a TOML file. No Python package, no runner, no vendored CLI, no hidden orchestration layer.

## What It Does

The subagent tells Codex how to use Cursor CLI in headless mode:

```bash
agent --model auto --print --trust -- "<TASK_PROMPT>"
```

For risky, dirty, or parallel work, it can use Cursor CLI's built-in worktree mode:

```bash
agent --model auto --print --trust --worktree <WORKTREE_NAME> -- "<TASK_PROMPT>"
```

`--trust` is part of the default command shape because headless runs cannot answer a workspace trust prompt interactively.
The `--` before the prompt keeps the prompt from being parsed as a flag value, especially when `--worktree` is present.

After Cursor finishes, the subagent is responsible for inspecting the diff, running reasonable checks, and reporting back clearly.

## Why

Codex is good at coordinating work and reviewing results. Cursor CLI can be useful as a fast implementation backend. This subagent keeps that handoff lightweight:

- Codex decides when delegation is useful.
- Cursor CLI attempts the implementation.
- Codex inspects `git diff` and reports what happened.
- Worktrees are used only when they actually help.

## Install

Copy the agent file into your project:

```bash
mkdir -p .codex/agents
cp bigfaster-worker.toml .codex/agents/bigfaster-worker.toml
```

Then ask Codex:

```text
Use bigfaster-worker to implement this task.
```

## Recommended AGENTS.md Usage

For best results, tell your main Codex agent how to use this subagent from the target repository's `AGENTS.md`.

Recommended snippet:

```md
## bigfaster-worker

Use `bigfaster-worker` for large or fast-moving implementation tasks where a Cursor CLI implementation attempt would help.

- Prefer one `bigfaster-worker` invocation for one coherent repository task.
- Do not call multiple `bigfaster-worker` agents unless the user explicitly asks for parallel implementations, comparison variants, or clearly disjoint ownership slices.
- If multiple related fixes touch the same package or feature area, combine them into one prompt with clear ownership boundaries.
- Give the worker explicit allowed files/directories, files/directories to avoid, and known test commands.
- The worker should use `--worktree` when the tree is dirty, the task is risky, or parallel work is likely.
- The worker must inspect `git diff` after Cursor finishes and report tests/checks run.
```

This matters because Codex may otherwise split a broad request into several subagent calls. That can be useful for truly independent work, but for related fixes in one repository it is usually better to make one `bigfaster-worker` call with a complete prompt.

## Requirements

- Codex with project-scoped subagent support.
- Cursor CLI installed and authenticated.
- The official Cursor CLI command must be available as `agent`.

Check Cursor CLI:

```bash
agent status
agent models
```

If you changed Cursor accounts:

```bash
agent logout
agent login
```

## Trust and Force

`bigfaster-worker` assumes `--trust` by default:

```bash
agent --model auto --print --trust -- "<TASK_PROMPT>"
```

This is a practical headless-mode default. Without it, Cursor CLI may stop at a workspace trust prompt that the subagent cannot answer interactively.

`--force` is different. It can bypass command approval prompts, so the subagent should not use it by default. It may use `--force` only when:

- the user explicitly authorized the implementation,
- the expected commands are part of the task or reasonable verification,
- command approval would otherwise block a headless run,
- the subagent reports that it used `--force` and why.

Example:

```bash
agent --model auto --print --trust --force -- "<TASK_PROMPT>"
```

This is useful when Cursor says it cannot run tests or checks because approval is blocking headless execution.

## How It Chooses Worktree vs Current Tree

The subagent starts by checking:

```bash
git status --short
git branch --show-current
```

It should prefer `--worktree` when:

- the working tree is already dirty,
- the task is risky,
- parallel work is likely,
- you want an isolated implementation attempt.

Use a short descriptive worktree name:

```bash
agent --model auto --print --trust --worktree pptx-semantic-style -- "<TASK_PROMPT>"
```

It may run directly in the current tree when:

- the tree is clean,
- the task is small or localized,
- you explicitly want in-place edits.

## Safety Notes

`bigfaster-worker` does not ask Cursor to merge, push, or delete worktrees by default.

It also instructs Cursor not to revert unrelated user changes or changes made by other agents. After Cursor finishes, the subagent must inspect:

```bash
git status --short
git diff --stat
git diff
```

If unrelated files changed, it should either revert those specific changes or report them clearly.

When Cursor runs in `--worktree`, the subagent should not blindly merge that worktree. The safer workflow is:

1. Inspect the Cursor worktree diff.
2. Confirm the changed files match the requested ownership boundary.
3. Apply or copy only the intended files back to the original repository.
4. Run tests/checks in the original repository if the worktree is missing dependencies.
5. Leave unrelated user or agent changes untouched.

This matters because Cursor's isolated worktree may not have `node_modules`, virtualenvs, generated assets, or other local dependencies available.

## Official Cursor CLI Basis

This repo follows the official Cursor CLI command shape:

- `agent`: Cursor CLI command
- `--print` / `-p`: headless, non-interactive mode
- `--model auto`: Cursor Auto model selection
- `--trust`: default for this subagent, because headless runs cannot answer trust prompts
- `--worktree <NAME>`: Cursor CLI built-in isolated worktree execution
- `--`: separates Cursor flags from the task prompt
- `--workspace <REPO_PATH>`: target a specific repository
- `--force`: only when explicitly approved and needed to avoid blocked command approvals
- `--output-format json` / `stream-json`: optional structured output

References:

- [Cursor CLI parameters](https://cursor.com/docs/cli/reference/parameters.md)
- [Using Cursor CLI](https://cursor.com/docs/cli/using.md)
- [Cursor models and pricing](https://cursor.com/docs/models-and-pricing.md)

## Repository Contents

```text
bigfaster-worker.toml  # Codex subagent definition
README.md             # this guide
LICENSE
NOTICE
AGENTS.md             # maintenance instructions for this repo
```

## License

Apache-2.0

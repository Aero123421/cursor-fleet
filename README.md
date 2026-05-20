# bigfaster-worker

`bigfaster-worker` is a tiny Codex subagent definition for delegating large or fast-moving implementation tasks to the official Cursor CLI.

It is intentionally just a TOML file. No Python package, no runner, no vendored CLI, no hidden orchestration layer.

## What It Does

The subagent tells Codex how to use Cursor CLI in headless mode:

```bash
agent --model auto --print "<TASK_PROMPT>"
```

For risky, dirty, or parallel work, it can use Cursor CLI's built-in worktree mode:

```bash
agent --model auto --print --worktree "<TASK_PROMPT>"
```

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

## Official Cursor CLI Basis

This repo follows the official Cursor CLI command shape:

- `agent`: Cursor CLI command
- `--print` / `-p`: headless, non-interactive mode
- `--model auto`: Cursor Auto model selection
- `--worktree`: Cursor CLI built-in isolated worktree execution
- `--workspace <REPO_PATH>`: target a specific repository
- `--trust`: avoid workspace trust prompts in headless mode
- `--force`: only when explicitly approved and needed
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

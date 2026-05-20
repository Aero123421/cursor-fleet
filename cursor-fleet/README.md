# cursor-fleet

**Use Codex as the brain, Cursor CLI as the fleet.**

`cursor-fleet` is a project-scoped Codex subagent plus a small Python CLI that decomposes large coding tasks, runs Cursor CLI workers with `agent -p`, isolates write-heavy workers in Git worktrees, integrates their changes, verifies the result, and applies one final patch back to the original workspace.

It is intentionally narrow:

- Codex handles orchestration and final judgment.
- Cursor CLI handles worker execution.
- Git worktrees isolate risky edits.
- `cursor-fleet` owns the messy middle: planning, worker prompts, merge, verification, reporting, cleanup.

> This project is not affiliated with Cursor, Anysphere, OpenAI, or Codex. Users must install and authenticate Cursor CLI separately.

## Why this exists

Codex subagents are great for delegation, but large write-heavy tasks can become noisy if the main session has to manage every worker, worktree, merge conflict, and verification step.

`cursor-fleet` lets the main Codex session say:

```text
Use cursor-fleet to implement this. Return the final result, changed files, tests run, and remaining risks.
```

The main session does **not** need to know about individual Cursor worker worktrees.

## Modes

`cursor-fleet` ships with all core modes enabled from day one:

| Mode | Purpose | Default Cursor mode | Worktrees |
| --- | --- | --- | --- |
| `investigate` | Large code investigation, root-cause analysis, architecture mapping | `ask` | No |
| `review` | PR/code review split by risk area | `ask` | No |
| `implement` | Feature implementation or bug fix | agent | Yes |
| `migrate` | Large migrations across packages/services | agent | Yes |
| `test` | Test additions, flaky-test investigation, coverage gaps | agent | Yes |
| `docs` | Documentation generation/sync with code | agent | Yes |
| `verify` | Verification-only pass on existing changes | none | No |
| `fix-ci` | Read CI logs, patch failures, re-run verification | agent | Yes |
| `auto` | Route to one of the above | mixed | Depends |

## Quick start for a normal install

```bash
# from this repository
python3 -m pip install -e .

# inside the project where you want the Codex subagent
cursor-fleet init --project .

# sanity check
cursor-fleet doctor --project .
```

## One-command project install from a cloned repo

This is the path intended for “give Codex the GitHub URL and let it install the subagent”.

```bash
git clone https://github.com/YOUR_ORG/cursor-fleet.git /tmp/cursor-fleet
python3 /tmp/cursor-fleet/scripts/install_project.py --target .
python3 .codex/tools/cursor_fleet.py doctor
```

The installer copies a self-contained vendor copy into your project:

```text
.codex/agents/cursor-fleet.toml
.codex/tools/cursor_fleet.py
.cursor-fleet/config.toml
.cursor-fleet/vendor/cursor-fleet/
```

That means the Codex subagent can run with:

```bash
python3 .codex/tools/cursor_fleet.py run --mode auto --task-file .cursor-fleet/tasks/task.md
```

No global Python package installation is required after project install.

## Prompt to give Codex with your future GitHub URL

After pushing this repository to GitHub, give Codex a prompt like:

```text
Install cursor-fleet from https://github.com/YOUR_ORG/cursor-fleet into this repository as a project-scoped Codex subagent.
Clone it to /tmp/cursor-fleet, run scripts/install_project.py --target ., then run python3 .codex/tools/cursor_fleet.py doctor.
Do not start a fleet run yet.
```

Then, for a large task:

```text
Use the cursor-fleet subagent to handle this task end-to-end. Hide worker worktree details unless something fails. Return only the final summary, changed files, verification results, and unresolved risks.
```

## Cursor CLI requirements

Install and authenticate Cursor CLI separately. `cursor-fleet` defaults to the `agent` binary:

```bash
agent status
agent models
```

Override the binary or model in `.cursor-fleet/config.toml`:

```toml
[cursor]
bin = "agent"
model = "auto"
output_format = "json"
trust = true
force = false
```

You can also override per run:

```bash
python3 .codex/tools/cursor_fleet.py run \
  --mode review \
  --model composer-2.5 \
  --max-workers 5 \
  --task "Review this branch against main for correctness, security, tests, performance, and maintainability."
```

## Safety defaults

- Uses the smallest worker count it can justify.
- Uses Cursor `ask` mode for read-only investigation and review.
- Uses Git worktrees for write-heavy modes.
- Keeps worker prompts scoped to assigned paths.
- Denies obvious secret paths by default.
- Runs configured verification before applying final patches.
- Skips final patch application when verification fails, unless explicitly overridden.
- Does not commit to the user's original branch.

## Verification

Edit `.cursor-fleet/config.toml`:

```toml
[verification]
commands = [
  "pnpm test",
  "pnpm typecheck",
  "pnpm lint",
]
```

Or pass commands per run:

```bash
python3 .codex/tools/cursor_fleet.py run \
  --mode verify \
  --verify-cmd "pnpm test" \
  --verify-cmd "pnpm typecheck"
```

## Examples

### Investigation

```bash
python3 .codex/tools/cursor_fleet.py run \
  --mode investigate \
  --task "Find why checkout totals sometimes differ between the API and UI."
```

### Review

```bash
python3 .codex/tools/cursor_fleet.py run \
  --mode review \
  --task "Review this branch against main. Focus on correctness, security, tests, performance, and maintainability."
```

### Implementation

```bash
python3 .codex/tools/cursor_fleet.py run \
  --mode implement \
  --max-workers 4 \
  --task "Add CSV export for billing invoices end-to-end."
```

### Migration

```bash
python3 .codex/tools/cursor_fleet.py run \
  --mode migrate \
  --task "Migrate the old feature-flag API to the new typed client across the repo."
```

### Test/flaky work

```bash
python3 .codex/tools/cursor_fleet.py run \
  --mode test \
  --task "Investigate and fix flaky auth session tests; add regression coverage."
```

### Docs sync

```bash
python3 .codex/tools/cursor_fleet.py run \
  --mode docs \
  --task "Update docs to match the new billing export behavior and API contract."
```

### CI fix

```bash
python3 .codex/tools/cursor_fleet.py run \
  --mode fix-ci \
  --ci-log /tmp/ci.log \
  --task "Fix the failures shown in this CI log."
```

## Repository layout

```text
src/cursor_fleet/              Python CLI and orchestration code
templates/codex/               Project-scoped Codex subagent template
templates/config/              Default project config
templates/tools/               Project launcher copied into .codex/tools
docs/                          Architecture, modes, safety, and install docs
scripts/install_project.py     Self-contained project installer
examples/                      Example plans and tasks
```

## Current status

This is an alpha-quality developer tool skeleton with real orchestration code. Expect to tune prompts, verification commands, conflict-resolution behavior, and path partitioning for your repository.

## License

Apache-2.0

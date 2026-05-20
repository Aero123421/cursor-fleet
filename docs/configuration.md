# Configuration

`cursor-fleet` reads `.cursor-fleet/config.toml` from the target project.

## Cursor

```toml
[cursor]
bin = "agent"
model = "auto"
output_format = "json"
trust = true
force = false
sandbox = ""
extra_args = []
```

- `bin`: Cursor CLI binary. Defaults to `agent`.
- `model`: Cursor model. Defaults to `auto`, which lets Cursor choose the model.
- `output_format`: `text`, `json`, or `stream-json`.
- `trust`: passes `--trust`, useful in headless mode.
- `force`: passes `--force` only if `safety.allow_force = true`.
- `sandbox`: optional Cursor sandbox flag.
- `extra_args`: additional Cursor CLI flags.

## Fleet

```toml
[fleet]
max_workers = 4
run_dir = ".cursor-fleet/runs"
cleanup_successful_runs = false
keep_failed_runs = true
worker_timeout_seconds = 1800
conflict_resolver_attempts = 1
```

## Safety

```toml
[safety]
require_clean_tree = false
protect_user_changes = true
allow_force = false
allow_workspace_outside_repo = false
deny_paths = [
  ".env",
  ".env.*",
  "**/.env",
  "**/.env.*",
  "**/*.pem",
  "**/*.key",
  "**/secrets/**",
]
```

The deny list is checked after each worker run. If a worker changes a denied path, its changes are not committed for integration.

## Verification

```toml
[verification]
commands = [
  "pnpm test",
  "pnpm typecheck",
  "pnpm lint",
]
```

Verification commands run in the integration worktree. If they fail, the final patch is not applied unless `--apply-on-verify-failure` is used.

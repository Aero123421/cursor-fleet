# Safety model

`cursor-fleet` is a guardrailed local orchestration tool, not a hard security sandbox.

Cursor CLI can read files, write files, and run shell commands. Codex sandboxing and Cursor's own approval/sandbox settings still matter.

## Guardrails included

- Worktree isolation for write-heavy tasks.
- Read-only Cursor modes for investigation and review.
- Deny-path checks after worker execution.
- Final patch application only after integration.
- Verification gate before applying final patch.
- No automatic commits to the original branch.
- Bounded conflict resolver attempts.
- Logs and reports saved per run.

## Guardrails not guaranteed

- Preventing a model from reading every file it can access.
- Preventing all secret-like data from appearing in logs.
- Proving a generated patch is correct.
- Preventing bad commands if Cursor is run with broad permissions.

## Recommended use

- Use in disposable branches.
- Keep production credentials out of the workspace.
- Configure `safety.deny_paths` for your repo.
- Keep `cursor.force = false` unless you really need it.
- Review final diffs before committing.

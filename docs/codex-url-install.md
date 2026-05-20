# Installing by giving Codex a GitHub URL

After you push this repo to GitHub, you can ask Codex to install it into another repository.

Use this prompt:

```text
Install cursor-fleet from https://github.com/YOUR_ORG/cursor-fleet into this repository as a project-scoped Codex subagent.
Clone it to /tmp/cursor-fleet, run:
python3 /tmp/cursor-fleet/scripts/install_project.py --target .
Then run:
python3 .codex/tools/cursor_fleet.py doctor
Do not start a fleet run yet.
```

What this does:

1. Clones the OSS repo.
2. Copies `.codex/agents/cursor-fleet.toml` into the target repo.
3. Copies a project-local launcher into `.codex/tools/cursor_fleet.py`.
4. Vendors the Python source into `.cursor-fleet/vendor/cursor-fleet`.
5. Creates `.cursor-fleet/config.toml`.
6. Adds runtime directories to `.gitignore`.

Then use:

```text
Use the cursor-fleet subagent to implement this large task end-to-end.
```

Codex should invoke the subagent, and the subagent should invoke:

```bash
python3 .codex/tools/cursor_fleet.py run --mode auto --task-file .cursor-fleet/tasks/<task>.md
```

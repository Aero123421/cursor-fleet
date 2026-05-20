# Agent instructions for cursor-fleet

This repository is a developer tool. Keep changes boring, deterministic, and easy to audit.

- Prefer Python standard library over new dependencies.
- Keep project installation self-contained: `scripts/install_project.py` should be able to copy the runner into another repo without requiring a global package install.
- Do not vendor Cursor CLI, Codex, model weights, credentials, or token material.
- Treat `.env`, private keys, tokens, CI secrets, and credentials as forbidden input.
- When changing runner behavior, update `docs/architecture.md`, `docs/modes.md`, and the Codex agent template.
- Do not remove safety gates to make demos easier.

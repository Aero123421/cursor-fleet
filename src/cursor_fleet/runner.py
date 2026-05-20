from __future__ import annotations

import shutil
import time
from pathlib import Path

from .config import AppConfig
from .models import WorkerResult, WorkerSpec
from .prompts import worker_prompt
from .util import run_cmd, shlex_join, write_text


class CursorRunner:
    def __init__(self, config: AppConfig):
        self.config = config

    def resolve_binary(self) -> str | None:
        configured = self.config.cursor.bin
        if Path(configured).exists():
            return configured
        found = shutil.which(configured)
        if found:
            return found
        # Friendly fallbacks for different Cursor CLI installs.
        for candidate in ("agent", "cursor-agent", "cursor"):
            found = shutil.which(candidate)
            if found:
                return found
        return None

    def doctor(self) -> list[str]:
        messages: list[str] = []
        binary = self.resolve_binary()
        if binary:
            messages.append(f"ok: Cursor CLI binary found: {binary}")
        else:
            messages.append("error: Cursor CLI binary not found. Install Cursor CLI or set cursor.bin in .cursor-fleet/config.toml")
            return messages
        result = run_cmd([binary, "status"], Path.cwd(), timeout=20)
        if result.returncode == 0:
            messages.append("ok: Cursor CLI status command succeeded")
        else:
            messages.append("warn: Cursor CLI status failed; run `agent login` or check your Cursor installation")
            if result.stderr.strip():
                messages.append(result.stderr.strip())
        models = run_cmd([binary, "models"], Path.cwd(), timeout=20)
        if models.returncode == 0:
            messages.append("ok: Cursor CLI models command succeeded")
        else:
            messages.append("warn: Cursor CLI models command failed; model override may not be available")
        return messages

    def build_command(self, workspace: Path, spec: WorkerSpec, prompt: str) -> list[str]:
        binary = self.resolve_binary()
        if not binary:
            raise RuntimeError("Cursor CLI binary not found")
        cfg = self.config.cursor
        cmd = [binary, "-p", "--output-format", cfg.output_format, "--model", cfg.model, "--workspace", str(workspace)]
        if cfg.trust:
            cmd.append("--trust")
        if cfg.sandbox:
            cmd.extend(["--sandbox", cfg.sandbox])
        if cfg.force and self.config.safety.allow_force:
            cmd.append("--force")
        if spec.cursor_mode in {"ask", "plan"}:
            cmd.extend(["--mode", spec.cursor_mode])
        cmd.extend(cfg.extra_args)
        cmd.append(prompt)
        return cmd

    def run_worker(self, *, spec: WorkerSpec, task: str, workspace: Path, worker_dir: Path) -> WorkerResult:
        worker_dir.mkdir(parents=True, exist_ok=True)
        prompt = worker_prompt(spec, task)
        prompt_path = worker_dir / "prompt.md"
        stdout_path = worker_dir / "stdout.txt"
        stderr_path = worker_dir / "stderr.txt"
        command_path = worker_dir / "command.txt"
        write_text(prompt_path, prompt)
        result = WorkerResult(
            id=spec.id,
            title=spec.title,
            status="running",
            workspace=str(workspace),
            prompt_path=str(prompt_path),
            stdout_path=str(stdout_path),
            stderr_path=str(stderr_path),
        )
        try:
            cmd = self.build_command(workspace, spec, prompt)
            write_text(command_path, shlex_join(cmd[:-1]) + " <prompt>\n")
            started = time.monotonic()
            completed = run_cmd(cmd, workspace, timeout=self.config.fleet.worker_timeout_seconds)
            result.returncode = completed.returncode
            result.duration_seconds = completed.duration_seconds
            write_text(stdout_path, completed.stdout)
            write_text(stderr_path, completed.stderr)
            if completed.returncode == 0:
                result.status = "ok"
            else:
                result.status = "failed"
                result.error = completed.stderr.strip() or completed.stdout.strip() or f"Cursor exited with {completed.returncode}"
        except Exception as exc:  # noqa: BLE001 - capture for report instead of crashing fan-out
            result.status = "failed"
            result.error = str(exc)
            write_text(stderr_path, str(exc) + "\n")
        return result

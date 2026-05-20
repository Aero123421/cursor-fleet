from __future__ import annotations

from pathlib import Path

from .models import VerificationResult
from .util import run_cmd, safe_id, write_text


def run_verification(commands: list[str], cwd: Path, output_dir: Path) -> list[VerificationResult]:
    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[VerificationResult] = []
    for index, command in enumerate(commands, start=1):
        stem = f"{index:02d}-{safe_id(command)[:80]}"
        stdout_path = output_dir / f"{stem}.stdout.txt"
        stderr_path = output_dir / f"{stem}.stderr.txt"
        result = run_cmd(command, cwd, shell=True)
        write_text(stdout_path, result.stdout)
        write_text(stderr_path, result.stderr)
        results.append(
            VerificationResult(
                command=command,
                status="ok" if result.returncode == 0 else "failed",
                returncode=result.returncode,
                stdout_path=str(stdout_path),
                stderr_path=str(stderr_path),
                duration_seconds=result.duration_seconds,
            )
        )
    return results


def verification_ok(results: list[VerificationResult]) -> bool:
    return all(r.returncode == 0 for r in results)

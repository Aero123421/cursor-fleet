from __future__ import annotations

import json
import os
import shlex
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(slots=True)
class CommandResult:
    cmd: list[str] | str
    cwd: str
    returncode: int
    stdout: str
    stderr: str
    duration_seconds: float

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    def to_dict(self) -> dict[str, object]:
        return {
            "cmd": self.cmd,
            "cwd": self.cwd,
            "returncode": self.returncode,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration_seconds": self.duration_seconds,
        }


def run_cmd(
    cmd: list[str] | str,
    cwd: Path | str,
    *,
    timeout: int | None = None,
    env: dict[str, str] | None = None,
    shell: bool = False,
    input_text: str | None = None,
) -> CommandResult:
    start = time.monotonic()
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        input=input_text,
        text=True,
        capture_output=True,
        timeout=timeout,
        env=env,
        shell=shell,
    )
    return CommandResult(
        cmd=cmd,
        cwd=str(cwd),
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        duration_seconds=time.monotonic() - start,
    )


def shlex_join(cmd: Iterable[str]) -> str:
    return shlex.join([str(x) for x in cmd])


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def safe_id(value: str) -> str:
    out = []
    for ch in value.lower():
        if ch.isalnum():
            out.append(ch)
        elif ch in {"-", "_", "."}:
            out.append(ch)
        elif ch.isspace() or ch in {"/", "\\", ":"}:
            out.append("-")
    result = "".join(out).strip("-._")
    while "--" in result:
        result = result.replace("--", "-")
    return result or "item"


def relative_to(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)

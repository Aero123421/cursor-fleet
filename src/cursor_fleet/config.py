from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_CONFIG_TOML = """
[cursor]
bin = "agent"
model = "composer-2.5"
output_format = "json"
trust = true
force = false
sandbox = ""
extra_args = []

[fleet]
max_workers = 4
run_dir = ".cursor-fleet/runs"
cleanup_successful_runs = false
keep_failed_runs = true
worker_timeout_seconds = 1800
conflict_resolver_attempts = 1

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
  "**/*.p12",
  "**/*.pfx",
  "**/id_rsa",
  "**/id_ed25519",
  "**/secrets/**",
  "**/.aws/**",
  "**/.ssh/**",
]

[verification]
commands = []
""".strip() + "\n"


@dataclass(slots=True)
class CursorConfig:
    bin: str = "agent"
    model: str = "composer-2.5"
    output_format: str = "json"
    trust: bool = True
    force: bool = False
    sandbox: str = ""
    extra_args: list[str] = field(default_factory=list)


@dataclass(slots=True)
class FleetConfig:
    max_workers: int = 4
    run_dir: str = ".cursor-fleet/runs"
    cleanup_successful_runs: bool = False
    keep_failed_runs: bool = True
    worker_timeout_seconds: int = 1800
    conflict_resolver_attempts: int = 1


@dataclass(slots=True)
class SafetyConfig:
    require_clean_tree: bool = False
    protect_user_changes: bool = True
    allow_force: bool = False
    allow_workspace_outside_repo: bool = False
    deny_paths: list[str] = field(default_factory=lambda: [
        ".env", ".env.*", "**/.env", "**/.env.*", "**/*.pem", "**/*.key",
        "**/*.p12", "**/*.pfx", "**/id_rsa", "**/id_ed25519", "**/secrets/**",
        "**/.aws/**", "**/.ssh/**",
    ])


@dataclass(slots=True)
class VerificationConfig:
    commands: list[str] = field(default_factory=list)


@dataclass(slots=True)
class AppConfig:
    cursor: CursorConfig = field(default_factory=CursorConfig)
    fleet: FleetConfig = field(default_factory=FleetConfig)
    safety: SafetyConfig = field(default_factory=SafetyConfig)
    verification: VerificationConfig = field(default_factory=VerificationConfig)
    path: Path | None = None


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x) for x in value]
    return [str(value)]


def find_config(project: Path, explicit: str | None = None) -> Path | None:
    if explicit:
        p = Path(explicit).expanduser()
        return p if p.is_absolute() else project / p
    candidates = [
        project / ".cursor-fleet" / "config.toml",
        project / "cursor-fleet.toml",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def load_config(project: Path, explicit: str | None = None) -> AppConfig:
    config = AppConfig()
    path = find_config(project, explicit)
    if not path or not path.exists():
        return config
    data = tomllib.loads(path.read_text(encoding="utf-8"))

    cursor = data.get("cursor", {})
    fleet = data.get("fleet", {})
    safety = data.get("safety", {})
    verification = data.get("verification", {})

    config.cursor = CursorConfig(
        bin=str(cursor.get("bin", config.cursor.bin)),
        model=str(cursor.get("model", config.cursor.model)),
        output_format=str(cursor.get("output_format", config.cursor.output_format)),
        trust=bool(cursor.get("trust", config.cursor.trust)),
        force=bool(cursor.get("force", config.cursor.force)),
        sandbox=str(cursor.get("sandbox", config.cursor.sandbox)),
        extra_args=_as_list(cursor.get("extra_args", config.cursor.extra_args)),
    )
    config.fleet = FleetConfig(
        max_workers=int(fleet.get("max_workers", config.fleet.max_workers)),
        run_dir=str(fleet.get("run_dir", config.fleet.run_dir)),
        cleanup_successful_runs=bool(fleet.get("cleanup_successful_runs", config.fleet.cleanup_successful_runs)),
        keep_failed_runs=bool(fleet.get("keep_failed_runs", config.fleet.keep_failed_runs)),
        worker_timeout_seconds=int(fleet.get("worker_timeout_seconds", config.fleet.worker_timeout_seconds)),
        conflict_resolver_attempts=int(fleet.get("conflict_resolver_attempts", config.fleet.conflict_resolver_attempts)),
    )
    config.safety = SafetyConfig(
        require_clean_tree=bool(safety.get("require_clean_tree", config.safety.require_clean_tree)),
        protect_user_changes=bool(safety.get("protect_user_changes", config.safety.protect_user_changes)),
        allow_force=bool(safety.get("allow_force", config.safety.allow_force)),
        allow_workspace_outside_repo=bool(safety.get("allow_workspace_outside_repo", config.safety.allow_workspace_outside_repo)),
        deny_paths=_as_list(safety.get("deny_paths", config.safety.deny_paths)),
    )
    config.verification = VerificationConfig(commands=_as_list(verification.get("commands", config.verification.commands)))
    config.path = path
    return config


def write_default_config(path: Path, force: bool = False) -> bool:
    if path.exists() and not force:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(DEFAULT_CONFIG_TOML, encoding="utf-8")
    return True


def apply_env_overrides(config: AppConfig) -> None:
    if os.environ.get("CURSOR_FLEET_CURSOR_BIN"):
        config.cursor.bin = os.environ["CURSOR_FLEET_CURSOR_BIN"]
    if os.environ.get("CURSOR_FLEET_MODEL"):
        config.cursor.model = os.environ["CURSOR_FLEET_MODEL"]
    if os.environ.get("CURSOR_FLEET_MAX_WORKERS"):
        config.fleet.max_workers = int(os.environ["CURSOR_FLEET_MAX_WORKERS"])

from __future__ import annotations

import fnmatch
from pathlib import Path


def normalize(path: str) -> str:
    return path.replace("\\", "/").lstrip("./") or "."


def path_matches(path: str, pattern: str) -> bool:
    p = normalize(path)
    pat = normalize(pattern)
    if fnmatch.fnmatch(p, pat):
        return True
    if pat.startswith("**/") and fnmatch.fnmatch(p, pat[3:]):
        return True
    return False


def denied_files(paths: list[str], deny_patterns: list[str]) -> list[str]:
    denied: list[str] = []
    for path in paths:
        for pattern in deny_patterns:
            if path_matches(path, pattern):
                denied.append(path)
                break
    return sorted(set(denied))


def out_of_scope_files(paths: list[str], allowed_paths: list[str]) -> list[str]:
    allowed = [normalize(p) for p in allowed_paths or ["."]]
    if "." in allowed:
        return []
    out: list[str] = []
    for raw in paths:
        path = normalize(raw)
        ok = False
        for allowed_path in allowed:
            if path == allowed_path or path.startswith(allowed_path.rstrip("/") + "/"):
                ok = True
                break
        if not ok:
            out.append(raw)
    return sorted(set(out))


def ensure_inside_repo(path: Path, repo: Path) -> bool:
    try:
        path.resolve().relative_to(repo.resolve())
        return True
    except ValueError:
        return False


def redact_for_prompt(text: str, max_chars: int = 120_000) -> str:
    # This is not a full DLP engine; it trims huge logs and masks common token-looking labels.
    replacements = [
        ("password=", "password=<redacted>"),
        ("PASSWORD=", "PASSWORD=<redacted>"),
        ("token=", "token=<redacted>"),
        ("TOKEN=", "TOKEN=<redacted>"),
        ("api_key=", "api_key=<redacted>"),
        ("API_KEY=", "API_KEY=<redacted>"),
        ("secret=", "secret=<redacted>"),
        ("SECRET=", "SECRET=<redacted>"),
    ]
    redacted = text
    for needle, replacement in replacements:
        redacted = redacted.replace(needle, replacement)
    if len(redacted) > max_chars:
        redacted = redacted[:max_chars] + "\n\n[truncated by cursor-fleet]\n"
    return redacted

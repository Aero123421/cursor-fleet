from __future__ import annotations

import os
import shutil
from pathlib import Path

from .util import CommandResult, run_cmd


class GitError(RuntimeError):
    pass


def git(args: list[str], cwd: Path, *, timeout: int | None = None) -> CommandResult:
    return run_cmd(["git", *args], cwd, timeout=timeout)


def git_checked(args: list[str], cwd: Path, *, timeout: int | None = None) -> CommandResult:
    result = git(args, cwd, timeout=timeout)
    if result.returncode != 0:
        raise GitError(f"git {' '.join(args)} failed in {cwd}: {result.stderr.strip()}")
    return result


def require_git() -> str:
    path = shutil.which("git")
    if not path:
        raise GitError("git binary was not found on PATH")
    return path


def repo_root(path: Path) -> Path:
    result = git(["rev-parse", "--show-toplevel"], path)
    if result.returncode != 0:
        raise GitError(f"not a git repository: {path}")
    return Path(result.stdout.strip()).resolve()


def current_head(cwd: Path) -> str:
    return git_checked(["rev-parse", "HEAD"], cwd).stdout.strip()


def current_branch(cwd: Path) -> str:
    result = git(["branch", "--show-current"], cwd)
    return result.stdout.strip() if result.returncode == 0 else ""


def status_porcelain(cwd: Path) -> str:
    return git_checked(["status", "--porcelain=v1"], cwd).stdout


def changed_files(cwd: Path) -> list[str]:
    result = git_checked(["status", "--porcelain=v1"], cwd)
    files: list[str] = []
    for line in result.stdout.splitlines():
        if not line:
            continue
        # Porcelain path starts at col 3. Rename uses "old -> new"; keep new.
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        files.append(path)
    return sorted(set(files))


def diff_binary(cwd: Path, *args: str) -> str:
    return git_checked(["diff", "--binary", *args], cwd).stdout


def diff_name_only(cwd: Path, base: str, ref: str = "HEAD") -> list[str]:
    result = git_checked(["diff", "--name-only", base, ref], cwd)
    return [x for x in result.stdout.splitlines() if x.strip()]


def has_uncommitted_changes(cwd: Path) -> bool:
    return bool(status_porcelain(cwd).strip())


def worktree_add(repo: Path, path: Path, branch: str, base: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    git_checked(["worktree", "add", "-B", branch, str(path), base], repo)


def worktree_remove(repo: Path, path: Path, *, force: bool = True) -> CommandResult:
    args = ["worktree", "remove"]
    if force:
        args.append("--force")
    args.append(str(path))
    return git(args, repo)


def branch_delete(repo: Path, branch: str, *, force: bool = True) -> CommandResult:
    return git(["branch", "-D" if force else "-d", branch], repo)


def commit_all(cwd: Path, message: str) -> str | None:
    if not has_uncommitted_changes(cwd):
        return None
    git_checked(["add", "-A"], cwd)
    env = os.environ.copy()
    env.setdefault("GIT_AUTHOR_NAME", "cursor-fleet")
    env.setdefault("GIT_AUTHOR_EMAIL", "cursor-fleet@example.invalid")
    env.setdefault("GIT_COMMITTER_NAME", "cursor-fleet")
    env.setdefault("GIT_COMMITTER_EMAIL", "cursor-fleet@example.invalid")
    result = run_cmd(["git", "commit", "-m", message], cwd, env=env)
    if result.returncode != 0:
        raise GitError(result.stderr.strip() or "git commit failed")
    return current_head(cwd)


def merge_branch(cwd: Path, branch: str) -> CommandResult:
    return git(["merge", "--no-ff", "--no-edit", branch], cwd)


def conflicted_files(cwd: Path) -> list[str]:
    result = git_checked(["diff", "--name-only", "--diff-filter=U"], cwd)
    return [x for x in result.stdout.splitlines() if x.strip()]


def finish_merge_commit(cwd: Path) -> str:
    git_checked(["add", "-A"], cwd)
    result = git(["commit", "--no-edit"], cwd)
    if result.returncode != 0:
        raise GitError(result.stderr.strip() or "git commit --no-edit failed")
    return current_head(cwd)


def apply_patch(cwd: Path, patch_file: Path, *, three_way: bool = True) -> CommandResult:
    args = ["apply", "--whitespace=nowarn"]
    if three_way:
        args.append("--3way")
    args.append(str(patch_file))
    return git(args, cwd)


def list_repo_areas(repo: Path) -> list[str]:
    preferred: list[str] = []
    for parent_name in ("apps", "packages", "services", "libs", "crates", "cmd", "internal", "src"):
        parent = repo / parent_name
        if parent.is_dir():
            children = [child for child in parent.iterdir() if child.is_dir() and not child.name.startswith(".")]
            if children and parent_name not in {"src", "internal"}:
                preferred.extend(str(child.relative_to(repo)) for child in sorted(children))
            else:
                preferred.append(parent_name)
    if preferred:
        return sorted(dict.fromkeys(preferred))

    ignore = {".git", ".codex", ".cursor", ".cursor-fleet", "node_modules", "dist", "build", "target", ".venv", "venv", "__pycache__"}
    dirs = [p.name for p in repo.iterdir() if p.is_dir() and p.name not in ignore and not p.name.startswith(".")]
    if dirs:
        return sorted(dirs)
    return ["."]

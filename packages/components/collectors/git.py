from __future__ import annotations

import subprocess
from pathlib import Path

from packages.schemas.events import ActivityEvent


class GitCollector:
    name = "git"

    def __init__(self, cwd: str | Path = ".") -> None:
        self.cwd = Path(cwd)

    def collect(self) -> list[ActivityEvent]:
        if not self._is_git_repo():
            return []

        branch = self._run_git("branch", "--show-current") or "detached"
        repo_path = str(self._repo_root() or self.cwd.resolve())
        events = [
            ActivityEvent(
                source="git",
                type="git.diff_snapshot",
                payload={
                    "branch": branch,
                    "repo_path": repo_path,
                    **self._diff_counts(),
                },
                metadata={"collector": self.name, "collector_version": "1"},
            )
        ]

        commit = self._latest_commit(branch, repo_path)
        if commit:
            events.append(commit)
        return events

    def _latest_commit(self, branch: str, repo_path: str) -> ActivityEvent | None:
        output = self._run_git("log", "-1", "--pretty=format:%H%x1f%s%x1f%aI")
        if not output:
            return None
        commit_hash, message, author_time = output.split("\x1f", 2)
        return ActivityEvent(
            source="git",
            type="git.commit",
            payload={
                "hash": commit_hash,
                "message": message,
                "author_time": author_time,
                "branch": branch,
                "repo_path": repo_path,
            },
            metadata={"collector": self.name, "collector_version": "1"},
        )

    def _diff_counts(self) -> dict[str, int]:
        status = self._run_git("status", "--porcelain")
        lines = [line for line in status.splitlines() if line.strip()]
        staged = sum(1 for line in lines if len(line) >= 1 and line[0] not in (" ", "?"))
        unstaged = sum(1 for line in lines if len(line) >= 2 and line[1] not in (" ", "?"))
        untracked = sum(1 for line in lines if line.startswith("??"))
        return {
            "changed_file_count": len(lines),
            "staged_count": staged,
            "unstaged_count": unstaged,
            "untracked_count": untracked,
        }

    def _repo_root(self) -> Path | None:
        output = self._run_git("rev-parse", "--show-toplevel")
        return Path(output) if output else None

    def _is_git_repo(self) -> bool:
        return bool(self._run_git("rev-parse", "--is-inside-work-tree"))

    def _run_git(self, *args: str) -> str:
        try:
            completed = subprocess.run(
                ["git", *args],
                cwd=self.cwd,
                check=False,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            return ""
        if completed.returncode != 0:
            return ""
        return completed.stdout.strip()

"""Publish ONLY the two image paths to 'output', in an isolated temporary repo.

This is an optional caller step, never part of image generation. No force pushes,
no checkout of the caller's worktree, no credentials written to git config.
"""

from __future__ import annotations

import argparse
import base64
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ASSETS = ("git-ship.gif", "git-ship.png")


def publish(assets: Path, remote: str, default_branch: str, token: str = "") -> bool:
    if not default_branch or default_branch == "output":
        raise ValueError("refusing publication: output must not be the default branch")
    content = {}
    for name in ASSETS:
        source = assets / name
        if not source.is_file() or source.stat().st_size > 8_000_000:
            raise ValueError(f"missing or oversized generated asset: {name}")
        content[name] = source.read_bytes()
    env = os.environ.copy()
    env.update(
        {
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_AUTHOR_NAME": "github-actions[bot]",
            "GIT_COMMITTER_NAME": "github-actions[bot]",
            "GIT_AUTHOR_EMAIL": "41898282+github-actions[bot]@users.noreply.github.com",
            "GIT_COMMITTER_EMAIL": "41898282+github-actions[bot]@users.noreply.github.com",
        }
    )
    if token:
        encoded = base64.b64encode(f"x-access-token:{token}".encode()).decode()
        env.update(
            {
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_KEY_0": "http.https://github.com/.extraheader",
                "GIT_CONFIG_VALUE_0": f"AUTHORIZATION: basic {encoded}",
            }
        )
    with tempfile.TemporaryDirectory(prefix="git-ship-publish-") as scratch:
        root = Path(scratch)

        def git(*args: str, accepted: tuple[int, ...] = (0,)) -> subprocess.CompletedProcess[str]:
            proc = subprocess.run(["git", *args], cwd=root, env=env, text=True, capture_output=True)
            if proc.returncode not in accepted:
                # Raw git stderr may include authenticated HTTP details; omit it.
                raise RuntimeError(
                    f"git {args[0]} failed (exit {proc.returncode}); check contents:write, "
                    "output branch rules and concurrent updates. No default branch was changed."
                )
            return proc

        git("init", "-b", "output")
        git("remote", "add", "origin", remote)
        exists = git("ls-remote", "--exit-code", "origin", "refs/heads/output", accepted=(0, 2))
        if exists.returncode == 0:
            git("fetch", "--depth=1", "origin", "refs/heads/output")
            git("checkout", "-B", "output", "FETCH_HEAD")
        for name, data in content.items():
            target = root / name
            if target.is_symlink() or target.is_dir():
                raise ValueError(f"refusing to replace non-file output branch path: {name}")
            target.write_bytes(data)
        git("add", "--", *ASSETS)
        changed = git("diff", "--cached", "--quiet", accepted=(0, 1)).returncode == 1
        if not changed:
            return False
        git("commit", "-m", "Refresh Git Ship assets")
        git("push", "origin", "HEAD:refs/heads/output")
        return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets-dir", type=Path, required=True)
    parser.add_argument("--repository", required=True, help="owner/repository")
    parser.add_argument("--default-branch", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repository):
        parser.error("repository must have owner/repository syntax")
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        parser.error("publishing requires GITHUB_TOKEN with contents:write")
    try:
        changed = publish(
            args.assets_dir, f"https://github.com/{args.repository}.git", args.default_branch, token
        )
        print("Published assets to output." if changed else "Assets unchanged; no commit created.")
        return 0
    except (ValueError, OSError, RuntimeError) as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

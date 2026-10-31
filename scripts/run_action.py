"""Actual composite-action entry point; tested locally with the same input env."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from git_ship.cli import main
from git_ship.config import DATA_WINDOWS, load_config


def run() -> int:
    try:
        workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
        output = (workspace / os.environ.get("SHIP_OUTPUT_DIR", "git-ship-output")).resolve()
        if not output.is_relative_to(workspace) or output == workspace:
            raise ValueError("output-dir must be a subdirectory inside the caller workspace")
        config_value = os.environ.get("SHIP_CONFIG", "")
        config_path = (workspace / config_value).resolve() if config_value else None
        if config_path and not config_path.is_relative_to(workspace):
            raise ValueError("config must be inside the caller workspace")
        demo = os.environ.get("SHIP_DEMO", "false").lower()
        if demo not in ("true", "false"):
            raise ValueError("demo must be true or false")
        args = ["render", "--output-dir", str(output)]
        data_window = os.environ.get("SHIP_DATA_WINDOW", "").strip().lower()
        if data_window:
            if data_window not in DATA_WINDOWS:
                raise ValueError("data-window must be day, week or month")
            args += ["--data-window", data_window]
        if config_path:
            args += ["--config", str(config_path)]
        if demo == "true":
            args.append("--demo")
        else:
            username = os.environ.get("SHIP_USERNAME")
            if not username:
                username = load_config(config_path).username or os.environ["SHIP_REPOSITORY_OWNER"]
            args += ["--username", username]
        code = main(args)
        if code:
            print("::error::Git Ship generation failed; see the diagnostic above.", file=sys.stderr)
            return code
        values = {
            "gif": str(output / "git-ship.gif"),
            "png": str(output / "git-ship.png"),
            "output-dir": str(output),
            "publish-script": str(Path(__file__).resolve().with_name("publish_assets.py")),
        }
        if any("\n" in v or "\r" in v for v in values.values()):
            raise ValueError("action paths cannot contain newlines")
        with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as stream:
            for key, value in values.items():
                stream.write(f"{key}={value}\n")
        return 0
    except (KeyError, ValueError, OSError) as exc:
        print(f"::error::Git Ship action configuration: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run())

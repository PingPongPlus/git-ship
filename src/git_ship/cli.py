"""Command-line entry point; the demo path cannot initiate network calls."""

from __future__ import annotations

import argparse
import json
import os
import sys
from importlib.resources import as_file, files
from pathlib import Path

from . import __version__
from .config import DATA_WINDOWS, load_config
from .export import export
from .github import GitHubClient, GitHubError
from .layout import layout
from .model import Profile, rank_languages
from .preview import write_preview


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="git-ship", description="Your languages, a little fleet.")
    root.add_argument("--version", action="version", version=f"git-ship {__version__}")
    render = root.add_subparsers(dest="command", required=True).add_parser("render")
    source = render.add_mutually_exclusive_group()
    source.add_argument("--demo", action="store_true", help="render the fixed offline demo")
    source.add_argument(
        "--profile", type=Path, help="render a cached normalized JSON profile offline"
    )
    render.add_argument("--username", help="GitHub user (overrides config)")
    render.add_argument("--config", type=Path, help="TOML configuration")
    render.add_argument("--output-dir", type=Path, default=Path("out"))
    render.add_argument("--cache-profile", type=Path, help="save normalized credential-free data")
    render.add_argument(
        "--preview", action="store_true", help="write contact sheet and local HTML preview"
    )
    render.add_argument("--observation-date", help="fixed UTC observation date, YYYY-MM-DD")
    render.add_argument("--seed")
    render.add_argument(
        "--lighthouse-beam",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="enable or disable the rotating lighthouse ray",
    )
    render.add_argument(
        "--watermark",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="enable or disable the project and activity-period watermark",
    )
    window = render.add_mutually_exclusive_group()
    window.add_argument("--activity-window", type=int, help="rolling activity window in days")
    presets = ", ".join(f"{name} ({days})" for name, days in DATA_WINDOWS.items())
    window.add_argument(
        "--data-window", choices=DATA_WINDOWS, help=f"rolling period in days: {presets}"
    )
    for name in ("ships", "scale", "fps", "duration"):
        render.add_argument(f"--{name}", type=int)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        keys = (
            "username",
            "ships",
            "scale",
            "fps",
            "duration",
            "activity_window",
            "seed",
            "lighthouse_beam",
            "watermark",
            "observation_date",
        )
        overrides = {k: getattr(args, k) for k in keys}
        if args.data_window:
            overrides["activity_window"] = DATA_WINDOWS[args.data_window]
        config = load_config(args.config, overrides)
        if args.demo:
            with as_file(files("git_ship").joinpath("assets/demo.json")) as path:
                profile = Profile.read(path)
        elif args.profile:
            profile = Profile.read(args.profile)
        else:
            profile = GitHubClient(os.environ.get("GITHUB_TOKEN")).fetch(config)
        if (
            (args.demo or args.profile)
            and config.username
            and config.username.casefold() != profile.username.casefold()
        ):
            raise ValueError(
                "offline profile username differs from configured username; omit --username"
            )
        for warning in profile.warnings:
            print(f"git-ship: warning: {warning}", file=sys.stderr)
        if args.cache_profile:
            profile.write(args.cache_profile)
        scene = layout(profile, config)
        if config.ships and any(
            language.cargo is None for language in rank_languages(profile, config)
        ):
            print(
                "git-ship: warning: cached commit data does not cover this fleet/window; "
                "ships with unknown activity are omitted. Fetch a fresh profile to populate them.",
                file=sys.stderr,
            )
        report, frames = export(scene, config, args.output_dir)
        if args.preview:
            write_preview(args.output_dir, frames, config.duration)
        print(json.dumps({"output_dir": str(args.output_dir.resolve()), **report}, indent=2))
        if report["gif_bytes"] >= 2_000_000:
            print(
                "git-ship: GIF exceeds the 2 MB target; try a smaller scale or frame rate",
                file=sys.stderr,
            )
        return 0
    except (ValueError, OSError, GitHubError) as exc:
        # Do not include request objects, headers, raw responses or credentials.
        message = str(exc)
        token = os.environ.get("GITHUB_TOKEN")
        if token:
            message = message.replace(token, "[redacted]")
        print(f"git-ship: {message}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

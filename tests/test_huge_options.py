import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from git_ship.cli import main
from git_ship.config import Config
from git_ship.model import commit_filter_signature

ROOT = Path(__file__).resolve().parents[1]


def write_config(path, enabled):
    path.write_text(
        "scale = 1\nduration = 2\nfps = 5\nseed = 'huge-options'\nactivity_window = 1\n"
        "lighthouse_beam = false\nwatermark = false\n"
        f"huge_cargo_ship = {str(enabled).lower()}\n"
    )


def assert_mode(report, enabled):
    assert report["huge_cargo_ship"] is enabled
    assert report["activity_window_days"] == 30
    assert report["decoded_frames_match"]
    if enabled:
        assert report["mode"] == "huge-cargo-ship"
        assert report["languages"] == []
        assert report["commits_per_large_container"] == 6
        assert report["total_commits"] == 44
        assert report["large_containers"] == 7 and report["small_containers"] == 2
        assert report["huge_ship"] is not None
    else:
        assert report["mode"] == "fleet"
        assert report["commits_per_large_container"] == 4
        assert [language["cargo"] for language in report["languages"]] == [7, 20, 6, 4, 5, 2]


@pytest.mark.parametrize("enabled", (False, True))
def test_cli_huge_flag_overrides_opposite_toml_setting_for_month(tmp_path, capsys, enabled):
    config = tmp_path / "ship.toml"
    write_config(config, not enabled)
    assert (
        main(
            [
                "render",
                "--demo",
                "--config",
                str(config),
                "--huge-cargo-ship" if enabled else "--no-huge-cargo-ship",
                "--data-window",
                "month",
                "--output-dir",
                str(tmp_path / "fleet"),
            ]
        )
        == 0
    )
    assert_mode(json.loads(capsys.readouterr().out), enabled)
    assert (tmp_path / "fleet/git-ship.gif").is_file()


def action(tmp_path, huge, configured):
    config = tmp_path / "ship.toml"
    write_config(config, configured)
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_action.py")],
        env={
            **os.environ,
            "GITHUB_WORKSPACE": str(tmp_path),
            "GITHUB_OUTPUT": str(tmp_path / "outputs"),
            "GITHUB_TOKEN": "",
            "SHIP_OUTPUT_DIR": "fleet",
            "SHIP_CONFIG": config.name,
            "SHIP_DEMO": "true",
            "SHIP_USERNAME": "",
            "SHIP_REPOSITORY_OWNER": "sailor",
            "SHIP_DATA_WINDOW": "month",
            "SHIP_LIGHTHOUSE_BEAM": "false",
            "SHIP_WATERMARK": "false",
            "SHIP_HUGE_CARGO_SHIP": huge,
        },
        text=True,
        capture_output=True,
    )


@pytest.mark.parametrize(
    "huge,configured,expected",
    [("true", False, True), ("false", True, False), ("", True, True), ("", False, False)],
)
def test_action_huge_input_overrides_or_preserves_toml(tmp_path, huge, configured, expected):
    proc = action(tmp_path, huge, configured)
    assert proc.returncode == 0, proc.stderr
    assert_mode(json.loads(proc.stdout), expected)
    assert "png=" in (tmp_path / "outputs").read_text()


@pytest.mark.parametrize("huge", ("yes", "1"))
def test_action_rejects_invalid_huge_input_before_rendering(tmp_path, huge):
    proc = action(tmp_path, huge, False)
    assert proc.returncode == 1
    assert "huge-cargo-ship must be true or false" in proc.stderr
    assert not (tmp_path / "fleet/git-ship.gif").exists()


@pytest.mark.parametrize("aggregate_cache", (False, True))
def test_cli_refuses_caches_without_the_coverage_needed_for_the_selected_mode(
    demo, tmp_path, capsys, aggregate_cache
):
    if aggregate_cache:
        profile = replace(
            demo,
            commit_coverage="complete-metadata",
            cargo_window=30,
            observed_at="2026-10-01T23:59:59.999999Z",
            commit_filters=commit_filter_signature(Config()),
        )
    else:
        profile = replace(demo, commit_coverage="sampled-language")
    path = tmp_path / "profile.json"
    profile.write(path)
    assert (
        main(
            [
                "render",
                "--profile",
                str(path),
                "--no-huge-cargo-ship" if aggregate_cache else "--huge-cargo-ship",
                "--output-dir",
                str(tmp_path / "fleet"),
            ]
        )
        == 1
    )
    error = capsys.readouterr().err
    assert "fetch a fresh" in error
    assert ("aggregate-only data" if aggregate_cache else "complete history") in error
    assert not (tmp_path / "fleet/git-ship.gif").exists()

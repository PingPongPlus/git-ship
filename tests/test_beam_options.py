import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from git_ship.cli import main

ROOT = Path(__file__).resolve().parents[1]


def action(tmp_path, beam, configured=False, window="month"):
    config = tmp_path / "ship.toml"
    config.write_text(
        f"scale = 1\nduration = 2\nfps = 5\nlighthouse_beam = {str(configured).lower()}\n"
    )
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
            "SHIP_DATA_WINDOW": window,
            "SHIP_LIGHTHOUSE_BEAM": beam,
        },
        text=True,
        capture_output=True,
    )


@pytest.mark.parametrize("enabled", [False, True])
def test_cli_beam_flag_overrides_toml(tmp_path, capsys, enabled):
    config = tmp_path / "ship.toml"
    config.write_text(f"lighthouse_beam = {str(not enabled).lower()}\n")
    assert (
        main(
            [
                "render",
                "--demo",
                "--config",
                str(config),
                "--lighthouse-beam" if enabled else "--no-lighthouse-beam",
                "--scale",
                "1",
                "--duration",
                "2",
                "--fps",
                "5",
                "--output-dir",
                str(tmp_path / "fleet"),
            ]
        )
        == 0
    )
    report = json.loads(capsys.readouterr().out)
    assert report["lighthouse_beam"] is enabled
    assert (tmp_path / "fleet/git-ship.gif").is_file()


@pytest.mark.parametrize(
    "beam,configured,expected", [("true", False, True), ("false", True, False), ("", False, False)]
)
def test_action_beam_input_overrides_toml_and_empty_input_preserves_it(
    tmp_path, beam, configured, expected
):
    proc = action(tmp_path, beam, configured)
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["lighthouse_beam"] is expected
    assert "gif=" in (tmp_path / "outputs").read_text()


@pytest.mark.parametrize("beam", ["yes", "1"])
def test_invalid_action_beam_input_reports_clear_error_without_rendering(tmp_path, beam):
    proc = action(tmp_path, beam)
    assert proc.returncode == 1
    assert "lighthouse-beam must be true or false" in proc.stderr
    assert not (tmp_path / "fleet/git-ship.gif").exists()


def test_action_accepts_year_window_with_beam_enabled(tmp_path):
    proc = action(tmp_path, "true", window="year")
    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["activity_window_days"] == 365
    assert report["lighthouse_beam"] is True
    assert (tmp_path / "fleet/git-ship.png").is_file()

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from git_ship.cli import main

ROOT = Path(__file__).resolve().parents[1]
MONTH_LABEL = "Git Ship — commits from the past month"


def action(tmp_path, watermark, configured):
    config = tmp_path / "ship.toml"
    config.write_text(
        "scale = 1\nduration = 2\nfps = 5\nactivity_window = 1\n"
        f"watermark = {str(configured).lower()}\n"
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
            "SHIP_DATA_WINDOW": "month",
            "SHIP_LIGHTHOUSE_BEAM": "false",
            "SHIP_WATERMARK": watermark,
        },
        text=True,
        capture_output=True,
    )


@pytest.mark.parametrize("enabled", [False, True])
def test_cli_watermark_flag_overrides_toml_with_selected_month_label(tmp_path, capsys, enabled):
    config = tmp_path / "ship.toml"
    config.write_text(
        f"watermark = {str(not enabled).lower()}\nactivity_window = 1\nlighthouse_beam = false\n"
    )
    assert (
        main(
            [
                "render",
                "--demo",
                "--config",
                str(config),
                "--watermark" if enabled else "--no-watermark",
                "--data-window",
                "month",
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
    assert report["watermark"] is enabled
    assert report["watermark_text"] == (MONTH_LABEL if enabled else None)
    assert report["activity_window_days"] == 30
    assert (tmp_path / "fleet/git-ship.gif").is_file()


@pytest.mark.parametrize(
    "watermark,configured,expected",
    [("true", False, True), ("false", True, False), ("", False, False), ("", True, True)],
)
def test_action_watermark_override_and_omitted_input_preserve_beam_setting(
    tmp_path, watermark, configured, expected
):
    proc = action(tmp_path, watermark, configured)
    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["watermark"] is expected
    assert report["watermark_text"] == (MONTH_LABEL if expected else None)
    assert report["activity_window_days"] == 30
    assert report["lighthouse_beam"] is False
    assert "gif=" in (tmp_path / "outputs").read_text()


@pytest.mark.parametrize("watermark", ["yes", "1"])
def test_invalid_action_watermark_reports_clear_error_without_rendering(tmp_path, watermark):
    proc = action(tmp_path, watermark, False)
    assert proc.returncode == 1
    assert "watermark must be true or false" in proc.stderr
    assert not (tmp_path / "fleet/git-ship.gif").exists()

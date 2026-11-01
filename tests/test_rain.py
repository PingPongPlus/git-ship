import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest
from PIL import Image, ImageChops, ImageDraw

from git_ship.animation import Animator
from git_ship.cli import main
from git_ship.config import Config, load_config
from git_ship.export import export
from git_ship.layout import layout
from git_ship.rain import Drop, blocked_water, draw_rain, impact, rain_drops

ROOT = Path(__file__).resolve().parents[1]


def test_impact_art_matches_approved_preview_stages():
    with Image.open(ROOT / "artwork/rain/impact-stages.png") as approved:
        for index, age in enumerate((0, 0.12, 0.3, 0.5, 0.72, 0.9)):
            tile = Image.new("RGBA", (17, 9))
            impact(ImageDraw.Draw(tile), 8, 4, age)
            assert tile.tobytes() == approved.crop((index * 17, 0, (index + 1) * 17, 9)).tobytes()


def test_falling_drop_ends_at_its_own_impact_then_clears():
    blank = Image.new("RGBA", (400, 160))
    drops = (Drop(100, 120, 0),)
    falling = draw_rain(blank, drops, 0.66 / 5)
    assert falling.getbbox()[3] <= 120
    splash = draw_rain(blank, drops, 0.68 / 5)
    assert splash.getbbox() == (99, 119, 102, 121)
    ripple = draw_rain(blank, drops, 0.82 / 5)
    left, top, right, bottom = ripple.getbbox()
    assert right - left > 3 and top >= 119 and bottom <= 122
    assert draw_rain(blank, drops, 0.98 / 5).getbbox() is None
    assert draw_rain(blank, (), 0.5).getbbox() is None


@pytest.mark.parametrize("huge", (False, True))
@pytest.mark.parametrize("seed", range(6))
def test_seeded_rain_impacts_stay_in_open_water_and_do_not_change_cargo_or_positions(
    demo, huge, seed
):
    dry = Config(seed=seed, huge_cargo_ship=huge, display_commits=True)
    wet = replace(dry, rain=True)
    scene = layout(demo, wet)
    assert scene == layout(demo, dry)
    drops = rain_drops(scene)
    assert len(drops) == 44 and drops == rain_drops(scene)
    blocked = blocked_water(scene)
    for drop in drops:
        assert 10 <= drop.x <= 389 and 91 <= drop.y <= 149
        assert blocked.crop((drop.x - 6, drop.y - 2, drop.x + 7, drop.y + 2)).getbbox() is None
    assert len(set(drops)) > 40


@pytest.mark.parametrize("huge", (False, True))
def test_rain_leaves_all_ship_lighthouse_and_caption_pixels_intact_and_loops(demo, huge):
    config = Config(
        seed="rain-occlusion",
        scale=1,
        huge_cargo_ship=huge,
        display_commits=True,
        lighthouse_beam=False,
        rain=True,
    )
    wet = Animator(layout(demo, config), config)
    dry_config = replace(config, rain=False)
    dry = Animator(layout(demo, dry_config), dry_config)
    for step in range(40):
        t = step / 40
        background, actual = dry.frame(t), wet.frame(t)
        mask = background.getchannel("A")
        diff = ImageChops.difference(background.convert("RGB"), actual.convert("RGB"))
        assert not ImageChops.multiply(diff, mask.convert("RGB")).getbbox()
        alpha_diff = ImageChops.difference(mask, actual.getchannel("A"))
        assert not ImageChops.multiply(alpha_diff, mask).getbbox()
        assert set(actual.getchannel("A").tobytes()) == {0, 255}
    assert wet.frame(0).tobytes() == wet.frame(1).tobytes()
    assert wet.frame(-0.25).tobytes() == wet.frame(0.75).tobytes()
    assert wet.frame(0).tobytes() != dry.frame(0).tobytes()


def test_rain_off_preserves_the_existing_demo_image_exactly(demo):
    config = Config(seed="demo")
    frame = Animator(layout(demo, config), config).frame(0)
    with Image.open(ROOT / "examples/demo/git-ship.png") as original:
        assert frame.tobytes() == original.convert("RGBA").tobytes()


@pytest.mark.parametrize("huge", (False, True))
def test_rainy_gif_keeps_exact_transparency_beam_cargo_and_quiet_scene(tmp_path, demo, huge):
    config = Config(
        rain=True,
        huge_cargo_ship=huge,
        cargo_logos=huge,
        seed="rain-export",
        scale=1,
        fps=5,
        duration=2,
        activity_window=1,
    )
    scene = layout(demo, config)
    report, frames = export(scene, config, tmp_path)
    assert report["rain"] and report["decoded_frames_match"]
    assert report["frames"] == 10 and report["languages"] == []
    assert scene.huge_ship is None and not scene.ships
    assert any(f.getchannel("A").getbbox() for f in frames)
    assert Animator(scene, config).frame(0).tobytes() == Animator(scene, config).frame(1).tobytes()


@pytest.mark.parametrize("enabled", (False, True))
def test_cli_rain_flag_overrides_toml(tmp_path, capsys, enabled):
    config = tmp_path / "ship.toml"
    config.write_text(f"rain = {str(not enabled).lower()}\nscale = 1\nfps = 5\nduration = 2\n")
    assert (
        main(
            [
                "render",
                "--demo",
                "--config",
                str(config),
                "--rain" if enabled else "--no-rain",
                "--output-dir",
                str(tmp_path / "fleet"),
            ]
        )
        == 0
    )
    report = json.loads(capsys.readouterr().out)
    assert report["rain"] is enabled and report["decoded_frames_match"]


@pytest.mark.parametrize(
    "value,configured,expected",
    [
        ("true", False, True),
        ("false", True, False),
        ("", True, True),
        ("", False, False),
        ("yes", False, None),
    ],
)
def test_action_rain_input_overrides_or_preserves_toml(tmp_path, value, configured, expected):
    config = tmp_path / "ship.toml"
    config.write_text(f"rain = {str(configured).lower()}\nscale = 1\nfps = 5\nduration = 2\n")
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_action.py")],
        env={
            **os.environ,
            "GITHUB_TOKEN": "",
            "GITHUB_WORKSPACE": str(tmp_path),
            "GITHUB_OUTPUT": str(tmp_path / "outputs"),
            "SHIP_OUTPUT_DIR": "fleet",
            "SHIP_CONFIG": config.name,
            "SHIP_DEMO": "true",
            "SHIP_RAIN": value,
        },
        text=True,
        capture_output=True,
    )
    if expected is None:
        assert result.returncode == 1 and "rain must be true or false" in result.stderr
        assert not (tmp_path / "fleet/git-ship.gif").exists()
    else:
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout)["rain"] is expected


def test_rain_defaults_off_and_requires_a_real_boolean(tmp_path):
    assert not Config().rain
    config = tmp_path / "ship.toml"
    config.write_text("rain = true\n")
    assert load_config(config).rain
    for invalid in ("true", 1, None):
        with pytest.raises(ValueError, match="rain must be true or false"):
            Config(rain=invalid)

import json
import os
import subprocess
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path

import pytest

from git_ship.animation import Animator
from git_ship.cargo_art import container
from git_ship.cli import main
from git_ship.config import Config, load_config
from git_ship.export import export
from git_ship.huge_ship import (
    cargo_stack_offset,
    huge_cargo_counts,
    huge_ship_sprite,
    language_cargo_plan,
)
from git_ship.layout import layout
from git_ship.model import Commit, Repository
from git_ship.rain import blocked_water

ROOT = Path(__file__).resolve().parents[1]


def with_counts(demo, counts):
    commits = []
    for name, count in counts:
        for _ in range(count):
            commits.append(
                Commit(f"{len(commits) + 1:040x}", demo.username, "2026-09-30T12:00:00Z", (name,))
            )
    repository = Repository(
        "stack", demo.username, False, False, None, dict.fromkeys(dict(counts), 100), tuple(commits)
    )
    return replace(demo, repositories=(repository,))


@pytest.mark.parametrize("total", (0, 1, 5, 6, 179, 180, 185, 186, 191, 216, 601, 6000))
def test_endless_counts_show_every_commit_and_grow_by_whole_tiers(total):
    limited = huge_cargo_counts(total)
    counts = huge_cargo_counts(total, endless_cargo=True)
    assert counts["visible_large"] == total // 6
    assert counts["visible_small"] == total % 6
    assert counts["overflow_commits"] == 0
    assert counts["visible_large"] * 6 + counts["visible_small"] == total
    assert limited["visible_large"] <= 30
    tiers = (total // 6 + 5) // 6
    assert cargo_stack_offset(total, endless_cargo=True) == max(0, tiers - 5) * 10
    assert cargo_stack_offset(total) == 0


def test_language_packing_preserves_all_weights_beyond_old_capacity():
    counts = (("Java", 247), ("Go", 122), ("Lua", 41), ("TypeScript", 13))
    total = sum(n for _, n in counts)
    plan = language_cargo_plan(total, counts, endless_cargo=True)
    recovered = Counter()
    for box in plan["large"] + plan["small"]:
        recovered.update(box["languages"])
    assert recovered == dict(counts)
    assert len(plan["large"]) == total // 6 > 30
    assert len(plan["small"]) == total % 6
    assert plan["overflow_commits"] == 0
    assert any(box["label"] == "Mixed" for box in plan["large"])


@pytest.mark.parametrize("logos", (False, True))
def test_tall_ship_exports_without_clipping_and_keeps_ocean_effects_aligned(demo, tmp_path, logos):
    profile = with_counts(demo, (("C", 601),))
    config = Config(
        huge_cargo_ship=True,
        endless_cargo=True,
        cargo_logos=logos,
        rain=True,
        seed="endless",
        scale=1,
        fps=5,
        duration=2,
    )
    scene = layout(profile, config)
    animator = Animator(scene, config)
    assert animator.vertical_offset == 120
    assert animator.huge_sprite.size == (300, 230)
    assert animator.frame(0).size == (400, 280)
    assert animator.frame(0).tobytes() == animator.frame(1).tobytes()
    if logos:
        assert animator.huge_sprite.crop((72, 26, 99, 36)).tobytes() == container("C").tobytes()
    # Rain lands in the translated sea, outside the moving hull and lighthouse.
    blocked = blocked_water(scene, vertical_offset=120)
    assert len(animator.rain_drops) == 44
    for drop in animator.rain_drops:
        assert 211 <= drop.y <= 269
        assert blocked.crop((drop.x - 6, drop.y - 2, drop.x + 7, drop.y + 2)).getbbox() is None
    # The sea and lighthouse retain their exact geometry at the new baseline.
    dry = Animator(scene, replace(config, rain=False, lighthouse_beam=False, watermark=False))
    limited = Animator(
        scene,
        replace(config, endless_cargo=False, rain=False, lighthouse_beam=False, watermark=False),
    )
    assert (
        dry.frame(0).crop((0, 120, 70, 280)).tobytes()
        == limited.frame(0).crop((0, 0, 70, 160)).tobytes()
    )
    report, frames = export(scene, config, tmp_path)
    assert report["endless_cargo"] and report["decoded_frames_match"]
    assert report["height"] == 280 and report["cargo_tiers"] == 17
    assert report["displayed_large_containers"] == 100
    assert report["displayed_small_containers"] == 1
    assert report["overflow_commits"] == 0
    assert report["cargo_commits"] == report["total_commits"] == 601
    assert report["huge_ship"]["height"] == 230
    assert len(frames) == 10
    if logos:
        assert len(report["cargo_containers"]["large"]) == 100


def test_disabled_option_and_fleet_mode_preserve_existing_pixels(demo):
    assert not Config().endless_cargo
    for total in (0, 1, 44, 180, 185):
        assert (
            huge_ship_sprite(total).tobytes()
            == huge_ship_sprite(total, endless_cargo=True).tobytes()
        )
    profile = with_counts(demo, (("Go", 601),))
    normal = Config(huge_cargo_ship=True, seed="off", scale=1)
    scene = layout(profile, normal)
    assert (
        Animator(scene, normal).frame(0).tobytes()
        == Animator(scene, replace(normal, endless_cargo=False)).frame(0).tobytes()
    )
    assert Animator(scene, normal).frame(0).size == (400, 160)
    fleet = Config(seed="fleet", scale=1)
    assert (
        Animator(layout(demo, fleet), fleet).frame(0).tobytes()
        == Animator(layout(demo, fleet), replace(fleet, endless_cargo=True)).frame(0).tobytes()
    )


def test_tall_canvas_budget_is_checked_before_sprite_or_plan_allocation(
    demo, monkeypatch, tmp_path
):
    config = Config(huge_cargo_ship=True, endless_cargo=True)
    scene = layout(demo, config)
    scene = replace(
        scene,
        total_commits=6000,
        authored_commits=6000,
        huge_ship=replace(scene.huge_ship, total_commits=6000),
    )

    def unexpected(*args, **kwargs):
        raise AssertionError("must validate the actual canvas before drawing")

    monkeypatch.setattr("git_ship.animation.huge_ship_sprite", unexpected)
    with pytest.raises(ValueError, match="80 million frame-pixels"):
        Animator(scene, config)
    saved = {name: b"previous asset" for name in ("git-ship.gif", "git-ship.png", "report.json")}
    for name, content in saved.items():
        (tmp_path / name).write_bytes(content)
    with pytest.raises(ValueError, match="80 million frame-pixels"):
        export(scene, config, tmp_path)
    assert {name: (tmp_path / name).read_bytes() for name in saved} == saved
    with pytest.raises(ValueError, match="GIF dimensions"):
        huge_ship_sprite(999999999, endless_cargo=True)
    with pytest.raises(ValueError, match="GIF dimensions"):
        language_cargo_plan(999999999, (("Java", 999999999),), endless_cargo=True)


@pytest.mark.parametrize("value", (None, 1, "true"))
def test_endless_option_requires_an_actual_boolean(value):
    with pytest.raises(ValueError, match="endless_cargo must be true or false"):
        Config(endless_cargo=value)


@pytest.mark.parametrize("enabled", (None, False, True))
def test_cli_and_toml_endless_option_precedence(demo, tmp_path, capsys, enabled):
    profile = tmp_path / "profile.json"
    with_counts(demo, (("Go", 601),)).write(profile)
    settings = tmp_path / "ship.toml"
    settings.write_text(
        "scale = 1\nfps = 5\nduration = 2\nhuge_cargo_ship = true\n"
        f"endless_cargo = {str(enabled is not True).lower()}\n"
    )
    assert load_config(settings).endless_cargo is (enabled is not True)
    args = [
        "render",
        "--profile",
        str(profile),
        "--config",
        str(settings),
        "--output-dir",
        str(tmp_path / "out"),
    ]
    if enabled is not None:
        args.append("--endless-cargo" if enabled else "--no-endless-cargo")
    assert main(args) == 0
    report = json.loads(capsys.readouterr().out)
    expected = enabled is not False
    assert report["endless_cargo"] is expected
    assert report["height"] == (280 if expected else 160)
    assert report["overflow_commits"] == (0 if expected else 420)


@pytest.mark.parametrize(
    "value,configured,expected",
    (
        ("true", False, True),
        ("false", True, False),
        ("", True, True),
        ("", False, False),
        ("yes", False, None),
    ),
)
def test_action_endless_input_overrides_or_preserves_toml(tmp_path, value, configured, expected):
    settings = tmp_path / "ship.toml"
    settings.write_text(
        "scale = 1\nfps = 5\nduration = 2\nhuge_cargo_ship = true\n"
        f"endless_cargo = {str(configured).lower()}\n"
    )
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_action.py")],
        env={
            **os.environ,
            "GITHUB_WORKSPACE": str(tmp_path),
            "GITHUB_OUTPUT": str(tmp_path / "outputs"),
            "SHIP_CONFIG": settings.name,
            "SHIP_OUTPUT_DIR": "out",
            "SHIP_DEMO": "true",
            "SHIP_ENDLESS_CARGO": value,
        },
        text=True,
        capture_output=True,
    )
    if expected is None:
        assert proc.returncode == 1
        assert "endless-cargo must be true or false" in proc.stderr
        assert not (tmp_path / "out/git-ship.gif").exists()
    else:
        assert proc.returncode == 0, proc.stderr
        assert json.loads(proc.stdout)["endless_cargo"] is expected

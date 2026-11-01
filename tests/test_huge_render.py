from dataclasses import replace
from datetime import date

import pytest

from git_ship.animation import Animator
from git_ship.config import Config
from git_ship.export import export
from git_ship.layout import HugeShip, Scene, layout
from git_ship.model import Commit, Profile, Repository


def profile_with_total(total):
    records = tuple(
        Commit(f"{number:040x}", "sailor", "2026-09-30T12:00:00Z", ("Java", "Python"))
        for number in range(total)
    )
    repository = Repository("code", "sailor", False, False, None, {"Java": 100}, records)
    return Profile(
        "sailor",
        date(2026, 10, 1),
        (repository,),
        commit_coverage="complete-language",
    )


@pytest.mark.parametrize("total", [0, 1, 5, 6, 20, 44, 185, 186, 197])
def test_huge_replaces_every_language_ship_and_keeps_uncapped_unique_totals(total):
    config = Config(huge_cargo_ship=True, seed="aggregate", ships=0)
    scene = layout(profile_with_total(total), config)
    assert scene.ships == ()
    assert scene.total_commits == total
    assert (scene.huge_ship is not None) == (total > 0)
    if scene.huge_ship:
        assert scene.huge_ship.total_commits == total
    assert scene == layout(profile_with_total(total), config)


def test_huge_gif_has_exact_totals_overflow_and_a_seamless_calm_loop(tmp_path):
    config = Config(huge_cargo_ship=True, seed="overflow", scale=1, duration=2)
    scene = layout(profile_with_total(197), config)
    report, frames = export(scene, config, tmp_path)
    assert report["mode"] == "huge-cargo-ship" and report["huge_cargo_ship"]
    assert report["languages"] == []
    assert report["total_commits"] == 197
    assert report["commits_per_large_container"] == 6
    assert (report["large_containers"], report["small_containers"]) == (32, 5)
    assert (report["displayed_large_containers"], report["displayed_small_containers"]) == (30, 5)
    assert report["overflow_commits"] == 12
    assert 30 * 6 + 5 + report["overflow_commits"] == report["total_commits"]
    assert report["decoded_frames_match"] and report["min_transparent_fraction"] > 0.45
    animator = Animator(scene, config)
    assert animator.frame(0).tobytes() == animator.frame(1).tobytes()
    assert len({frame.tobytes() for frame in frames}) > 10
    for frame in frames:
        assert set(frame.getchannel("A").tobytes()) == {0, 255}


def test_quiet_huge_mode_remains_a_lighthouse_only_scene(tmp_path):
    config = Config(huge_cargo_ship=True, scale=1, duration=2)
    report, _ = export(layout(profile_with_total(0), config), config, tmp_path)
    assert report["total_commits"] == 0 and report["huge_ship"] is None
    assert report["large_containers"] == report["small_containers"] == 0
    assert report["overflow_commits"] == 0
    assert report["decoded_frames_match"]


def test_complete_metadata_cache_cannot_masquerade_as_a_language_fleet(demo):
    metadata = replace(demo, commit_coverage="complete-metadata")
    with pytest.raises(ValueError, match="aggregate-only.*fresh profile"):
        layout(metadata, Config())


def test_huge_sprite_wake_and_mooring_fit_canvas_for_many_seeds():
    for seed in range(30):
        config = Config(
            huge_cargo_ship=True, seed=seed, scale=1, lighthouse_beam=False, watermark=False
        )
        scene = layout(profile_with_total(197), config)
        animator = Animator(scene, config)
        for step in range(20):
            frame = animator.frame(step / 20)
            # Every occupied pixel stays away from all four image edges.
            left, top, right, bottom = frame.getbbox()
            assert 0 < left < right < 400
            assert 0 < top < bottom < 160


@pytest.mark.parametrize(
    "scene,config",
    [
        (Scene("sailor", (), 0), Config(huge_cargo_ship=True)),
        (Scene("sailor", (), 0, huge_ship=HugeShip(6, 80, 35, 0)), Config()),
        (Scene("sailor", (), 0, total_commits=6), Config(huge_cargo_ship=True)),
        (
            Scene("sailor", (), 0, huge_ship=HugeShip(5, 80, 35, 0), total_commits=6),
            Config(huge_cargo_ship=True),
        ),
    ],
)
def test_inconsistent_mode_or_commit_scene_is_rejected(scene, config):
    with pytest.raises(ValueError):
        Animator(scene, config)

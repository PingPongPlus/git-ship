import random
from dataclasses import replace
from datetime import UTC, datetime
from itertools import combinations

import pytest

from git_ship.animation import Animator
from git_ship.config import HEIGHT, MAX_SHIPS, WIDTH, Config
from git_ship.export import export
from git_ship.github import GitHubClient
from git_ship.layout import layout, placements
from git_ship.model import Commit, Profile, Repository

NAMES = ("Java", "C++", "Python", "Rust", "JavaScript", "TypeScript", "Go", "Ruby")


def active_profile(count=8, cargo=1):
    languages = {name: (len(NAMES) - i) * 1000 for i, name in enumerate(NAMES[:count])}
    commits = tuple(
        Commit(f"{i * 100 + j + 1:040x}", "sailor", "2026-09-30T18:00:00Z", (name,))
        for i, name in enumerate(languages)
        for j in range(cargo)
    )
    repo = Repository("one", "sailor", False, False, None, languages, commits)
    return Profile(
        "sailor", datetime(2026, 10, 1).date(), (repo,), observed_at="2026-10-01T03:23:00Z"
    )


def test_quiet_and_unknown_languages_do_not_appear(demo):
    assert layout(demo, Config(activity_window=1)).ships == ()
    week = layout(demo, Config(activity_window=7))
    assert {ship.language.name for ship in week.ships} == {
        "Java",
        "C++",
        "JavaScript",
        "TypeScript",
    }
    assert all(ship.language.cargo > 0 for ship in week.ships)
    unknown = replace(
        demo, repositories=tuple(replace(repo, commits=None) for repo in demo.repositories)
    )
    assert layout(unknown, Config()).ships == ()


def test_filter_before_limit_and_never_show_more_than_six():
    profile = active_profile()
    scene = layout(profile, Config())
    assert len(scene.ships) == MAX_SHIPS == 6
    assert [ship.language.name for ship in scene.ships] == list(NAMES[:6])
    assert len(layout(profile, Config(ships=2)).ships) == 2
    only_low_ranked = replace(
        profile.repositories[0],
        commits=(Commit(f"{999:040x}", profile.username, "2026-09-30T18:00:00Z", ("Ruby",)),),
    )
    scene = layout(replace(profile, repositories=(only_low_ranked,)), Config(ships=1))
    assert [ship.language.name for ship in scene.ships] == ["Ruby"]


def test_live_fetch_discovers_activity_below_inactive_high_byte_languages(monkeypatch):
    client = GitHubClient()
    profile = active_profile(cargo=0)
    profile = replace(profile, repositories=(replace(profile.repositories[0], commits=None),))
    observed = datetime(2026, 10, 1, 3, 23, tzinfo=UTC)
    sha = f"{42:040x}"

    def request(path, body=None):
        if "/commits?" in path:
            return [
                {
                    "sha": sha,
                    "author": {"login": profile.username},
                    "commit": {"committer": {"date": "2026-09-30T18:00:00Z"}},
                }
            ], {}
        return {"sha": sha, "files": [{"filename": "lib/example.rb"}]}, {}

    monkeypatch.setattr(client, "request", request)
    config = Config(ships=1, activity_window=1)
    loaded = replace(profile, repositories=client.load_cargo(profile, config, observed))
    assert [ship.language.name for ship in layout(loaded, config).ships] == ["Ruby"]


def test_new_layout_per_render_and_reported_seed_replays_the_whole_scene(demo, monkeypatch):
    seeds = iter(("a" * 32, "b" * 32))
    monkeypatch.setattr("git_ship.layout.secrets.token_hex", lambda _: next(seeds))
    first, second = layout(demo, Config()), layout(demo, Config())
    assert first.layout_seed != second.layout_seed
    assert [(s.x, s.y) for s in first.ships] != [(s.x, s.y) for s in second.ships]
    replay = layout(demo, Config(seed=first.layout_seed))
    assert replay == first
    assert (
        Animator(first, Config()).frame(0.37).tobytes()
        == Animator(replay, Config()).frame(0.37).tobytes()
    )


def test_explicit_seed_is_repeatable_and_not_rechosen_for_animation_frames(demo, monkeypatch):
    def forbidden(*args):
        raise AssertionError("unexpected per-frame or explicitly seeded randomness")

    monkeypatch.setattr("git_ship.layout.secrets.token_hex", forbidden)
    config = Config(seed="repeatable")
    scene = layout(demo, config)
    assert layout(demo, config) == scene
    animator = Animator(scene, config)
    assert animator.frame(0).tobytes() == animator.frame(1).tobytes()
    assert animator.frame(0.5).tobytes() == animator.frame(0.5).tobytes()


def test_placements_use_the_whole_sea_instead_of_fixed_rows(demo):
    positions = [layout(demo, Config(ships=1, seed=i)).ships[0] for i in range(50)]
    assert max(ship.x for ship in positions) - min(ship.x for ship in positions) > 200
    assert max(ship.y for ship in positions) - min(ship.y for ship in positions) > 70
    assert len({ship.y for ship in positions}) > 20


def test_dense_fallback_fits_six_maximum_width_motion_envelopes():
    class CrowdedRandom(random.Random):
        def randint(self, a, b):
            # Force every free-placement retry to collide at the same corner.
            return a

    positions = placements([62] * 6, CrowdedRandom(42))
    boxes = [(x - 8, y - 2, x + 70, y + 63) for x, y in positions]
    assert len(boxes) == 6
    for left, top, right, bottom in boxes:
        assert 70 < left < right < WIDTH
        assert 0 <= top < bottom < HEIGHT
    for a, b in combinations(boxes, 2):
        assert a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1]


@pytest.mark.parametrize("count", range(7))
def test_full_motion_envelopes_fit_and_remain_disjoint_across_many_layouts(count):
    profile = active_profile(count=count, cargo=20)
    for seed in range(20):
        ships = layout(profile, Config(seed=seed)).ships
        assert len(ships) == count
        # Conservative envelopes include every hull, label, cargo, mast, smoke,
        # wake and the largest allowed bob/drift across the complete loop.
        boxes = [(s.x - 8, s.y - 2, s.x + s.width + 8, s.y + 63) for s in ships]
        for left, top, right, bottom in boxes:
            assert 70 < left < right < WIDTH
            assert 0 <= top < bottom < HEIGHT
        for a, b in combinations(boxes, 2):
            assert a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1]


@pytest.mark.parametrize("beam", [False, True])
def test_six_fully_loaded_ships_keep_transparency_and_exact_gif_cleanup(tmp_path, beam):
    config = Config(seed="six-full-ships", scale=1, duration=2, lighthouse_beam=beam)
    scene = layout(active_profile(count=6, cargo=20), config)
    report, _ = export(scene, config, tmp_path)
    assert len(report["languages"]) == 6
    assert all(language["cargo"] == 20 for language in report["languages"])
    assert report["min_transparent_fraction"] > (0.7 if beam else 0.8)
    assert report["decoded_frames_match"]
    assert report["layout_seed"] == config.seed

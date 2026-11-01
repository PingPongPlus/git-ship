import json
import os
import random
import subprocess
import sys
from dataclasses import replace
from datetime import date
from itertools import combinations
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from PIL import Image

from git_ship.animation import Animator
from git_ship.cli import main
from git_ship.config import Config, load_config
from git_ship.github import GitHubClient
from git_ship.layout import layout, placements
from git_ship.model import Profile, aggregate_commits, rank_languages
from git_ship.watermark import COMMIT_FOOTER_HEIGHT, commit_label, draw_commit_total

ROOT = Path(__file__).resolve().parents[1]


def test_fleet_counter_fetches_complete_total_without_changing_capped_language_sample(
    monkeypatch, tmp_path
):
    client = GitHubClient()
    config = Config(
        username="sailor",
        display_commits=True,
        observation_date=date(2026, 10, 1),
        include_non_code=True,
    )
    calls = []

    def item(number):
        return {
            "sha": f"{number:040x}",
            "author": {"login": "sailor"},
            "commit": {"committer": {"date": "2026-09-30T18:00:00Z"}},
        }

    def request(path, body=None):
        calls.append(path)
        if path == "/users/sailor":
            return {"type": "User"}, {}
        if path.startswith("/users/sailor/repos?"):
            return [
                {
                    "name": name,
                    "owner": {"login": "sailor"},
                    "fork": False,
                    "archived": False,
                    "pushed_at": None,
                }
                for name in ("code", "docs")
            ], {}
        parsed = urlparse(path)
        if parsed.path.endswith("/languages"):
            return ({"Java": 200, "Python": 100} if "/code/" in path else {}), {}
        if parsed.path.endswith("/commits"):
            if "/docs/" in path:
                return [item(1), item(31)], {}
            if parse_qs(parsed.query).get("page") == ["2"]:
                return [item(i) for i in range(26, 31)], {}
            return [item(i) for i in range(1, 26)], {
                "link": '<https://api.github.com/repos/sailor/code/commits?page=2>; rel="next"'
            }
        return {
            "sha": path.split("/")[-1].split("?")[0],
            "files": [{"filename": "Main.java"}, {"filename": "main.py"}],
        }, {}

    monkeypatch.setattr(client, "request", request)
    profile = client.fetch(config)
    assert [language.cargo for language in rank_languages(profile, config)] == [20, 20]
    assert len(profile.repositories[0].commits) == 20
    assert profile.repositories[1].commits is None
    assert profile.commit_total == aggregate_commits(profile, config) == 31
    assert any("page=2" in path for path in calls)
    path = tmp_path / "profile.json"
    profile.write(path)
    assert aggregate_commits(Profile.read(path), config) == 31
    for changes in ({"activity_window": 7}, {"exclude": ("docs",)}, {"include_forks": True}):
        with pytest.raises(ValueError, match="fetch a fresh"):
            aggregate_commits(profile, replace(config, **changes))


@pytest.mark.parametrize("total", (0, 1, 44, 123456))
def test_counter_right_alignment_singular_plural_and_binary_alpha(total):
    image = Image.new("RGBA", (400, 160))
    draw_commit_total(image, total)
    left, top, right, bottom = image.getbbox()
    assert left > 250 and top == 149 and right == 396 and bottom == 157
    assert commit_label(total) == ("1 COMMIT" if total == 1 else f"{total} COMMITS")
    assert set(image.getchannel("A").tobytes()) == {0, 255}


@pytest.mark.parametrize("seed", range(12))
def test_counter_reserves_space_and_stays_readable_over_the_moving_ray(demo, seed):
    config = Config(seed=seed, scale=1, display_commits=True)
    scene = layout(demo, config)
    assert scene.fleet_commits == 44
    assert len(scene.ships) == 6
    assert all(ship.y + 63 < 160 - COMMIT_FOOTER_HEIGHT for ship in scene.ships)
    animator = Animator(scene, config)
    expected = Image.new("RGBA", (400, 160))
    draw_commit_total(expected, 44)
    mask = expected.getchannel("A")
    for t in (0, 0.25, 0.6):
        rendered = Image.new("RGBA", expected.size)
        rendered.paste(animator.frame(t), mask=mask)
        assert rendered.tobytes() == expected.tobytes()
    assert animator.frame(0).tobytes() == animator.frame(1).tobytes()


def test_dense_fallback_fits_header_footer_and_disjoint_motion_envelopes():
    class CrowdedRandom(random.Random):
        def randint(self, a, b):
            return a

    positions = placements([62] * 6, CrowdedRandom(42), 14, COMMIT_FOOTER_HEIGHT)
    boxes = [(x - 8, y - 2, x + 70, y + 63) for x, y in positions]
    assert all(top >= 14 and bottom < 148 for _, top, _, bottom in boxes)
    for a, b in combinations(boxes, 2):
        assert a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1]


def test_counter_requires_complete_total_and_huge_mode_keeps_existing_hull_total(demo):
    assert layout(demo, Config()).fleet_commits is None
    with pytest.raises(ValueError, match="complete history"):
        layout(replace(demo, commit_coverage="sampled-language"), Config(display_commits=True))
    config = Config(huge_cargo_ship=True, display_commits=True)
    scene = layout(demo, config)
    assert scene.fleet_commits is None and scene.total_commits == 44
    Animator(scene, config)


def test_zero_commits_display_without_watermark_or_ships(demo):
    config = Config(display_commits=True, watermark=False, activity_window=1, scale=1)
    scene = layout(demo, config)
    assert scene.fleet_commits == 0 and not scene.ships
    frame = Animator(scene, config).frame(0)
    expected = Image.new("RGBA", frame.size)
    draw_commit_total(expected, 0)
    assert frame.crop((330, 148, 400, 160)) == expected.crop((330, 148, 400, 160))


def test_cached_total_requires_valid_count_and_scope(demo, tmp_path):
    path = tmp_path / "profile.json"
    demo.write(path)
    raw = json.loads(path.read_text())
    for value in (-1, True, "44", 4.5):
        with pytest.raises(ValueError, match="commit_total"):
            Profile.from_dict({**raw, "commit_total": value})
    with pytest.raises(ValueError, match="requires its window, instant and filters"):
        Profile.from_dict({**raw, "commit_total": 44})


@pytest.mark.parametrize("enabled", (False, True))
def test_cli_counter_flag_overrides_toml_and_exports_exact_total(tmp_path, capsys, enabled):
    config = tmp_path / "ship.toml"
    config.write_text(
        f"scale = 1\nduration = 2\nfps = 5\ndisplay_commits = {str(not enabled).lower()}\n"
    )
    assert (
        main(
            [
                "render",
                "--demo",
                "--config",
                str(config),
                "--display-commits" if enabled else "--no-display-commits",
                "--output-dir",
                str(tmp_path / "fleet"),
            ]
        )
        == 0
    )
    report = json.loads(capsys.readouterr().out)
    assert report["display_commits"] is enabled
    assert report["commit_counter_text"] == ("44 COMMITS" if enabled else None)
    if enabled:
        assert report["total_commits"] == 44
    assert report["decoded_frames_match"]


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
def test_action_counter_input_overrides_or_preserves_config(tmp_path, value, configured, expected):
    config = tmp_path / "ship.toml"
    config.write_text(
        f"scale = 1\nduration = 2\nfps = 5\ndisplay_commits = {str(configured).lower()}\n"
    )
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_action.py")],
        env={
            **os.environ,
            "GITHUB_WORKSPACE": str(tmp_path),
            "GITHUB_TOKEN": "",
            "GITHUB_OUTPUT": str(tmp_path / "outputs"),
            "SHIP_OUTPUT_DIR": "fleet",
            "SHIP_CONFIG": config.name,
            "SHIP_DEMO": "true",
            "SHIP_DISPLAY_COMMITS": value,
        },
        text=True,
        capture_output=True,
    )
    if expected is None:
        assert proc.returncode == 1 and "display-commits must be true or false" in proc.stderr
    else:
        assert proc.returncode == 0, proc.stderr
        assert json.loads(proc.stdout)["display_commits"] is expected


def test_counter_defaults_off_and_requires_boolean_toml(tmp_path):
    assert not Config().display_commits
    path = tmp_path / "ship.toml"
    path.write_text("display_commits = true\n")
    assert load_config(path).display_commits
    with pytest.raises(ValueError, match="display_commits must be true or false"):
        Config(display_commits="true")

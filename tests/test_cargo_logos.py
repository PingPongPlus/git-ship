import json
import os
import subprocess
import sys
from collections import Counter
from dataclasses import replace
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import pytest
from PIL import Image, ImageChops, ImageDraw

from git_ship.animation import Animator
from git_ship.cargo_art import STYLES, container
from git_ship.cli import main
from git_ship.config import Config, load_config
from git_ship.export import export
from git_ship.github import GitHubClient
from git_ship.huge_ship import huge_ship_sprite, language_cargo_plan
from git_ship.layout import layout
from git_ship.model import Commit, Profile, Repository, aggregate_languages

ROOT = Path(__file__).resolve().parents[1]


def test_full_language_boxes_mixed_remainders_and_exact_small_weights():
    counts = (("Java", 13), ("Python", 10), ("JavaScript", 3), ("Git", 1))
    plan = language_cargo_plan(27, counts)
    assert [box["label"] for box in plan["large"]] == ["Java", "Java", "Python", "Mixed"]
    assert plan["large"][-1]["languages"] == {"Java": 1, "Python": 4, "JavaScript": 1}
    recovered = Counter()
    for box in plan["large"] + plan["small"]:
        recovered.update(box["languages"])
    assert recovered == dict(counts)
    assert sum(box["commits"] for box in plan["large"] + plan["small"]) == 27
    assert plan["overflow_commits"] == 0


@pytest.mark.parametrize("total", (0, 1, 5, 6, 7, 179, 180, 185, 186, 197, 999999999))
def test_grouping_capacity_and_overflow_are_bounded_and_exact(total):
    for counts in ((("Java", total),), (("Java", total // 2), ("Python", total - total // 2))):
        plan = language_cargo_plan(total, counts)
        assert len(plan["large"]) <= 30 and len(plan["small"]) < 6
        assert all(box["commits"] == 6 for box in plan["large"])
        assert all(box["commits"] == 1 for box in plan["small"])
        assert len(plan["large"]) * 6 + len(plan["small"]) + plan["overflow_commits"] == total


def test_many_languages_with_only_remainders_still_pack_exactly():
    plan = language_cargo_plan(203, tuple((f"Language{i}", 1) for i in range(203)))
    assert len(plan["large"]) == 30 and len(plan["small"]) == 5
    assert plan["overflow_commits"] == 18
    assert all(box["label"] == "Mixed" for box in plan["large"])


@pytest.mark.parametrize(
    "counts", ((("Java", 5),), (("Java", 3), ("Java", 3)), (("Java", True),), (("", 6),))
)
def test_invalid_language_weights_are_rejected(counts):
    with pytest.raises(ValueError, match="language counts"):
        language_cargo_plan(6, counts)


def test_approved_container_pixels_and_ship_geometry():
    with Image.open(ROOT / "artwork/huge-ship/language-containers.png") as approved:
        for index, name in enumerate(STYLES):
            assert (
                container(name).tobytes()
                == approved.crop((27 * index, 0, 27 * (index + 1), 10)).tobytes()
            )
    counts = tuple((name, 6) for name in STYLES)
    actual = huge_ship_sprite(36, counts)
    original = huge_ship_sprite(36)
    mask = Image.new("L", actual.size, 255)
    ImageDraw.Draw(mask).rectangle((72, 26, 239, 75), fill=0)
    diff = ImageChops.difference(actual, original)
    assert not ImageChops.multiply(diff, mask.convert("RGBA")).getbbox(alpha_only=False)
    assert set(actual.getchannel("A").tobytes()) == {0, 255}
    for name in ("Mixed", "TypeScript", "HTML", "C#", "Go", "Unknown Language"):
        assert container(name).size == (27, 10)


def test_classified_history_deduplicates_across_repos_and_counts_docs_once(demo):
    observed = "2026-09-30T12:00:00Z"
    commits = (
        Commit("1" * 40, demo.username, observed, ("Java", "Python")),
        Commit("2" * 40, demo.username, observed, ()),
        Commit("3" * 40, "other", observed, ("Rust",)),
        Commit("4" * 40, demo.username, "2024-01-01T00:00:00Z", ("Rust",)),
    )
    repo = Repository("code", demo.username, False, False, None, {"Java": 100}, commits)
    profile = replace(demo, repositories=(repo, replace(repo, name="copy")))
    assert dict(aggregate_languages(profile, Config())) == {"Git": 1, "Java": 1}
    for coverage in ("sampled-language", "complete-metadata"):
        with pytest.raises(ValueError, match="fresh"):
            layout(
                replace(profile, commit_coverage=coverage),
                Config(huge_cargo_ship=True, cargo_logos=True),
            )


def test_primary_changed_language_uses_all_pages_lines_and_stable_ties(monkeypatch):
    client = GitHubClient()
    calls = []

    def request(path, body=None):
        calls.append(path)
        if "page=2" in path:
            return {"sha": "a" * 40, "files": [{"filename": "more.py", "changes": 20}]}, {}
        return {
            "sha": "a" * 40,
            "files": [
                {"filename": "Main.java", "changes": 10},
                {"filename": "main.py", "changes": 1},
            ],
        }, {"link": '<https://api.github.com/repos/a/b/commits/aaa?page=2>; rel="next"'}

    monkeypatch.setattr(client, "request", request)
    available = {"Java": 1000, "Python": 10}
    assert client.changed_languages("/repos/a/b", "a" * 40, available, primary_only=True) == (
        "Python",
    )
    assert len(calls) == 2
    assert client.changed_languages("/repos/a/b", "a" * 40, available) == ("Java", "Python")
    monkeypatch.setattr(
        client,
        "request",
        lambda *a: (
            {
                "sha": "a" * 40,
                "files": [
                    {"filename": "main.py", "changes": 10},
                    {"filename": "Main.java", "changes": 10},
                ],
            },
            {},
        ),
    )
    assert client.changed_languages("/repos/a/b", "a" * 40, available, primary_only=True) == (
        "Java",
    )


def test_live_logo_scan_is_complete_uncapped_and_cache_marks_primary_coverage(
    monkeypatch, tmp_path
):
    client = GitHubClient()
    config = Config(
        username="sailor",
        huge_cargo_ship=True,
        cargo_logos=True,
        observation_date=date(2026, 10, 1),
    )
    calls = []

    def item(i):
        return {
            "sha": f"{i:040x}",
            "author": {"login": "sailor"},
            "commit": {"committer": {"date": "2026-09-30T12:00:00Z"}},
        }

    def request(path, body=None):
        calls.append(path)
        if path == "/users/sailor":
            return {"type": "User"}, {}
        if path.startswith("/users/sailor/repos?"):
            return [
                {
                    "name": n,
                    "owner": {"login": "sailor"},
                    "fork": False,
                    "archived": False,
                    "pushed_at": None,
                }
                for n in ("code", "docs")
            ], {}
        if path.endswith("/languages"):
            return ({"Java": 100, "Python": 1} if "/code/" in path else {}), {}
        if urlparse(path).path.endswith("/commits"):
            if "/docs/" in path:
                return [item(1), item(31)], {}
            if "page=2" in path:
                return [item(i) for i in range(26, 31)], {}
            return [item(i) for i in range(1, 26)], {
                "link": '<https://api.github.com/repos/sailor/code/commits?page=2>; rel="next"'
            }
        sha = urlparse(path).path.split("/")[-1]
        return {
            "sha": sha,
            "files": [
                {"filename": "Main.java", "changes": 9},
                {"filename": "main.py", "changes": 1},
            ],
        }, {}

    monkeypatch.setattr(client, "request", request)
    profile = client.fetch(config)
    assert profile.commit_coverage == "complete-primary-language"
    assert dict(aggregate_languages(profile, config)) == {"Java": 30, "Git": 1}
    assert len(profile.repositories[0].commits) == 30
    assert len([path for path in calls if "/commits/" in path]) == 30
    path = tmp_path / "profile.json"
    profile.write(path)
    assert Profile.read(path) == profile
    with pytest.raises(ValueError, match="aggregate-only"):
        layout(profile, replace(config, huge_cargo_ship=False))
    with pytest.raises(ValueError, match="fetch a fresh"):
        aggregate_languages(profile, replace(config, activity_window=7))


def test_logo_render_exact_export_and_disable_preserve_old_mode(demo, tmp_path):
    config = Config(huge_cargo_ship=True, cargo_logos=True, seed="logos", scale=1, duration=2)
    scene = layout(demo, config)
    report, frames = export(scene, config, tmp_path)
    assert report["cargo_logos"] is True and report["decoded_frames_match"]
    assert sum(report["cargo_languages"].values()) == report["total_commits"] == 44
    assert len(report["cargo_containers"]["large"]) == 7
    assert len(report["cargo_containers"]["small"]) == 2
    assert Animator(scene, config).frame(0).tobytes() == Animator(scene, config).frame(1).tobytes()
    off = replace(config, cargo_logos=False)
    assert layout(demo, off).cargo_languages is None
    assert frames[0].tobytes() != Animator(layout(demo, off), off).frame(0).tobytes()
    assert layout(demo, Config(cargo_logos=True, seed="same")) == layout(demo, Config(seed="same"))


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
def test_action_logo_input_and_toml(tmp_path, value, configured, expected):
    config = tmp_path / "ship.toml"
    config.write_text(
        "huge_cargo_ship = true\nscale = 1\nduration = 2\nfps = 5\n"
        f"cargo_logos = {str(configured).lower()}\n"
    )
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_action.py")],
        env={
            **os.environ,
            "GITHUB_TOKEN": "",
            "GITHUB_WORKSPACE": str(tmp_path),
            "GITHUB_OUTPUT": str(tmp_path / "outputs"),
            "SHIP_CONFIG": config.name,
            "SHIP_OUTPUT_DIR": "fleet",
            "SHIP_DEMO": "true",
            "SHIP_CARGO_LOGOS": value,
        },
        text=True,
        capture_output=True,
    )
    if expected is None:
        assert result.returncode == 1 and "cargo-logos must be true or false" in result.stderr
    else:
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout)["cargo_logos"] is expected


@pytest.mark.parametrize("enabled", (False, True))
def test_cli_logo_overrides_toml(tmp_path, capsys, enabled):
    config = tmp_path / "ship.toml"
    config.write_text(
        "huge_cargo_ship = true\nscale = 1\nduration = 2\nfps = 5\n"
        f"cargo_logos = {str(not enabled).lower()}\n"
    )
    assert (
        main(
            [
                "render",
                "--demo",
                "--config",
                str(config),
                "--cargo-logos" if enabled else "--no-cargo-logos",
                "--output-dir",
                str(tmp_path / "out"),
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["cargo_logos"] is enabled


def test_logo_option_validates_boolean_and_defaults_off(tmp_path):
    assert not Config().cargo_logos
    path = tmp_path / "ship.toml"
    path.write_text("cargo_logos = true\n")
    assert load_config(path).cargo_logos
    with pytest.raises(ValueError, match="cargo_logos must be true or false"):
        Config(cargo_logos=1)

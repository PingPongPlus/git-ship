import json
import os
import subprocess
import sys
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from git_ship.cli import main
from git_ship.config import Config, load_config
from git_ship.github import GitHubClient
from git_ship.languages import DATA, is_programming
from git_ship.layout import layout
from git_ship.model import (
    Commit,
    Profile,
    Repository,
    aggregate_commits,
    aggregate_languages,
    rank_languages,
)

ROOT = Path(__file__).resolve().parents[1]


def mixed_profile():
    records = tuple(
        Commit(f"{i:040x}", "sailor", "2026-09-30T12:00:00Z", names)
        for i, names in enumerate(
            (
                (),
                ("Markdown",),
                ("YAML",),
                ("JSON",),
                ("SVG",),
                ("Java",),
                ("Shell",),
                ("Markdown", "Python"),
            ),
            1,
        )
    )
    repo = Repository(
        "code",
        "sailor",
        False,
        False,
        None,
        {"Markdown": 1000, "Java": 20, "Shell": 10, "Python": 10},
        records,
    )
    return Profile(
        "sailor",
        date(2026, 10, 1),
        (repo, replace(repo, name="duplicate")),
        commit_coverage="complete-language",
    )


def test_default_counts_only_programming_shas_once_in_both_huge_variants():
    profile = mixed_profile()
    assert aggregate_commits(profile, Config()) == 3
    assert dict(aggregate_languages(profile, Config())) == {"Java": 1, "Python": 1, "Shell": 1}
    for logos in (False, True):
        scene = layout(profile, Config(huge_cargo_ship=True, cargo_logos=logos))
        assert scene.total_commits == 3
    assert [lang.name for lang in rank_languages(profile, Config())] == ["Java", "Python", "Shell"]
    all_config = Config(include_non_code=True)
    assert aggregate_commits(profile, all_config) == 8
    assert sum(dict(aggregate_languages(profile, all_config)).values()) == 8
    assert any(lang.name == "Markdown" for lang in rank_languages(profile, all_config))


@pytest.mark.parametrize(
    "name", ("Java", "Python", "Shell", "PowerShell", "JavaScript", "TypeScript", "Rust", "C++")
)
def test_programming_and_scripting_types_are_included(name):
    assert is_programming(name)


@pytest.mark.parametrize(
    "name", ("Markdown", "YAML", "JSON", "TOML", "SVG", "Text", "HTML", "CSS", "Git", "Unknown")
)
def test_docs_data_markup_and_unknowns_are_excluded(name):
    assert not is_programming(name)


def test_vendored_language_categories_are_complete():
    assert all(
        spec["type"] in {"programming", "markup", "data", "prose"}
        for spec in DATA["languages"].values()
    )


def test_docs_heavy_commit_is_still_attributed_to_its_actual_code_change(monkeypatch):
    client = GitHubClient()
    monkeypatch.setattr(
        client,
        "request",
        lambda *a: (
            {
                "sha": "a" * 40,
                "files": [
                    {"filename": "README.md", "changes": 1000},
                    {"filename": "Main.java", "changes": 1},
                ],
            },
            {},
        ),
    )
    assert client.changed_languages(
        "/repos/a/b", "a" * 40, {}, primary_only=True, programming_only=True
    ) == ("Java",)
    assert client.changed_languages("/repos/a/b", "a" * 40, {}, primary_only=True) == ("Markdown",)


def test_readme_workflow_only_profile_has_no_idle_huge_ship():
    profile = mixed_profile()
    repo = replace(profile.repositories[0], commits=profile.repositories[0].commits[:5])
    scene = layout(
        replace(profile, repositories=(repo,)), Config(huge_cargo_ship=True, cargo_logos=True)
    )
    assert scene.total_commits == 0 and scene.huge_ship is None and scene.cargo_languages == ()


def test_old_all_commit_scope_is_readable_but_cannot_fake_a_programming_total(tmp_path):
    profile = replace(
        mixed_profile(),
        cargo_window=30,
        observed_at="2026-10-01T23:59:59.999999Z",
        commit_filters={
            "include_forks": False,
            "include_archived": True,
            "include": [],
            "exclude": [],
        },
        commit_total=8,
        commit_coverage="complete-file-language",
    )
    path = tmp_path / "old.json"
    profile.write(path)
    restored = Profile.read(path)
    assert restored.commit_filters["include_non_code"] is True
    with pytest.raises(ValueError, match="fetch a fresh"):
        aggregate_commits(restored, Config())
    assert aggregate_commits(restored, Config(include_non_code=True)) == 8


@pytest.mark.parametrize("all_commits", (False, True))
def test_live_plain_huge_and_fleet_totals_respect_scope_without_cargo_logos(
    monkeypatch, all_commits
):
    client = GitHubClient()
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
                    "name": "code",
                    "owner": {"login": "sailor"},
                    "fork": False,
                    "archived": False,
                    "pushed_at": None,
                }
            ], {}
        if path.endswith("/languages"):
            return {"Java": 10}, {}
        if "/commits?" in path:
            return [item(1), item(2), item(3)], {}
        sha = path.split("/")[-1].split("?")[0]
        filename = {1: "README.md", 2: "Main.java", 3: ".github/workflows/ci.yml"}[int(sha, 16)]
        return {"sha": sha, "files": [{"filename": filename, "changes": 1}]}, {}

    monkeypatch.setattr(client, "request", request)
    for huge in (False, True):
        config = Config(
            username="sailor",
            huge_cargo_ship=huge,
            display_commits=True,
            include_non_code=all_commits,
            observation_date=date(2026, 10, 1),
        )
        profile = client.fetch(config)
        assert aggregate_commits(profile, config) == (3 if all_commits else 1)
        scene = layout(profile, config)
        assert (scene.total_commits if huge else scene.fleet_commits) == (3 if all_commits else 1)


@pytest.mark.parametrize("include", (False, True))
def test_cli_non_code_override_and_toml_validation(tmp_path, capsys, include):
    profile = tmp_path / "profile.json"
    mixed_profile().write(profile)
    config = tmp_path / "ship.toml"
    config.write_text(
        f"include_non_code = {str(not include).lower()}\nscale=1\nfps=5\nduration=2\n"
    )
    assert (
        main(
            [
                "render",
                "--profile",
                str(profile),
                "--config",
                str(config),
                "--huge-cargo-ship",
                "--cargo-logos",
                "--include-non-code" if include else "--no-include-non-code",
                "--output-dir",
                str(tmp_path / "out"),
            ]
        )
        == 0
    )
    report = json.loads(capsys.readouterr().out)
    assert report["include_non_code"] is include and report["total_commits"] == (
        8 if include else 3
    )
    assert report["decoded_frames_match"]
    assert load_config(config).include_non_code is not include


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
def test_action_non_code_override(tmp_path, value, configured, expected):
    config = tmp_path / "ship.toml"
    config.write_text(f"include_non_code = {str(configured).lower()}\nscale=1\nfps=5\nduration=2\n")
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_action.py")],
        env={
            **os.environ,
            "GITHUB_WORKSPACE": str(tmp_path),
            "GITHUB_OUTPUT": str(tmp_path / "outputs"),
            "GITHUB_TOKEN": "",
            "SHIP_DEMO": "true",
            "SHIP_CONFIG": config.name,
            "SHIP_OUTPUT_DIR": "out",
            "SHIP_INCLUDE_NON_CODE": value,
        },
        text=True,
        capture_output=True,
    )
    if expected is None:
        assert proc.returncode == 1 and "include-non-code must be true or false" in proc.stderr
    else:
        assert proc.returncode == 0, proc.stderr
        assert json.loads(proc.stdout)["include_non_code"] is expected


def test_non_code_option_defaults_off_and_rejects_non_booleans():
    assert not Config().include_non_code
    with pytest.raises(ValueError, match="include_non_code must be true or false"):
        Config(include_non_code="true")

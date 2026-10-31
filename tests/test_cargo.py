import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import pytest

from git_ship.config import Config
from git_ship.github import GitHubClient, GitHubError
from git_ship.languages import file_language
from git_ship.layout import layout
from git_ship.model import Commit, Profile, Repository, rank_languages
from git_ship.sprites import language_style, ship_sprite


def commit(number, when="2026-10-01T02:00:00Z", languages=("C++",), author="sailor"):
    return Commit(f"{number:040x}", author, when, languages)


def test_distinct_authored_commits_count_once_per_language_and_cap_at_twenty():
    records = tuple(commit(i, languages=("C++", "Python", "C++")) for i in range(1, 24))
    records += (commit(100, author="someone-else"), commit(101, when="2025-01-01T00:00:00Z"))
    repo = Repository("one", "sailor", False, False, None, {"C++": 200, "Python": 100}, records)
    profile = Profile(
        "sailor",
        datetime(2026, 10, 1).date(),
        (repo, replace(repo, name="two")),
        observed_at="2026-10-01T03:23:00Z",
    )
    assert {language.name: language.cargo for language in rank_languages(profile, Config())} == {
        "C++": 20,
        "Python": 20,
    }
    fewer = replace(profile, repositories=(replace(repo, commits=records[:3] + records[:3]),))
    assert [language.cargo for language in rank_languages(fewer, Config())] == [3, 3]
    shared_history = replace(
        profile,
        repositories=(
            replace(repo, commits=records[:3]),
            replace(repo, name="copy", commits=records[:3] + (commit(99),)),
        ),
    )
    assert [language.cargo for language in rank_languages(shared_history, Config())] == [4, 3]


@pytest.mark.parametrize("days,expected", [(1, 1), (7, 2), (30, 3)])
def test_period_is_a_rolling_day_week_or_month_even_at_0323_utc(days, expected):
    observed = datetime(2026, 10, 1, 3, 23, tzinfo=UTC)
    repo = Repository(
        "one",
        "sailor",
        False,
        False,
        None,
        {"C++": 200},
        (
            commit(1, "2026-09-30T04:00:00Z"),  # Yesterday still belongs to the last 24 hours.
            commit(2, "2026-09-25T04:00:00Z"),
            commit(3, "2026-09-02T04:00:00Z"),
            commit(4, "2026-10-01T03:24:00Z"),  # Never include a future commit.
            commit(5, (observed - timedelta(days=days)).isoformat()),  # Exclude exact start.
        ),
    )
    profile = Profile(
        "sailor", datetime(2026, 10, 1).date(), (repo,), observed_at="2026-10-01T03:23:00Z"
    )
    assert rank_languages(profile, Config(activity_window=days))[0].cargo == expected


def test_old_or_different_window_cache_omits_unknown_cargo(demo, tmp_path):
    path = tmp_path / "profile.json"
    demo.write(path)
    data = json.loads(path.read_text())
    data["schema_version"] = 1
    for repo in data["repositories"]:
        repo.pop("commits")
    old = Profile.from_dict(data)
    assert all(language.cargo is None for language in rank_languages(old, Config()))
    cached = replace(demo, cargo_window=30, observed_at="2026-10-01T23:59:59.999999Z")
    assert any(
        language.cargo is None for language in rank_languages(cached, Config(activity_window=7))
    )
    assert all(language.cargo is not None for language in rank_languages(cached, Config()))


def test_file_language_matches_linguist_names_compound_suffixes_and_ambiguity():
    languages = {
        "Java": 1,
        "C++": 20,
        "C": 10,
        "Python": 1,
        "Rust": 1,
        "JavaScript": 1,
        "TypeScript": 1,
        "Shell": 1,
        "Ruby": 1,
    }
    for name, language in {
        "A.java": "Java",
        "a.cpp": "C++",
        "a.C": "C++",
        "a.h": "C++",
        "a.py": "Python",
        "a.rs": "Rust",
        "a.jsx": "JavaScript",
        "index.d.ts": "TypeScript",
        "script.sh": "Shell",
        "Gemfile": "Ruby",
    }.items():
        assert file_language(name, languages) == language
    assert file_language("image.png", languages) is None
    assert file_language("README.md", languages) is None


def test_changed_files_paginate_and_a_rename_can_affect_two_languages(monkeypatch):
    client = GitHubClient()
    sha = f"{1:040x}"
    paths = []

    def request(path, body=None):
        paths.append(path)
        if "page=2" not in path:
            return {"sha": sha, "files": [{"filename": "a.cpp"}, {"filename": "b.cpp"}]}, {
                "link": f"<https://api.github.com/repos/sailor/one/commits/{sha}?page=2>; "
                'rel="next"'
            }
        return {"sha": sha, "files": [{"filename": "moved.py", "previous_filename": "old.cpp"}]}, {}

    monkeypatch.setattr(client, "request", request)
    assert client.changed_languages("/repos/sailor/one", sha, {"C++": 20, "Python": 10}) == (
        "C++",
        "Python",
    )
    assert len(paths) == 2


def test_live_cargo_follows_commit_pages_filters_authors_and_deduplicates(monkeypatch):
    client = GitHubClient()
    repo = Repository("one", "sailor", False, False, None, {"C++": 20, "Python": 10})
    observed = datetime(2026, 10, 1, 3, 23, tzinfo=UTC)
    profile = Profile("sailor", observed.date(), (repo,), observed_at=observed.isoformat())
    calls = []

    def item(number, author="sailor"):
        return {
            "sha": f"{number:040x}",
            "author": {"login": author},
            "commit": {"committer": {"date": "2026-09-30T18:00:00Z"}},
        }

    def request(path, body=None):
        calls.append(path)
        if "page=2" in path:
            return [item(1), item(2), item(3, "other")], {}
        if "/commits?" in path:
            query = parse_qs(urlparse(path).query)
            assert query["author"] == ["sailor"]
            assert datetime.fromisoformat(query["until"][0]) == observed
            return [item(1)], {
                "link": '<https://api.github.com/repos/sailor/one/commits?page=2>; rel="next"'
            }
        sha = path.split("/commits/")[1].split("?")[0]
        return {"sha": sha, "files": [{"filename": "a.cpp"}, {"filename": "a.py"}]}, {}

    monkeypatch.setattr(client, "request", request)
    result = replace(
        profile, repositories=client.load_cargo(profile, Config(activity_window=1), observed)
    )
    assert [language.cargo for language in rank_languages(result, Config(activity_window=1))] == [
        2,
        2,
    ]
    assert len([path for path in calls if "/commits/" in path]) == 2


def test_live_scan_stops_at_twenty_cargos_without_requesting_more_pages(monkeypatch):
    client = GitHubClient()
    repo = Repository("one", "sailor", False, False, None, {"C++": 20})
    observed = datetime(2026, 10, 1, 3, 23, tzinfo=UTC)
    profile = Profile("sailor", observed.date(), (repo,), observed_at=observed.isoformat())
    details = []

    def request(path, body=None):
        if "/commits?" in path:
            assert "page=2" not in path
            return [
                {
                    "sha": f"{i:040x}",
                    "author": {"login": "sailor"},
                    "commit": {"committer": {"date": "2026-09-30T18:00:00Z"}},
                }
                for i in range(1, 26)
            ], {"link": '</commits?page=2>; rel="next"'}
        sha = path.split("/commits/")[1].split("?")[0]
        details.append(sha)
        return {"sha": sha, "files": [{"filename": "a.cpp"}]}, {}

    monkeypatch.setattr(client, "request", request)
    result = replace(profile, repositories=client.load_cargo(profile, Config(), observed))
    assert rank_languages(result, Config())[0].cargo == 20
    assert len(details) == 20


def test_github_file_limit_fails_instead_of_silently_undercounting(monkeypatch):
    client = GitHubClient()
    sha = f"{1:040x}"
    monkeypatch.setattr(
        client, "request", lambda _: ({"sha": sha, "files": [{"filename": "a.cpp"}] * 3000}, {})
    )
    with pytest.raises(GitHubError, match="3000-file"):
        client.changed_languages("/repos/a/b", sha, {"C++": 1})


@pytest.mark.parametrize("name", ["Java", "C++", "Python", "Rust", "JavaScript"])
def test_only_real_commit_cargo_occupies_the_reserved_deck_and_labels_stay_clear(name):
    style = language_style(name, Config())
    for width in (43, 53, 62):
        empty = ship_sprite(style, width, 0)
        assert empty.crop((3, 10, 20, 38)).getchannel("A").histogram()[255] == 0
        for count in (1, 7, 10, 20):
            loaded = ship_sprite(style, width, count)
            assert loaded.crop((3, 10, 20, 38)).getchannel("A").histogram()[255] == count * 20
            assert (
                loaded.crop((0, 38, width, 56)).tobytes()
                == empty.crop((0, 38, width, 56)).tobytes()
            )
    for invalid in (-1, 21, True):
        with pytest.raises(ValueError, match="cargo"):
            ship_sprite(style, 43, invalid)


def test_six_demo_ships_include_javascript_and_every_stack_matches_commits(demo):
    ships = layout(demo, Config()).ships
    assert [ship.language.name for ship in ships] == [
        "Java",
        "C++",
        "Python",
        "Rust",
        "JavaScript",
        "TypeScript",
    ]
    assert [ship.language.cargo for ship in ships] == [7, 20, 6, 4, 5, 2]

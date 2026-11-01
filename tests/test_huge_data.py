import io
import json
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse

import pytest

from git_ship.config import Config, load_config
from git_ship.github import GitHubClient, GitHubError
from git_ship.model import (
    Commit,
    Profile,
    Repository,
    aggregate_commits,
    commit_filter_signature,
    rank_languages,
)

OBSERVED = datetime(2026, 10, 1, 3, 23, tzinfo=UTC)


def commit(number, languages=(), author="sailor", when="2026-09-30T18:00:00Z"):
    return Commit(f"{number:040x}", author, when, languages)


def repo(name, commits=(), **kwargs):
    return Repository(name, "sailor", False, False, None, {}, commits, **kwargs)


def complete_profile(repositories=(), config=None):
    config = config or Config(huge_cargo_ship=True)
    return Profile(
        "sailor",
        OBSERVED.date(),
        tuple(repositories),
        observed_at=OBSERVED.isoformat(),
        cargo_window=config.activity_window,
        commit_coverage="complete-metadata",
        commit_filters=commit_filter_signature(config),
    )


def test_aggregate_deduplicates_mixed_language_and_cross_repository_shas_and_counts_docs():
    config = Config(huge_cargo_ship=True, exclude=("excluded",))
    start = OBSERVED - timedelta(days=config.activity_window)
    shared = commit(1, ("Java", "Python"))
    profile = complete_profile(
        (
            repo("code", (shared, shared, commit(2))),
            repo(
                "docs",
                (
                    shared,
                    commit(3, author="someone-else"),
                    commit(4, when=start.isoformat()),
                    commit(5, when=(OBSERVED + timedelta(seconds=1)).isoformat()),
                    commit(6, author="SAILOR", when=OBSERVED.isoformat()),
                ),
            ),
            replace(repo("foreign", None), owner="someone-else"),
            replace(repo("fork", (commit(8),)), fork=True),
            replace(repo("archive", (commit(9),)), archived=True),
            repo("excluded", (commit(10),)),
        ),
        config,
    )
    assert aggregate_commits(profile, config) == 4
    assert aggregate_commits(complete_profile(), Config(huge_cargo_ship=True)) == 0
    assert aggregate_commits(complete_profile((repo("empty"),)), Config()) == 0


def test_full_classified_fixture_supports_windows_and_selection_without_live_scope_claims(demo):
    assert demo.commit_coverage == "complete-language"
    assert demo.commit_filters is None and demo.cargo_window is None
    assert aggregate_commits(demo, Config(activity_window=1)) == 0
    assert aggregate_commits(demo, Config(activity_window=7)) == 15
    assert aggregate_commits(demo, Config(activity_window=30)) == 44
    assert aggregate_commits(demo, Config(activity_window=365)) == 44
    assert aggregate_commits(demo, Config(exclude=("harbor",))) == 17
    assert [language.cargo for language in rank_languages(demo, Config())] == [7, 20, 6, 4, 5, 2]


@pytest.mark.parametrize("schema", (1, 2))
def test_legacy_cache_never_infers_complete_aggregate_history(tmp_path, schema):
    path = tmp_path / "profile.json"
    complete_profile((repo("one", (commit(1),)),)).write(path)
    data = json.loads(path.read_text())
    data["schema_version"] = schema
    legacy = Profile.from_dict(data)
    assert legacy.commit_coverage == "sampled-language"
    assert legacy.commit_filters is None
    with pytest.raises(ValueError, match="complete history.*fetch a fresh"):
        aggregate_commits(legacy, Config())


@pytest.mark.parametrize(
    "changes",
    [
        {"activity_window": 7},
        {"observation_date": OBSERVED.date()},
        {"include": ("one",)},
        {"exclude": ("other",)},
        {"include_forks": True},
        {"include_archived": False},
        {"username": "someone-else"},
    ],
)
def test_complete_live_cache_refuses_changed_window_observation_or_selection(changes):
    profile = complete_profile((repo("one", (commit(1),)),))
    with pytest.raises(ValueError, match="fetch a fresh"):
        aggregate_commits(profile, replace(Config(), **changes))


def test_sampled_or_incomplete_profiles_cannot_return_a_plausible_partial_total():
    profile = complete_profile((repo("one", (commit(1),)),))
    for invalid in (
        replace(profile, commit_coverage="sampled-language"),
        replace(profile, repositories=(repo("one", None),)),
        replace(profile, observed_at=None),
        replace(profile, cargo_window=None),
        replace(profile, commit_filters=None),
    ):
        with pytest.raises(ValueError, match="fetch a fresh"):
            aggregate_commits(invalid, Config())


def test_metadata_only_cache_roundtrip_preserves_complete_count_without_inventing_language_counts(
    tmp_path,
):
    repository = replace(
        repo("one", tuple(commit(i, ("Java",)) for i in range(25))), languages={"Java": 100}
    )
    profile = complete_profile((repository,))
    assert aggregate_commits(profile, Config()) == 25
    assert rank_languages(profile, Config())[0].cargo is None
    path = tmp_path / "profile.json"
    profile.write(path)
    assert json.loads(path.read_text())["schema_version"] == 3
    restored = Profile.read(path)
    assert restored == profile
    assert aggregate_commits(restored, Config()) == 25
    assert "token" not in path.read_text().lower()


def test_schema_three_coverage_and_live_scope_metadata_are_validated(tmp_path):
    path = tmp_path / "profile.json"
    complete_profile().write(path)
    data = json.loads(path.read_text())
    for changes in (
        {"commit_coverage": "probably-complete"},
        {"commit_filters": {"include_forks": False}},
        {"commit_filters": {**data["commit_filters"], "include_archived": "yes"}},
        {"commit_filters": {**data["commit_filters"], "include": "one"}},
        {"cargo_window": None},
        {"observed_at": None},
    ):
        with pytest.raises(ValueError):
            Profile.from_dict({**data, **changes})


def test_huge_fetch_reads_all_metadata_pages_and_repositories_without_language_or_file_requests(
    monkeypatch,
):
    client = GitHubClient()
    config = Config(
        username="sailor", huge_cargo_ship=True, ships=0, observation_date=date(2026, 10, 1)
    )
    calls = []
    names = ("code", "docs", "archive", "extra0", "extra1", "extra2", "extra3", "extra4", "empty")

    def raw_repo(name):
        return {
            "name": name,
            "owner": {"login": "sailor"},
            "private": False,
            "fork": False,
            "archived": name == "archive",
            "pushed_at": None,
        }

    def item(number, author="sailor"):
        return {
            "sha": f"{number:040x}",
            "author": {"login": author},
            "commit": {
                "author": {"email": "123+old-username@users.noreply.github.com"},
                "committer": {"date": "2026-09-30T18:00:00Z"},
            },
        }

    def request(path, body=None):
        calls.append(path)
        if path == "/users/sailor":
            return {"type": "User"}, {}
        if path.startswith("/users/sailor/repos?"):
            return [
                *[raw_repo(name) for name in names],
                {**raw_repo("fork"), "fork": True},
                {**raw_repo("private"), "private": True},
                {**raw_repo("foreign"), "owner": {"login": "someone-else"}},
            ], {}
        parsed = urlparse(path)
        assert parsed.path.endswith("/commits"), "aggregate mode fetched languages or file details"
        query = parse_qs(parsed.query)
        assert "author" not in query
        name = parsed.path.split("/")[-2]
        if name == "code":
            if query.get("page") == ["2"]:
                return [item(26), item(27), item(28, "someone-else")], {}
            return [item(i) for i in range(1, 27)], {
                "link": '<https://api.github.com/repos/sailor/code/commits?page=2>; rel="next"'
            }
        if name == "docs":
            return [item(1), item(100)], {}
        if name == "archive":
            return [item(101)], {}
        if name == "empty":
            return [], {}
        return [item(200 + int(name[-1]))], {}

    monkeypatch.setattr(client, "request", request)
    profile = client.fetch(config)
    assert aggregate_commits(profile, config) == 34
    assert profile.commit_coverage == "complete-metadata"
    assert profile.commit_filters == commit_filter_signature(config)
    assert [repository.name for repository in profile.repositories] == list(names)
    assert all(repository.languages == {} for repository in profile.repositories)
    assert all(repository.commits is not None for repository in profile.repositories)
    assert len([path for path in calls if "/commits?" in path]) == 10


def test_huge_history_pagination_limit_fails_instead_of_returning_partial_total(monkeypatch):
    client = GitHubClient()
    profile = complete_profile((repo("one", None),))
    calls = []

    def request(path, body=None):
        calls.append(path)
        page = int(parse_qs(urlparse(path).query).get("page", ["1"])[0])
        return [], {
            "link": f'<https://api.github.com/repos/sailor/one/commits?page={page + 1}>; rel="next"'
        }

    monkeypatch.setattr(client, "request", request)
    with pytest.raises(GitHubError, match="commit pagination exceeds"):
        client.load_cargo(profile, Config(huge_cargo_ship=True), OBSERVED)
    assert len(calls) == 10


@pytest.mark.parametrize(
    "path,message,empty",
    [
        ("/repos/sailor/one/commits?per_page=100", "Git Repository is empty.", True),
        ("/repos/sailor/one/languages", "Git Repository is empty.", False),
        ("/repos/sailor/one/commits", "A different conflict.", False),
    ],
)
def test_only_an_explicit_empty_repository_commit_response_becomes_zero(
    monkeypatch, path, message, empty
):
    def request(request, timeout):
        raise HTTPError(
            request.full_url,
            409,
            "conflict",
            {},
            io.BytesIO(json.dumps({"message": message}).encode()),
        )

    monkeypatch.setattr("git_ship.github.urlopen", request)
    client = GitHubClient()
    if empty:
        assert client.request(path) == ([], {})
    else:
        with pytest.raises(GitHubError, match="HTTP 409"):
            client.request(path)


def test_huge_mode_defaults_off_and_accepts_only_booleans_in_toml(tmp_path):
    assert Config().huge_cargo_ship is False
    path = tmp_path / "ship.toml"
    path.write_text("huge_cargo_ship = true\n")
    assert load_config(path).huge_cargo_ship is True
    for invalid in ("true", 1, None):
        with pytest.raises(ValueError, match="huge_cargo_ship must be true or false"):
            Config(huge_cargo_ship=invalid)

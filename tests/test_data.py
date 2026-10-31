import json
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from git_ship.config import Config, load_config
from git_ship.model import Profile, Repository, global_activity, rank_languages


def test_ranking_and_repository_filters(demo):
    extra = (
        Repository("fork", demo.username, True, False, None, {"Ruby": 10**9}),
        Repository("other-owner", "someone-else", False, False, None, {"Shell": 10**9}),
        Repository("archive", demo.username, False, True, None, {"Go": 20}),
    )
    profile = replace(demo, repositories=demo.repositories + extra)
    config = Config(include_archived=False)
    ranked = rank_languages(profile, config)
    assert [x.name for x in ranked] == ["Java", "C++", "Python", "Rust", "JavaScript"]
    assert sum(x.share for x in ranked) == pytest.approx(1)
    assert ranked[0].activity == pytest.approx(0.95)
    assert [x.name for x in rank_languages(profile, replace(config, include=("CH*",)))] == [
        "Python"
    ]
    assert [
        x.name for x in rank_languages(profile, replace(config, exclude=("git-ship/har*",)))
    ] == ["Python", "Rust", "JavaScript"]
    assert rank_languages(profile, replace(config, include_forks=True))[0].name == "Ruby"


def test_missing_empty_and_future_data(demo):
    for languages in ({}, {"C": 0}):
        empty = replace(
            demo, repositories=(Repository("empty", demo.username, False, False, None, languages),)
        )
        assert rank_languages(empty, Config()) == ()
    repo = Repository("future", demo.username, False, False, "2027-01-01T00:00:00Z", {"C": 10})
    assert rank_languages(replace(demo, repositories=(repo,)), Config())[0].activity == 0
    assert global_activity(replace(demo, contributions=None)) == 0
    assert global_activity(replace(demo, contributions=10**9)) == 1


def test_normalized_roundtrip_and_invalid_counts(demo, tmp_path):
    path = tmp_path / "cache.json"
    demo.write(path)
    assert Profile.read(path) == demo
    assert "token" not in path.read_text().lower()
    data = json.loads(path.read_text())
    data["repositories"][0]["languages"]["Java"] = -1
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="byte counts"):
        Profile.read(path)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"ships": 6},
        {"ships": True},
        {"fps": 12},
        {"scale": 0},
        {"duration": 1000},
        {"scale": 4, "duration": 20, "fps": 10},
        {"fps": 25, "duration": 20},
        {"activity_window": 0},
        {"labels": {"Java": "too long"}},
        {"colors": {"Java": "red"}},
        {"include": "all"},
        {"username": "../oops"},
        {"include_forks": "yes"},
        {"seed": []},
        {"observation_date": "2026-10-01"},
    ],
)
def test_config_bounds_before_frame_allocation(kwargs):
    with pytest.raises(ValueError):
        Config(**kwargs)


def test_toml_precedence_and_unknown_keys(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(
        'username="sailor"\nships=3\nobservation_date=2026-10-01\n[labels]\n"C#"="C#"\n'
    )
    config = load_config(path, {"ships": 5, "scale": None})
    assert config.ships == 5 and config.scale == 2
    assert config.observation_date == date(2026, 10, 1)
    path.write_text("typo=10")
    with pytest.raises(ValueError, match="unknown"):
        load_config(path)


def test_example_config_loads():
    assert load_config(Path("examples/config.toml")).ships == 5

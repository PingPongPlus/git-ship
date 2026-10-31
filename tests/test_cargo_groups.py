from datetime import UTC, datetime

import pytest
from PIL import ImageColor

from git_ship.config import Config
from git_ship.export import export
from git_ship.layout import layout
from git_ship.model import Commit, Profile, Repository
from git_ship.sprites import CARGO_GROUP_SIZE, INK, SHIP_DESIGNS, Style, cargo_groups, ship_sprite

BANK = (3, 10, 20, 38)


@pytest.mark.parametrize("commits", range(21))
def test_cargo_groups_preserve_commit_weight_at_every_load(commits):
    assert CARGO_GROUP_SIZE == 4
    large, small = cargo_groups(commits)
    assert 0 <= large <= 5 and 0 <= small < 4
    assert large * 4 + small == commits


@pytest.mark.parametrize("invalid", [-1, 21, True, 1.5, "4"])
def test_cargo_groups_reject_invalid_commit_counts(invalid):
    with pytest.raises(ValueError, match="cargo"):
        cargo_groups(invalid)


@pytest.mark.parametrize("design", SHIP_DESIGNS)
@pytest.mark.parametrize("width", (43, 53, 62))
def test_every_grouped_load_fits_without_overlap_or_changes_to_ship_art(design, width):
    style = Style("MMMMMM", design, "#335c87", "#79accc")
    empty = ship_sprite(style, width)
    assert empty.crop(BANK).getchannel("A").getbbox() is None
    outside = empty.copy()
    outside.paste((0, 0, 0, 0), BANK)
    for commits in range(21):
        loaded = ship_sprite(style, width, commits)
        large, small = cargo_groups(commits)
        bank = loaded.crop(BANK)
        # Every rectangular box must contribute its complete footprint. This
        # catches overlap, clipping, or missing boxes at any merge boundary.
        assert bank.getchannel("A").histogram()[255] == large * 56 + small * 20
        assert set(loaded.getchannel("A").tobytes()) == {0, 255}
        loaded.paste((0, 0, 0, 0), BANK)
        assert loaded.tobytes() == outside.tobytes(), (design, width, commits)


@pytest.mark.parametrize("commits", (4, 8, 12, 16, 20))
def test_fourth_small_container_merges_into_a_box_marked_four(commits):
    style = Style("JAVA", "steam", "#335c87", "#79accc")
    before = ship_sprite(style, 53, commits - 1).crop(BANK)
    after = ship_sprite(style, 53, commits).crop(BANK)
    assert cargo_groups(commits - 1) == (commits // 4 - 1, 3)
    assert cargo_groups(commits) == (commits // 4, 0)
    assert before.getchannel("A").histogram()[255] - after.getchannel("A").histogram()[255] == 4
    mark = ship_sprite(style, 53, commits).crop((5, 32, 8, 37))
    ink = (*ImageColor.getrgb(INK), 255)
    assert [
        "".join("1" if mark.getpixel((x, y)) == ink else "0" for x in range(3)) for y in range(5)
    ] == ["101", "101", "111", "001", "001"]


def test_grouped_gif_reports_real_commits_remainders_and_twenty_commit_cap(tmp_path):
    names = ("Java", "C++", "Python", "Rust", "JavaScript", "TypeScript")
    authored = (3, 4, 7, 8, 20, 25)
    languages = {name: 1000 - i * 100 for i, name in enumerate(names)}
    records = tuple(
        Commit(f"{i * 100 + j:040x}", "sailor", "2026-09-30T18:00:00Z", (name,))
        for i, (name, count) in enumerate(zip(names, authored, strict=True))
        for j in range(count)
    )
    observed = datetime(2026, 10, 1, 3, 23, tzinfo=UTC)
    profile = Profile(
        "sailor",
        observed.date(),
        (Repository("one", "sailor", False, False, None, languages, records),),
        observed_at=observed.isoformat(),
    )
    config = Config(
        scale=1, duration=2, fps=5, seed="grouped-cargo", lighthouse_beam=False, watermark=False
    )
    report, _ = export(layout(profile, config), config, tmp_path)
    assert report["commits_per_large_container"] == 4
    assert report["decoded_frames_match"]
    assert len(report["languages"]) == 6
    for language, count in zip(report["languages"], authored, strict=True):
        assert language["cargo"] == min(count, 20)
        assert language["large_containers"] * 4 + language["small_containers"] == language["cargo"]
        assert (language["large_containers"], language["small_containers"]) == divmod(
            min(count, 20), 4
        )

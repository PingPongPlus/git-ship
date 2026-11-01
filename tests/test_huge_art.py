from pathlib import Path

import pytest
from PIL import Image, ImageChops, ImageDraw

from git_ship.huge_ship import (
    COMMITS_PER_LARGE,
    HUGE_HEIGHT,
    HUGE_WIDTH,
    MAX_LARGE_CONTAINERS,
    MAX_TOTAL_COMMITS,
    draw_heavy_water,
    huge_cargo_counts,
    huge_ship_sprite,
)

APPROVED = Path(__file__).resolve().parents[1] / "artwork" / "huge-ship"


@pytest.mark.parametrize("commits", (0, 24, 72, 120))
def test_huge_approved_geometry_is_unchanged_outside_new_counters(commits):
    actual = huge_ship_sprite(commits)
    with Image.open(APPROVED / f"huge-ship-{commits}-commits.png") as original:
        assert actual.mode == original.mode == "RGBA"
        assert actual.size == original.size == (HUGE_WIDTH, HUGE_HEIGHT)
        difference = ImageChops.difference(actual, original)
        # Only the exact-total and optional overflow captions are new.
        mask = Image.new("L", actual.size, 255)
        draw = ImageDraw.Draw(mask)
        draw.rectangle((26, 85, 132, 91), fill=0)
        draw.rectangle((210, 85, 269, 91), fill=0)
        assert not ImageChops.multiply(difference, mask.convert("RGBA")).getbbox(alpha_only=False)
        assert (
            actual.crop((138, 85, 185, 92)).tobytes() == original.crop((138, 85, 185, 92)).tobytes()
        )


@pytest.mark.parametrize("remainder", range(6))
def test_small_boxes_preserve_every_remainder_commit(remainder):
    total = 72 + remainder
    counts = huge_cargo_counts(total)
    assert counts == {
        "total": total,
        "large": 12,
        "small": remainder,
        "visible_large": 12,
        "visible_small": remainder,
        "overflow_commits": 0,
    }
    empty = huge_ship_sprite(72)
    actual = huge_ship_sprite(total)
    for index in range(5):
        top = 70 - index * 6
        bank = actual.crop((245, top, 257, top + 6))
        original = empty.crop((245, top, 257, top + 6))
        assert (bank.tobytes() != original.tobytes()) == (index < remainder)
    assert actual.crop((72, 25, 239, 76)).tobytes() == empty.crop((72, 25, 239, 76)).tobytes()


@pytest.mark.parametrize("total", range(179, 187))
def test_capacity_and_overflow_keep_exact_commit_weights(total):
    counts = huge_cargo_counts(total)
    assert counts["large"] == total // COMMITS_PER_LARGE
    assert counts["small"] == total % COMMITS_PER_LARGE
    assert counts["visible_large"] == min(total // COMMITS_PER_LARGE, MAX_LARGE_CONTAINERS)
    assert counts["visible_small"] == counts["small"]
    assert (
        counts["visible_large"] * COMMITS_PER_LARGE
        + counts["visible_small"]
        + counts["overflow_commits"]
    ) == total
    if total < 186:
        assert counts["overflow_commits"] == 0
    else:
        assert counts["overflow_commits"] == 6


@pytest.mark.parametrize("total", (0, 6, 179, 185, 186, 200_000, MAX_TOTAL_COMMITS))
def test_huge_counters_and_art_remain_inside_the_native_canvas(total):
    image = huge_ship_sprite(total)
    left, top, right, bottom = image.getbbox()
    assert 0 < left < right < HUGE_WIDTH
    assert 0 < top < bottom < HUGE_HEIGHT
    assert set(image.getchannel("A").tobytes()) == {0, 255}
    assert image.crop((0, 0, HUGE_WIDTH, 5)).getchannel("A").getbbox() is None
    # Even the widest captions preserve the gap beside the hull name and bow.
    plain = huge_ship_sprite(0)
    for box in ((127, 84, 138, 93), (270, 84, 276, 93)):
        assert image.crop(box).tobytes() == plain.crop(box).tobytes()


def test_overflow_badge_appears_only_for_unrepresented_large_boxes():
    full = huge_ship_sprite(180).crop((210, 85, 270, 92))
    with_small_remainder = huge_ship_sprite(185).crop((210, 85, 270, 92))
    overflowing = huge_ship_sprite(186).crop((210, 85, 270, 92))
    assert full.tobytes() == with_small_remainder.tobytes()
    assert overflowing.tobytes() != full.tobytes()


@pytest.mark.parametrize("bad", (-1, True, 1.5, "72", MAX_TOTAL_COMMITS + 1))
def test_invalid_totals_are_rejected_before_rendering(bad):
    with pytest.raises(ValueError, match="total_commits"):
        huge_cargo_counts(bad)
    with pytest.raises(ValueError, match="total_commits"):
        huge_ship_sprite(bad)


def test_enormous_python_integer_never_reaches_text_conversion():
    with pytest.raises(ValueError, match="total_commits"):
        huge_ship_sprite(10**5000)


@pytest.mark.parametrize("foreground", (False, True))
def test_heavy_water_is_binary_calm_and_periodic(foreground):
    def water(t):
        image = Image.new("RGBA", (400, 160))
        draw_heavy_water(ImageDraw.Draw(image), 80, 35, t, foreground=foreground)
        return image

    assert water(0).tobytes() == water(1).tobytes()
    assert water(0).tobytes() != water(0.5).tobytes()  # One roll per loop, not two.
    boxes = []
    for phase in range(100):
        image = water(phase / 100)
        assert set(image.getchannel("A").tobytes()) == {0, 255}
        boxes.append(image.getbbox())
        # No high splash, detached spray or foam enters the hull label area.
        assert image.crop((0, 0, 400, 131)).getchannel("A").getbbox() is None
        left, top, right, bottom = image.getbbox()
        assert 0 < left < right < 400
        assert 131 <= top < bottom < 150
    assert max(box[0] for box in boxes) - min(box[0] for box in boxes) <= 2
    assert max(box[1] for box in boxes) - min(box[1] for box in boxes) <= 2

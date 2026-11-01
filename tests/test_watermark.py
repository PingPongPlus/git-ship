import random
from dataclasses import replace
from itertools import combinations

import pytest
from PIL import Image

from git_ship.animation import Animator
from git_ship.config import Config
from git_ship.layout import layout, placements
from git_ship.watermark import WATERMARK_HEIGHT, draw_watermark, watermark_label


@pytest.mark.parametrize(
    "days,period", [(1, "day"), (7, "week"), (30, "month"), (365, "year"), (14, "14 days")]
)
def test_watermark_displays_selected_period_and_fits_top_left(days, period):
    label = watermark_label(days)
    assert label == f"Git Ship — commits from the past {period}"
    image = Image.new("RGBA", (400, 160))
    draw_watermark(image, days)
    left, top, right, bottom = image.getbbox()
    assert (left, top) == (5, 4)
    assert right < image.width and bottom < WATERMARK_HEIGHT
    assert set(image.getchannel("A").tobytes()) == {0, 255}


def test_watermark_stays_readable_above_the_beam_and_can_be_disabled(demo):
    config = Config(seed="caption", scale=1, ships=0, activity_window=30)
    enabled = Animator(layout(demo, config), config)
    off = replace(config, watermark=False)
    disabled = Animator(layout(demo, off), off)
    expected = Image.new("RGBA", (400, 160))
    draw_watermark(expected, 30)
    for t in (0, 0.125, 0.25, 0.875):
        frame = enabled.frame(t)
        for y in range(WATERMARK_HEIGHT):
            for x in range(400):
                if expected.getpixel((x, y))[3]:
                    assert frame.getpixel((x, y)) == expected.getpixel((x, y))
        assert (
            disabled.frame(t).crop((0, 0, 400, WATERMARK_HEIGHT)).tobytes()
            != frame.crop((0, 0, 400, WATERMARK_HEIGHT)).tobytes()
        )


@pytest.mark.parametrize("seed", range(10))
def test_ship_motion_envelopes_clear_enabled_watermark(demo, seed):
    scene = layout(demo, Config(seed=seed))
    assert len(scene.ships) == 6
    assert all(ship.y - 2 >= WATERMARK_HEIGHT for ship in scene.ships)


def test_dense_fallback_respects_watermark_header():
    class CrowdedRandom(random.Random):
        def randint(self, a, b):
            return a

    positions = placements([62] * 6, CrowdedRandom(42), WATERMARK_HEIGHT)
    boxes = [(x - 8, y - 2, x + 70, y + 63) for x, y in positions]
    for left, top, right, bottom in boxes:
        assert left > 70 and right < 400
        assert top >= WATERMARK_HEIGHT and bottom < 160
    for a, b in combinations(boxes, 2):
        assert a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1]

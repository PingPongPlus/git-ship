from dataclasses import replace
from pathlib import Path

import pytest
from PIL import Image, ImageChops, ImageColor

from git_ship.sprites import SHIP_DESIGNS, Style, cargo_groups, ship_sprite

APPROVED = Path(__file__).resolve().parents[1] / "artwork" / "ship-designs"
STYLES = {
    "ferry": Style("FERRY", "ferry", "#346888", "#85b5cf"),
    "trawler": Style("TRAWL", "trawler", "#a34e44", "#d9825b"),
    "tanker": Style("TANKER", "tanker", "#537587", "#9bbdcb"),
}


@pytest.mark.parametrize("design", STYLES)
@pytest.mark.parametrize("cargo", (0, 20))
def test_approved_native_art_is_preserved_exactly(design, cargo):
    assert design in SHIP_DESIGNS
    with Image.open(APPROVED / f"{design}-cargo-{cargo}.png") as approved:
        actual = ship_sprite(STYLES[design], 60, cargo)
        assert actual.mode == approved.mode == "RGBA"
        assert actual.size == approved.size == (60, 56)
        if cargo:
            # Grouped cargo is allowed to change only the reserved cargo bank;
            # retain the original approved hull and superstructure references.
            actual = actual.copy()
            approved = approved.copy()
            actual.paste((0, 0, 0, 0), (3, 10, 20, 38))
            approved.paste((0, 0, 0, 0), (3, 10, 20, 38))
        assert actual.tobytes() == approved.tobytes()


@pytest.mark.parametrize("design", STYLES)
@pytest.mark.parametrize("width", (43, 53, 60, 62))
def test_new_designs_preserve_cargo_clearance_labels_and_canvas(design, width):
    style = STYLES[design]
    empty = ship_sprite(style, width, 0)
    assert empty.crop((3, 10, 20, 38)).getchannel("A").getbbox() is None
    for cargo in (1, 7, 20):
        loaded = ship_sprite(style, width, cargo)
        large, small = cargo_groups(cargo)
        assert (
            loaded.crop((3, 10, 20, 38)).getchannel("A").histogram()[255] == large * 56 + small * 20
        )
        assert loaded.crop((0, 38, width, 56)).tobytes() == empty.crop((0, 38, width, 56)).tobytes()
        assert set(loaded.getchannel("A").tobytes()) == {0, 255}
        left, top, right, bottom = loaded.getbbox()
        assert 0 < left < right < width
        assert 0 < top < bottom < 56
    labeled = ship_sprite(replace(style, label="MMMMMM"), width)
    blank = ship_sprite(replace(style, label="      "), width)
    for painted, underlying in zip(
        labeled.get_flattened_data(), blank.get_flattened_data(), strict=True
    ):
        if painted != underlying:
            assert underlying == (*ImageColor.getrgb(style.hull), 255)


@pytest.mark.parametrize("width", (43, 53, 60, 62))
def test_trawler_sway_changes_only_the_suspended_rigging(width):
    style = STYLES["trawler"]
    still = ship_sprite(style, width, 20)
    limit = 1 if width < 50 else 2
    for sway in (-limit, limit):
        moved = ship_sprite(style, width, 20, hook_sway=sway)
        difference = ImageChops.difference(still.convert("RGB"), moved.convert("RGB"))
        left, top, right, bottom = difference.getbbox()
        assert 20 < left < right < width - 4
        assert 20 < top < bottom <= 36
        assert moved.crop((3, 10, 20, 38)).tobytes() == still.crop((3, 10, 20, 38)).tobytes()
        assert moved.crop((0, 38, width, 56)).tobytes() == still.crop((0, 38, width, 56)).tobytes()
        assert moved.tobytes() == ship_sprite(style, width, 20, hook_sway=sway * 100).tobytes()
    for invalid in (True, 1.5, "left"):
        with pytest.raises(ValueError, match="hook_sway"):
            ship_sprite(style, width, hook_sway=invalid)


@pytest.mark.parametrize("design", ("ferry", "tanker"))
def test_other_new_designs_do_not_sway(design):
    assert (
        ship_sprite(STYLES[design], 60).tobytes()
        == ship_sprite(STYLES[design], 60, hook_sway=2).tobytes()
    )

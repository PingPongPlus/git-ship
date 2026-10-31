"""Original editable pixel sprite source, drawn on a single integer grid.

Every rectangle and polygon here is an art primitive. Sprites are separate
RGBA images, never crops or transformations of the concept reference.
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import dataclass
from importlib.resources import files

from PIL import Image, ImageColor, ImageDraw

from .config import Config
from .font import GLYPHS, paint_text, text_width
from .model import CARGO_LIMIT

INK = "#192e40"
CREAM = "#f4e6c8"
SHADE = "#c9bea6"
RED = "#b55250"
GOLD = "#efbe5d"
WAVE = "#70b3ce"
WAVE_DEEP = "#39799c"
FOAM = "#f1f4e8"
SMOKE = "#b2b9b8"
SMOKE_SHADE = "#909c9f"
SMOKE_LIGHT = "#d4d9d5"
STONE = "#697b88"

# Sprite-space mouth positions, shared by the art and its smoke emitter.
FUNNEL_ORIGINS = {"steam": (21, 18), "tug": (21, 20)}
SHIP_DESIGNS = ("steam", "tug", "freighter", "sail", "ferry", "trawler", "tanker")
CARGO_GROUP_SIZE = 4

LANGUAGES = json.loads(files("git_ship").joinpath("assets/languages.json").read_text())


def stable_seed(value: str) -> int:
    return int.from_bytes(hashlib.sha256(value.encode()).digest()[:8], "big")


@dataclass(frozen=True)
class Style:
    label: str
    design: str
    hull: str
    trim: str


def cargo_groups(cargo: int) -> tuple[int, int]:
    """Four commits per large container; the remainder stays in small boxes."""
    if type(cargo) is not int or not 0 <= cargo <= CARGO_LIMIT:
        raise ValueError(f"cargo must be an integer in 0..{CARGO_LIMIT}")
    return divmod(cargo, CARGO_GROUP_SIZE)


def language_style(name: str, config: Config, *, design: str | None = None) -> Style:
    known = LANGUAGES.get(name)
    if not isinstance(known, dict):
        variants = LANGUAGES["fallbacks"]
        known = variants[stable_seed(name) % len(variants)]
    letters = unicodedata.normalize("NFKD", name.upper()).encode("ascii", "ignore").decode()
    label = "".join(c for c in letters if c in GLYPHS).strip()[:6] or "CODE"
    label = config.labels.get(name, known.get("label", label))
    hull = config.colors.get(name, known["hull"])
    # White lettering needs a dark enough hull. A light user color becomes trim.
    r, g, b = ImageColor.getrgb(hull)
    if 0.2126 * r + 0.7152 * g + 0.0722 * b > 150:
        trim = hull
        hull = "#" + "".join(f"{round(c * 0.52):02x}" for c in (r, g, b))
    else:
        trim = known["trim"]
    return Style(label, design if design is not None else known["design"], hull, trim)


def _approved_superstructure(
    d: ImageDraw.ImageDraw, style: Style, width: int, hook_sway: int
) -> None:
    """Approved 60-pixel hull studies, fitted beside the unchanged cargo bank."""

    def x(value: int) -> int:
        return 21 + round((value - 21) * (width - 24) / 36)

    def rect(box: tuple[int, int, int, int], fill: str) -> None:
        left, top, right, bottom = box
        d.rectangle((x(left), top, x(right), bottom), fill=fill)

    def points(vertices: list[tuple[int, int]]) -> list[tuple[int, int]]:
        return [(x(px), py) for px, py in vertices]

    if style.design == "ferry":
        rect((22, 29, 55, 38), INK)
        rect((23, 30, 54, 37), CREAM)
        rect((23, 30, 24, 37), SHADE)
        for px in (27, 34, 41, 48):
            rect((px, 32, px + 3, 35), INK)
            rect((px + 1, 32, px + 2, 34), style.trim)
        rect((25, 19, 53, 28), INK)
        rect((26, 20, 52, 27), CREAM)
        rect((26, 20, 27, 27), SHADE)
        for px in (30, 37, 44):
            rect((px, 22, px + 3, 25), INK)
            rect((px + 1, 22, px + 2, 24), style.trim)
        rect((23, 18, 55, 19), INK)
        rect((24, 19, 54, 19), style.trim)
        rect((21, 28, 56, 29), INK)
        rect((22, 29, 55, 29), style.trim)
        rect((40, 9, 42, 18), INK)
        rect((41, 10, 41, 17), GOLD)
        d.polygon(points([(43, 10), (48, 12), (43, 14)]), fill=style.trim)
    elif style.design == "trawler":
        rect((26, 8, 28, 38), INK)
        rect((27, 10, 27, 37), style.trim)
        d.line(points([(28, 14), (40, 20)]), fill=INK, width=2)
        d.line(points([(29, 14), (40, 19)]), fill=style.trim)
        d.line(points([(27, 9), (40, 19)]), fill=SHADE)
        # Only the suspended line and hook sway; their boom anchor stays fixed.
        limit = 1 if width < 50 else 2
        sway = max(-limit, min(hook_sway, limit))
        d.line([(x(40), 20), (x(40) + sway, 33)], fill=INK)
        d.line(
            [(x(px) + sway, py) for px, py in ((40, 33), (38, 35), (36, 35), (36, 32))],
            fill=GOLD,
        )
        rect((31, 35, 35, 38), INK)
        rect((32, 36, 34, 37), SHADE)
        rect((44, 24, 56, 38), INK)
        rect((45, 25, 55, 37), CREAM)
        rect((45, 25, 46, 37), SHADE)
        for px in (48, 52):
            rect((px, 27, px + 2, 31), INK)
            rect((px + 1, 27, px + 1, 30), style.trim)
        rect((42, 22, 57, 24), INK)
        rect((43, 23, 56, 23), style.trim)
        rect((51, 16, 53, 22), INK)
        rect((52, 17, 52, 21), GOLD)
    elif style.design == "tanker":
        for px in (22, 33):
            d.polygon(
                points(
                    [(px + 2, 27), (px + 7, 27), (px + 9, 29), (px + 9, 37), (px, 37), (px, 29)]
                ),
                fill=INK,
            )
            d.polygon(
                points(
                    [
                        (px + 2, 28),
                        (px + 7, 28),
                        (px + 8, 30),
                        (px + 8, 36),
                        (px + 1, 36),
                        (px + 1, 30),
                    ]
                ),
                fill=CREAM,
            )
            rect((px + 2, 30, px + 3, 36), SHADE)
            rect((px + 4, 24, px + 5, 27), INK)
            rect((px + 3, 24, px + 6, 24), GOLD)
        rect((24, 35, 44, 36), INK)
        rect((25, 35, 43, 35), style.trim)
        rect((46, 24, 56, 38), INK)
        rect((47, 25, 55, 37), CREAM)
        rect((47, 25, 48, 37), SHADE)
        rect((50, 27, 53, 31), INK)
        rect((51, 27, 52, 30), GOLD)
        rect((44, 22, 57, 24), INK)
        rect((45, 23, 56, 23), style.trim)
        rect((51, 15, 53, 22), INK)
        rect((52, 16, 52, 21), style.trim)


def ship_sprite(style: Style, width: int, cargo: int = 0, *, hook_sway: int = 0) -> Image.Image:
    """A right-facing boat, its hull at y=39..52; lettering never scales."""
    large, small = cargo_groups(cargo)
    if type(hook_sway) is not int:
        raise ValueError("hook_sway must be an integer")
    if style.design not in SHIP_DESIGNS:
        raise ValueError(f"unknown ship design: {style.design}")
    image = Image.new("RGBA", (width, 56))
    d = ImageDraw.Draw(image)
    mid = width - 13

    def rect(box: tuple[int, int, int, int], fill: str) -> None:
        d.rectangle(box, fill=fill)

    if style.design in ("steam", "tug"):
        funnel, mouth = FUNNEL_ORIGINS[style.design]
        # The stack must reach the deck rather than float above it. The cabin
        # is painted afterward so narrower boats retain the correct overlap.
        rect((funnel, mouth, funnel + 6, 38), INK)
        rect((funnel + 1, mouth + 3, funnel + 5, 37), style.trim)
        rect((funnel, mouth, funnel + 6, mouth + 2), INK)
        cabin = width - 17
        rect((cabin, 29, width - 5, 39), INK)
        rect((cabin + 1, 30, width - 6, 38), CREAM)
        rect((cabin + 1, 30, cabin + 2, 38), SHADE)
        for x in (cabin + 3, cabin + 8):
            rect((x, 32, x + 3, 35), INK)
            rect((x + 1, 32, x + 2, 34), GOLD)
        rect((cabin - 1, 28, width - 4, 29), INK)
        if style.design == "steam":
            rect((width - 9, 23, width - 7, 28), INK)
            rect((width - 8, 24, width - 8, 27), style.trim)
    elif style.design == "freighter":
        rect((width - 19, 25, width - 5, 39), INK)
        rect((width - 18, 26, width - 6, 38), CREAM)
        rect((width - 21, 24, width - 4, 25), INK)
        rect((width - 15, 17, width - 13, 24), INK)
        rect((width - 14, 18, width - 14, 23), GOLD)
        for x in (width - 15, width - 10):
            rect((x, 29, x + 2, 32), INK)
    elif style.design == "sail":
        # Stepped triangles: hard integer edges, cream sails and a dark mast.
        d.polygon([(mid - 2, 9), (mid - 2, 35), (21, 35)], fill=INK)
        d.polygon([(mid - 3, 13), (mid - 3, 33), (23, 33)], fill=CREAM)
        d.polygon([(mid + 2, 12), (width - 4, 35), (mid + 2, 35)], fill=INK)
        d.polygon([(mid + 3, 16), (width - 7, 33), (mid + 3, 33)], fill=CREAM)
        rect((mid - 1, 7, mid + 1, 39), INK)
        rect((mid, 9, mid, 36), style.trim)
        rect((mid - 6, 35, mid + 7, 39), INK)
        rect((mid - 5, 36, mid + 6, 38), CREAM)
    else:
        _approved_superstructure(d, style, width, hook_sway)

    # Compact four commits into one large box marked "4". Remainders remain
    # individual small boxes; every possible load fits the same reserved bank.
    colors = (style.trim, "#ad655b", "#668fa5")
    for index in range(large):
        x = 3 + (index % 2) * 9
        y = 31 - (index // 2) * 7
        rect((x, y, x + 7, y + 6), INK)
        rect((x + 1, y + 1, x + 6, y + 5), colors[index % 3])
        for row, bits in enumerate((5, 5, 7, 1, 1)):
            for column in range(3):
                if bits & (1 << (2 - column)):
                    d.point((x + 2 + column, y + 1 + row), fill=INK)
    for index in range(small):
        if large:
            x = 3 + (large % 2) * 9
            y = 34 - (large // 2) * 7 - index * 4
        else:
            x, y = 3 + index * 6, 34
        color = colors[(large * CARGO_GROUP_SIZE + index) % 3]
        rect((x, y, x + 4, y + 3), INK)
        rect((x + 1, y + 1, x + 3, y + 2), color)

    # Wide flat hull panels make the names part of the boat's silhouette.
    if width < 49:
        # A six-character name needs a full panel through row 48 even on the
        # fifth ship. Begin the narrow hull's taper beneath the lettering.
        d.polygon(
            [(1, 38), (width - 2, 38), (width - 2, 48), (width - 9, 52), (8, 52), (1, 48)],
            fill=INK,
        )
        d.polygon(
            [(3, 40), (width - 4, 40), (width - 4, 48), (width - 10, 50), (9, 50), (3, 48)],
            fill=style.hull,
        )
    else:
        d.polygon(
            [(1, 38), (width - 2, 38), (width - 4, 46), (width - 9, 52), (8, 52), (3, 47)],
            fill=INK,
        )
        d.polygon(
            [(3, 40), (width - 4, 40), (width - 6, 46), (width - 10, 50), (9, 50), (5, 46)],
            fill=style.hull,
        )
    rect((3, 38, width - 3, 40), style.trim)
    rect((8, 51, width - 10, 51), INK)
    paint_text(d, ((width - text_width(style.label)) // 2, 42), style.label, CREAM)
    return image


def lighthouse_sprite(bright: bool = True) -> Image.Image:
    """A 42×78 lighthouse and three minimal rocks; no land or scenery."""
    image = Image.new("RGBA", (42, 78))
    d = ImageDraw.Draw(image)
    d.polygon([(13, 27), (29, 27), (32, 68), (9, 68)], fill=INK)
    d.polygon([(15, 28), (27, 28), (29, 66), (12, 66)], fill=CREAM)
    d.polygon([(15, 28), (17, 28), (15, 66), (12, 66)], fill=SHADE)
    d.rectangle((14, 40, 28, 45), fill=RED)
    d.rectangle((13, 55, 29, 60), fill=RED)
    d.rectangle((20, 32, 22, 36), fill=INK)
    d.rectangle((20, 48, 22, 52), fill=INK)
    d.rectangle((20, 62, 24, 68), fill=INK)
    d.rectangle((12, 13, 29, 28), fill=INK)
    d.rectangle((16, 15, 25, 24), fill=GOLD if bright else "#d8a44c")
    d.rectangle((19, 16, 23, 23), fill=CREAM if bright else GOLD)
    d.rectangle((10, 25, 31, 28), fill=INK)
    for x in (13, 18, 23, 28):
        d.rectangle((x, 26, x + 1, 27), fill=SHADE)
    d.polygon([(10, 12), (15, 8), (18, 7), (18, 3), (23, 3), (23, 7), (27, 9), (31, 12)], fill=INK)
    d.rectangle((19, 5, 20, 8), fill=STONE)
    d.rectangle((14, 11, 27, 12), fill="#33546a")
    d.polygon([(2, 72), (7, 67), (13, 68), (18, 74), (14, 76), (2, 76)], fill=INK)
    d.polygon([(5, 71), (8, 68), (12, 69), (14, 73), (4, 73)], fill=STONE)
    d.polygon([(14, 74), (18, 68), (26, 67), (30, 72), (28, 76), (14, 76)], fill=INK)
    d.polygon([(18, 72), (20, 69), (25, 69), (27, 73), (17, 73)], fill=STONE)
    d.polygon([(28, 73), (32, 69), (36, 71), (40, 75), (28, 76)], fill=INK)
    d.line((31, 72, 35, 72), fill=SHADE)
    return image

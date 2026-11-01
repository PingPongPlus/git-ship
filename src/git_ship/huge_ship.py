"""Approved heavy cargo hull and calm displacement wake on the native grid."""

from __future__ import annotations

import math
from collections import Counter

from PIL import Image, ImageDraw

from .cargo_art import STYLES, container
from .font import paint_text, text_width
from .sprites import CREAM, FOAM, GOLD, INK, SHADE, WAVE, WAVE_DEEP

HUGE_WIDTH = 300
HUGE_HEIGHT = 110
COMMITS_PER_LARGE = 6
MAX_LARGE_CONTAINERS = 30
# These fixed-width counters exceed the client's bounded API workload by orders
# of magnitude. Reject larger values before Python ever converts them to text.
MAX_TOTAL_COMMITS = 999_999_999
NAVY = "#203748"
HULL_SHADE = "#142736"
HULL_EDGE = "#10212e"
WATERLINE = "#a34e44"
CONTAINERS = ("#b55250", "#dfbe62", "#39799c", "#287477", "#c9bea6", "#d9825b")


def huge_cargo_counts(total_commits: int) -> dict[str, int]:
    """Exact commit weights, visible boxes and commits beyond the large-box bay."""
    if type(total_commits) is not int or not 0 <= total_commits <= MAX_TOTAL_COMMITS:
        raise ValueError(f"total_commits must be an integer in 0..{MAX_TOTAL_COMMITS}")
    large, small = divmod(total_commits, COMMITS_PER_LARGE)
    visible_large = min(large, MAX_LARGE_CONTAINERS)
    return {
        "total": total_commits,
        "large": large,
        "small": small,
        "visible_large": visible_large,
        "visible_small": small,
        "overflow_commits": (large - visible_large) * COMMITS_PER_LARGE,
    }


def language_cargo_plan(total_commits: int, language_counts: tuple[tuple[str, int], ...]) -> dict:
    """Pack full single-language boxes, then mixed leftovers, without losing weight."""
    counts = huge_cargo_counts(total_commits)
    if (
        any(
            not isinstance(name, str) or not name or type(n) is not int or n < 0
            for name, n in language_counts
        )
        or len({name for name, _ in language_counts}) != len(language_counts)
        or sum(n for _, n in language_counts) != total_commits
    ):
        raise ValueError("container language counts must be unique and sum to total_commits")
    ordered = sorted(language_counts, key=lambda p: (-p[1], p[0].casefold(), p[0]))
    large: list[dict] = []
    leftovers: list[str] = []

    def box(names):
        content = dict(sorted(Counter(names).items()))
        return {
            "label": next(iter(content)) if len(content) == 1 else "Mixed",
            "commits": len(names),
            "languages": content,
        }

    for name, n in ordered:
        for _ in range(min(n // COMMITS_PER_LARGE, MAX_LARGE_CONTAINERS - len(large))):
            large.append(box([name] * COMMITS_PER_LARGE))
        leftovers.extend([name] * (n % COMMITS_PER_LARGE))
    full_end = len(leftovers) // COMMITS_PER_LARGE * COMMITS_PER_LARGE
    for start in range(0, full_end, COMMITS_PER_LARGE):
        if len(large) == MAX_LARGE_CONTAINERS:
            break
        large.append(box(leftovers[start : start + COMMITS_PER_LARGE]))
    small = [box([name]) for name in leftovers[full_end:]]
    assert len(large) == counts["visible_large"]
    assert len(small) == counts["visible_small"]
    return {"large": large, "small": small, "overflow_commits": counts["overflow_commits"]}


def huge_ship_sprite(
    total_commits: int,
    language_counts: tuple[tuple[str, int], ...] | None = None,
    *,
    counter_total: int | None = None,
) -> Image.Image:
    """A wide low freighter, with one large container per six commits."""
    counts = huge_cargo_counts(total_commits)
    counter = (
        counts["total"] if counter_total is None else huge_cargo_counts(counter_total)["total"]
    )
    if counter < total_commits:
        raise ValueError("the authored commit counter cannot be smaller than cargo")
    plan = (
        language_cargo_plan(total_commits, language_counts) if language_counts is not None else None
    )
    image = Image.new("RGBA", (HUGE_WIDTH, HUGE_HEIGHT))
    d = ImageDraw.Draw(image)

    def rect(box, color):
        d.rectangle(box, fill=color)

    # White aft accommodation block: stacked decks, windows and railings.
    rect((17, 43, 57, 77), HULL_EDGE)
    rect((19, 44, 55, 76), CREAM)
    rect((19, 44, 23, 76), SHADE)
    for y in (50, 64):
        for x in (27, 34, 41, 48):
            rect((x, y, x + 3, y + 3), INK)
            rect((x + 1, y, x + 2, y + 1), "#79accc")
    for y in (57, 71):
        rect((14, y, 59, y + 2), HULL_EDGE)
        rect((15, y, 58, y), "#9bbdcb")
        for x in range(17, 59, 6):
            rect((x, y - 3, x, y - 1), SHADE)
    rect((23, 29, 59, 43), HULL_EDGE)
    rect((25, 30, 57, 42), CREAM)
    rect((25, 30, 28, 42), SHADE)
    for x in (30, 36, 42, 48, 54):
        rect((x, 33, x + 3, 37), INK)
        rect((x + 1, 33, x + 2, 35), "#79accc")
    rect((21, 27, 62, 29), HULL_EDGE)
    rect((22, 27, 61, 27), "#9bbdcb")
    rect((25, 19, 34, 26), INK)
    rect((25, 18, 34, 19), HULL_EDGE)
    rect((28, 15, 30, 18), INK)
    rect((42, 7, 44, 26), SHADE)
    rect((43, 8, 43, 25), CREAM)
    rect((36, 15, 51, 16), SHADE)
    rect((40, 10, 47, 11), CREAM)
    rect((43, 5, 43, 7), GOLD)
    d.line((35, 25, 43, 12, 54, 25), fill=SHADE)
    # Orange rescue boat at the stern, attached below the accommodation.
    d.polygon([(9, 64), (15, 61), (20, 64), (18, 70), (11, 71), (7, 68)], fill=HULL_EDGE)
    d.polygon([(10, 65), (15, 63), (18, 65), (16, 69), (11, 69), (9, 67)], fill="#d9825b")
    d.line((12, 64, 16, 65), fill=GOLD)

    # Large ISO-like container panels. Six columns, up to five supported tiers.
    cargo = counts["visible_large"]
    column_order = (2, 3, 1, 4, 0, 5)

    def position(index):
        if plan is None:
            tier, offset = divmod(index, 6)
            return column_order[offset], tier
        # Adjacent entries in the grouped cargo plan stay adjacent on deck:
        # fill supported stacks from left to right, rather than center-out rows.
        tiers = max(1, math.ceil(cargo / 6))
        column, tier = divmod(index, tiers)
        return column, tier

    for index in range(cargo):
        column, tier = position(index)
        x, y = 72 + column * 28, 66 - tier * 10
        color = CONTAINERS[(column + tier * 2) % len(CONTAINERS)]
        rect((x, y, x + 26, y + 9), HULL_EDGE)
        rect((x + 1, y + 1, x + 25, y + 8), color)
        # Crisp ribs and a restrained highlight, all on the same logical grid.
        for rib in (5, 10, 15, 20):
            rect((x + rib, y + 2, x + rib, y + 7), HULL_SHADE)
        rect((x + 2, y + 1, x + 24, y + 1), SHADE if color == "#c9bea6" else color)
        rect((x + 24, y + 3, x + 24, y + 6), CREAM)

    # Fine deck rails and the smaller forward mast leave the cargo unobstructed.
    rect((6, 76, 261, 78), HULL_EDGE)
    rect((8, 76, 260, 76), "#9bbdcb")
    for x in range(9, 260, 10):
        rect((x, 73, x, 77), "#9bbdcb")
    rect((272, 43, 273, 74), SHADE)
    rect((267, 51, 279, 52), CREAM)
    rect((269, 47, 276, 47), "#9bbdcb")
    rect((272, 40, 273, 42), GOLD)
    d.line((263, 73, 272, 51, 282, 72), fill=SHADE)

    # Dark, broad hull. Its lower red waterline is submerged under broken foam.
    d.polygon(
        [
            (5, 77),
            (246, 77),
            (260, 71),
            (296, 71),
            (282, 94),
            (272, 100),
            (22, 100),
            (11, 93),
            (5, 87),
        ],
        fill=HULL_EDGE,
    )
    d.polygon(
        [
            (7, 79),
            (247, 79),
            (261, 73),
            (292, 73),
            (279, 93),
            (270, 98),
            (23, 98),
            (13, 91),
            (7, 86),
        ],
        fill=NAVY,
    )
    d.polygon([(14, 93), (280, 93), (272, 99), (23, 99)], fill=HULL_SHADE)
    d.polygon([(18, 96), (277, 96), (272, 99), (24, 99)], fill=WATERLINE)
    d.line((23, 99, 271, 99), fill="#813b3c")
    d.line((10, 79, 247, 79, 262, 73, 289, 73), fill="#33546a")
    for x in (28, 63, 101, 139, 177, 215):
        rect((x, 81, x + 2, 82), SHADE)
    d.polygon([(285, 79), (282, 82), (284, 85), (286, 82)], fill=GOLD)
    label = "GIT-SHIP"
    paint_text(d, ((300 - text_width(label)) // 2 + 12, 85), label, CREAM)
    # Remainders retain their exact weight: one small box is one commit.
    for index in range(counts["visible_small"]):
        top = 70 - index * 6
        color = CONTAINERS[index % len(CONTAINERS)]
        if plan is not None:
            color = STYLES.get(plan["small"][index]["label"], ("#788e98", ""))[0]
        rect((245, top, 256, top + 5), HULL_EDGE)
        rect((246, top + 1, 255, top + 4), color)
        d.line((249, top + 2, 249, top + 3), fill=HULL_SHADE)
        d.line((253, top + 2, 253, top + 3), fill=HULL_SHADE)
    unit = "COMMIT" if counter == 1 else "COMMITS"
    paint_text(d, (26, 85), f"{counter} {unit}", SHADE)
    if counts["overflow_commits"]:
        paint_text(d, (210, 85), f"+{counts['overflow_commits']}", GOLD)
    if plan is not None:
        for index, box in enumerate(plan["large"]):
            column, tier = position(index)
            x, y = 72 + column * 28, 66 - tier * 10
            image.alpha_composite(container(box["label"]), (x, y))
    assert set(image.getchannel("A").tobytes()) == {0, 255}
    return image


def draw_heavy_water(
    draw: ImageDraw.ImageDraw, x: int, y: int, t: float, *, foreground: bool = False
) -> None:
    """Slow broad displacement foam, with one gentle roll per complete loop."""
    angle = math.tau * (t % 1)
    water_y = y + 99
    if not foreground:
        # Irregular lengths and offsets avoid an evenly tiled row of waves.
        patches = ((-16, 29, 4), (24, 46, 7), (85, 31, 4), (132, 43, 6), (190, 32, 4), (235, 29, 7))
        for index, (offset, length, depth) in enumerate(patches):
            phase = angle + index * 1.13
            left = x + offset + round(math.sin(phase))
            top = water_y + depth + round(0.7 * math.sin(phase + 0.8))
            draw.polygon(
                [
                    (left, top),
                    (left + length - 5, top),
                    (left + length - 5, top + 1),
                    (left + length, top + 1),
                    (left + length, top + 2),
                    (left + 5, top + 2),
                    (left + 5, top + 1),
                    (left, top + 1),
                ],
                fill=WAVE_DEEP,
            )
            draw.rectangle((left + 3, top - 1, left + length - 4, top), fill=WAVE)
            draw.rectangle((left + 7, top - 2, left + length - 9, top - 1), fill=FOAM)
        return

    for index, (offset, length) in enumerate(((23, 22), (62, 37), (116, 25), (165, 36), (222, 30))):
        phase = angle + index * 1.17
        left = x + offset + round(math.sin(phase))
        top = water_y - 1 + round(0.7 * math.sin(phase + 0.5))
        draw.rectangle((left, top, left + length, top + 1), fill=WAVE)
        draw.rectangle((left + 3, top - 1, left + length - 6, top), fill=FOAM)
        draw.rectangle((left + 7, top - 1, left + 11, top - 1), fill=FOAM)

    # A low rounded bow curl replaces the old high crest and flying spray.
    bow_x = x + 282
    lift = round(0.7 * math.sin(angle))
    draw.polygon(
        [
            (bow_x - 8, water_y + 2),
            (bow_x - 4, water_y),
            (bow_x - 1, water_y),
            (bow_x + 1, water_y - 2 + lift),
            (bow_x + 3, water_y - 2 + lift),
            (bow_x + 5, water_y),
            (bow_x + 9, water_y + 1),
            (bow_x + 13, water_y + 3),
            (bow_x + 10, water_y + 4),
            (bow_x - 8, water_y + 4),
        ],
        fill=WAVE,
    )
    draw.line(
        [
            (bow_x - 5, water_y + 1),
            (bow_x - 1, water_y - 1),
            (bow_x + 2, water_y - 2 + lift),
            (bow_x + 5, water_y + 1),
            (bow_x + 10, water_y + 2),
        ],
        fill=FOAM,
    )

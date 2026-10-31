"""Fresh free-position layouts with non-overlapping full motion envelopes."""

from __future__ import annotations

import math
import random
import secrets
from dataclasses import dataclass

from .config import HEIGHT, WIDTH, Config
from .model import Language, Profile, global_activity, rank_languages
from .sprites import SHIP_DESIGNS, Style, language_style, stable_seed
from .watermark import WATERMARK_HEIGHT


@dataclass(frozen=True)
class Ship:
    language: Language
    style: Style
    x: int
    y: int
    width: int
    phase: float
    drift: float
    bob: float


@dataclass(frozen=True)
class Scene:
    username: str
    ships: tuple[Ship, ...]
    energy: float
    layout_seed: str = ""


def placements(widths: list[int], rng: random.Random, top_margin: int = 0) -> list[tuple[int, int]]:
    """Sample the entire sea, retrying bounded packs before a guaranteed fit."""
    if not widths:
        return []

    def separated(a: tuple[int, ...], b: tuple[int, ...]) -> bool:
        return a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1]

    for _ in range(96):
        positions: dict[int, tuple[int, int]] = {}
        boxes: list[tuple[int, ...]] = []
        order = list(range(len(widths)))
        rng.shuffle(order)
        for index in order:
            width = widths[index]
            for _ in range(160):
                x = rng.randint(82, WIDTH - width - 9)
                y = rng.randint(2 + top_margin, HEIGHT - 64)
                box = (x - 8, y - 2, x + width + 8, y + 63)
                if all(separated(box, other) for other in boxes):
                    positions[index] = (x, y)
                    boxes.append(box)
                    break
            else:
                break
        if len(positions) == len(widths):
            return [positions[index] for index in range(len(widths))]

    # Dense fleets can fragment free space. Random-width columns and independent
    # vertical splits guarantee a fit without shrinking sprites or overlapping.
    minimum = max(widths) + 18
    extra = WIDTH - 76 - 3 * minimum
    cuts = sorted((0, rng.randrange(extra + 1), rng.randrange(extra + 1), extra))
    columns = [minimum + cuts[i + 1] - cuts[i] for i in range(3)]
    rng.shuffle(columns)
    cells = [(column, row) for column in range(3) for row in range(2)]
    rng.shuffle(cells)
    splits = [rng.randint(68 + top_margin, 90) for _ in range(3)]
    result = []
    for width, (column, row) in zip(widths, cells, strict=False):
        left = 74 + sum(columns[:column])
        x = rng.randint(left + 8, left + columns[column] - width - 10)
        y = (
            rng.randint(2 + top_margin, splits[column] - 64)
            if row == 0
            else rng.randint(splits[column] + 4, 96)
        )
        result.append((x, y))
    return result


def layout(profile: Profile, config: Config) -> Scene:
    # Filter before limiting: an inactive high-byte language must never hide an
    # active language farther down the ranking. Unknown commit data is hidden.
    languages = tuple(
        language for language in rank_languages(profile, config) if (language.cargo or 0) > 0
    )[: config.ships]
    energy = global_activity(profile)
    layout_seed = str(config.seed) if config.seed is not None else secrets.token_hex(16)
    rng = random.Random(stable_seed(layout_seed))
    identity = profile.username.casefold()
    widths = [min(round(44 + 16 * math.sqrt(language.share)), 62) for language in languages]
    positions = placements(widths, rng, WATERMARK_HEIGHT if config.watermark else 0)
    # Each shuffled bag uses every approved design before repeating. Ship shapes
    # are chosen per generation, independently of the language they carry.
    design_rng = random.Random(stable_seed(f"{layout_seed}:ships"))
    designs = []
    while len(designs) < len(languages):
        bag = list(SHIP_DESIGNS)
        design_rng.shuffle(bag)
        designs.extend(bag)
    ships = []
    for language, width, (x, y), design in zip(
        languages, widths, positions, designs[: len(languages)], strict=True
    ):
        phase = (stable_seed(f"{identity}:{language.name}") % 1024) / 1024
        ships.append(
            Ship(
                language,
                language_style(language.name, config, design=design),
                x,
                y,
                width,
                phase,
                2.5 + 1.5 * language.activity,
                1.2 + energy * 0.8,
            )
        )
    return Scene(profile.username, tuple(ships), energy, layout_seed)

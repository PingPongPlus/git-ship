"""Fresh per-render placements within six non-overlapping motion envelopes."""

from __future__ import annotations

import math
import random
import secrets
from dataclasses import dataclass

from .config import WIDTH, Config
from .model import Language, Profile, global_activity, rank_languages
from .sprites import Style, language_style, stable_seed


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
    # Two rows leave room for the full 56-pixel sprite, wake, bob and smoke.
    # Three wide columns preserve native lettering and cargo at six ships.
    cells = rng.sample([(column, row) for row in range(2) for column in range(3)], len(languages))
    column_width = (WIDTH - 86) / 3
    ships = []
    for language, (column, row) in zip(languages, cells, strict=True):
        width = min(round(44 + 16 * math.sqrt(language.share)), 62)
        left = 80 + column * column_width
        x = rng.randint(math.ceil(left + 8), math.floor(left + column_width - width - 8))
        y = (9 if row == 0 else 83) + rng.randrange(6)
        phase = (stable_seed(f"{identity}:{language.name}") % 1024) / 1024
        ships.append(
            Ship(
                language,
                language_style(language.name, config),
                x,
                y,
                width,
                phase,
                2.5 + 1.5 * language.activity,
                1.2 + energy * 0.8,
            )
        )
    return Scene(profile.username, tuple(ships), energy, layout_seed)

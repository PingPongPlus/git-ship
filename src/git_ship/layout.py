"""Deterministic slots bound the complete motion, smoke and wake envelopes."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .config import Config
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


def layout(profile: Profile, config: Config) -> Scene:
    languages = rank_languages(profile, config)[: config.ships]
    energy = global_activity(profile)
    seed = stable_seed(str(config.seed) if config.seed is not None else profile.username.casefold())
    slot = 318 / max(1, len(languages))
    ships = []
    # Hull baselines, with enough room for the tallest mast and rising smoke.
    baselines = (121, 91, 129, 108, 125)
    for i, language in enumerate(languages):
        width = min(round(44 + 16 * math.sqrt(language.share)), int(slot) - 20, 62)
        phase = ((seed >> (i * 8)) % 256) / 256
        ships.append(
            Ship(
                language,
                language_style(language.name, config),
                round(76 + i * slot + (slot - width) / 2),
                baselines[i] - 52,
                width,
                phase,
                2.5 + 1.5 * language.activity,
                1.2 + energy * 0.8,
            )
        )
    return Scene(profile.username, tuple(ships), energy)

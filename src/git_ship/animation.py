"""Periodic independent sprite motion and finite-life binary-alpha particles."""

from __future__ import annotations

import math
from dataclasses import dataclass

from PIL import Image, ImageDraw

from .config import HEIGHT, WIDTH, Config
from .layout import Scene, Ship
from .sprites import (
    FOAM,
    FUNNEL_ORIGINS,
    SMOKE,
    SMOKE_LIGHT,
    SMOKE_SHADE,
    WAVE,
    WAVE_DEEP,
    lighthouse_sprite,
    ship_sprite,
)

TAU = math.tau


@dataclass(frozen=True)
class Motion:
    x: int
    y: int


def ship_motion(ship: Ship, t: float) -> Motion:
    phase = TAU * ((t + ship.phase) % 1)
    return Motion(
        ship.x + round(ship.drift * math.sin(phase)),
        ship.y + round(ship.bob * math.sin(2 * phase)),
    )


def wave(d: ImageDraw.ImageDraw, x: int, y: int, length: int, crest: int = 0) -> None:
    """A short stepped blue wake with a foamy crest, on otherwise empty space."""
    d.polygon(
        [
            (x + 1, y + 2),
            (x + length - 3, y + 2),
            (x + length - 3, y + 3),
            (x + length - 1, y + 3),
            (x + length - 1, y + 4),
            (x + 5, y + 4),
            (x + 5, y + 3),
            (x + 1, y + 3),
        ],
        fill=WAVE_DEEP,
    )
    d.rectangle((x, y + 1, x + length - 1, y + 2), fill=WAVE)
    d.rectangle((x + 1, y - 1, x + 3, y + 1), fill=WAVE)
    d.rectangle((x + 2, y, x + length - 4, y + 2), fill=WAVE)
    peak = x + length // 3 + crest
    d.rectangle((peak - 2, y - 1, peak + 4, y), fill=FOAM)
    d.rectangle((peak, y - 3, peak + 2, y - 1), fill=FOAM)
    d.rectangle((peak + 3, y - 2 + crest, peak + 4, y - 1), fill=FOAM)
    d.rectangle((peak + 2, y + 1, peak + 6, y + 1), fill=FOAM)
    d.line((x + length - 3, y + 1, x + length - 2, y + 1), fill=FOAM)


def smoke_puff(d: ImageDraw.ImageDraw, x: int, bottom: int, age: float) -> None:
    """Small stepped puffs grow, rise and shrink without alpha fading."""
    radius = 1 if age < 0.14 or age > 0.7 else 2
    d.rectangle((x - radius, bottom - 2 * radius + 1, x + radius, bottom - 1), fill=SMOKE_SHADE)
    d.rectangle((x - radius + 1, bottom - 2 * radius, x + radius - 1, bottom), fill=SMOKE)
    d.rectangle((x - radius + 1, bottom - 2 * radius, x + 1, bottom - radius), fill=SMOKE_LIGHT)


class Animator:
    def __init__(self, scene: Scene, config: Config) -> None:
        self.scene, self.config = scene, config
        self.sprites = tuple(
            ship_sprite(s.style, s.width, s.language.cargo or 0) for s in scene.ships
        )
        self.lights = (lighthouse_sprite(False), lighthouse_sprite(True))

    def frame(self, t: float) -> Image.Image:
        """t is loop phase in [0, 1); frame(0) == frame(1), no final hold."""
        t %= 1
        image = Image.new("RGBA", (WIDTH, HEIGHT))
        d = ImageDraw.Draw(image)
        image.alpha_composite(self.lights[int(math.sin(TAU * t * 2) > -0.55)], (17, 27))
        for j, (x, y) in enumerate(((15, 106), (51, 105))):
            p = (t * 2 + j * 0.5) % 1
            if 0.12 < p < 0.88:
                wave(d, x + int(p * 2), y, 10 + int(3 * math.sin(math.pi * p)), int(p * 4) % 2)
        for ship, sprite in zip(self.scene.ships, self.sprites, strict=True):
            m = ship_motion(ship, t)
            # Periodic mooring motion, always the same heading: right-facing
            # boats surge forward and gently ease astern; never mirror names.
            for j in range(3):
                p = (t * 3 + ship.phase + j / 3) % 1
                if 0.08 < p < 0.78:
                    x = m.x + (-2, ship.width // 2 - 8, ship.width - 11)[j] - int(p * 3)
                    # End crests tuck behind the hull; the middle patch sits
                    # below the keel. Their gaps keep the sea fully transparent.
                    y = m.y + (52, 55, 52)[j] + int(p * 2)
                    wave(d, x, y, 11 + round(5 * math.sin(math.pi * p)), int(p * 4) % 2)
            if ship.style.design in ("steam", "tug"):
                funnel, mouth = FUNNEL_ORIGINS[ship.style.design]
                # Three complete particle cycles per loop; no alpha fading or matte.
                for j in range(2):
                    p = (t * 3 + ship.phase + j * 0.5) % 1
                    if p < 0.86:
                        sx = m.x + funnel + 3 - round(p * 7)
                        bottom = m.y + mouth - 1 - round(p * 11)
                        smoke_puff(d, sx, bottom, p)
            # Cargo and the hull occlude smoke drifting behind them.
            image.alpha_composite(sprite, (m.x, m.y))
        if self.config.scale != 1:
            image = image.resize(
                (WIDTH * self.config.scale, HEIGHT * self.config.scale), Image.Resampling.NEAREST
            )
        return image

    def frames(self) -> list[Image.Image]:
        count = self.config.fps * self.config.duration
        return [self.frame(i / count) for i in range(count)]

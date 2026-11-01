"""Periodic independent sprite motion and finite-life binary-alpha particles."""

from __future__ import annotations

import math
from dataclasses import dataclass

from PIL import Image, ImageDraw

from .config import HEIGHT, WIDTH, Config
from .huge_ship import draw_heavy_water, huge_cargo_counts, huge_ship_sprite
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
from .watermark import draw_watermark

TAU = math.tau
LIGHT_ORIGIN = (38, 47)
BEAM_LIGHT = "#ffe15b"
BEAM_RGB = (255, 225, 91)
BEAM_TINT = 0.3


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


def lighthouse_beam(image: Image.Image, t: float) -> None:
    """Fill empty space yellow and blend that light over existing artwork."""
    angle = TAU * (t % 1)
    facing = math.cos(angle)
    depth = abs(facing)
    reach = round(354 * facing)
    # Foreshortening collapses the fan as the lamp points toward/away from us.
    # Its tilt and widening tip distinguish a turning lamp from a blinking ray.
    if abs(reach) < 4:
        return
    x, y = LIGHT_ORIGIN
    tip_x = x + reach
    tip_y = y + round((20 + 65 * math.sin(angle)) * depth)
    spread = max(1, round(24 * depth))
    vertices = [(x, y), (tip_x, tip_y - spread), (tip_x, tip_y + spread)]
    mask = Image.new("1", image.size)
    ImageDraw.Draw(mask).polygon(vertices, fill=1)
    bounds = mask.getbbox()
    if bounds is None:
        return
    left, top, right, bottom = bounds
    pixels, inside = image.load(), mask.load()
    # GIF supports binary alpha. Composite the translucent yellow onto existing
    # colors here, preserving the exact same appearance in GIF and PNG. A fixed
    # blend gives each art color one lit counterpart across the entire loop.
    for py in range(top, bottom):
        for px in range(left, right):
            if not inside[px, py]:
                continue
            previous = pixels[px, py]
            color = (
                tuple(
                    round(base * (1 - BEAM_TINT) + light * BEAM_TINT)
                    for base, light in zip(previous[:3], BEAM_RGB, strict=True)
                )
                if previous[3]
                else BEAM_RGB
            )
            pixels[px, py] = (*color, 255)


class Animator:
    def __init__(self, scene: Scene, config: Config) -> None:
        if config.huge_cargo_ship != (scene.total_commits is not None):
            raise ValueError("scene and render mode differ; rebuild the scene with layout()")
        if config.huge_cargo_ship:
            counts = huge_cargo_counts(scene.total_commits)
            if (
                scene.ships
                or bool(counts["total"]) != (scene.huge_ship is not None)
                or (
                    scene.huge_ship is not None and scene.huge_ship.total_commits != counts["total"]
                )
            ):
                raise ValueError("aggregate scene has inconsistent ship or commit data")
        elif scene.huge_ship is not None:
            raise ValueError("huge ship data requires huge-cargo-ship mode")
        self.scene, self.config = scene, config
        self.sprites = tuple(
            ship_sprite(s.style, s.width, s.language.cargo or 0) for s in scene.ships
        )
        self.lights = (lighthouse_sprite(False), lighthouse_sprite(True))
        self.huge_sprite = (
            huge_ship_sprite(scene.huge_ship.total_commits) if scene.huge_ship else None
        )

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
        if self.scene.huge_ship is not None:
            vessel = self.scene.huge_ship
            phase = (t + vessel.phase) % 1
            x = vessel.x + round(math.sin(TAU * phase))
            y = vessel.y + round(0.65 * math.sin(TAU * phase))
            draw_heavy_water(d, x, y, phase)
            assert self.huge_sprite is not None
            image.alpha_composite(self.huge_sprite, (x, y))
            draw_heavy_water(d, x, y, phase, foreground=True)
        for ship, sprite in zip(self.scene.ships, self.sprites, strict=True):
            m = ship_motion(ship, t)
            if ship.style.design == "trawler":
                # The line pivots from the fixed boom tip; only the hanging
                # hook sways. One cycle closes exactly at the animation seam.
                amplitude = 1 if ship.width < 50 else 2
                sway = round(amplitude * math.sin(TAU * (t + ship.phase)))
                sprite = ship_sprite(
                    ship.style, ship.width, ship.language.cargo or 0, hook_sway=sway
                )
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
        if self.config.lighthouse_beam:
            lighthouse_beam(image, t)
        if self.config.watermark:
            draw_watermark(image, self.config.activity_window)
        if self.config.scale != 1:
            image = image.resize(
                (WIDTH * self.config.scale, HEIGHT * self.config.scale), Image.Resampling.NEAREST
            )
        return image

    def frames(self) -> list[Image.Image]:
        count = self.config.fps * self.config.duration
        return [self.frame(i / count) for i in range(count)]

"""Approved pixel rain and short-lived surface ripples on the native grid."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from PIL import Image, ImageDraw

from .config import HEIGHT, WIDTH
from .layout import Scene
from .sprites import stable_seed
from .watermark import COMMIT_FOOTER_HEIGHT

STREAK = "#527f95"
DROP_COLOR = "#92c4d2"
RIPPLE = "#70b3ce"
DEEP = "#39799c"
FOAM = "#c3dde2"


@dataclass(frozen=True)
class Drop:
    x: int
    y: int
    phase: float


def impact(draw: ImageDraw.ImageDraw, x: int, y: int, age: float) -> None:
    """The approved tap expands into a broken miniature ripple, then clears."""
    if age < 0.2:
        draw.point((x, y - 1), fill=FOAM)
        draw.line((x - 1, y, x + 1, y), fill=RIPPLE)
        if age > 0.06:
            draw.point((x - 2, y - 1), fill=DROP_COLOR)
            draw.point((x + 2, y - 1), fill=DROP_COLOR)
        return
    radius = 2 + round((age - 0.2) / 0.8 * 4)
    color = RIPPLE if age < 0.65 else DEEP
    draw.line((x - radius, y, x - radius + 1, y), fill=color)
    draw.line((x + radius - 1, y, x + radius, y), fill=color)
    if age < 0.7:
        draw.line((x - radius + 2, y - 1, x + radius - 2, y - 1), fill=RIPPLE)
        draw.line((x - radius + 2, y + 1, x + radius - 2, y + 1), fill=DEEP)


def blocked_water(scene: Scene, *, vertical_offset: int = 0) -> Image.Image:
    """Reserve land and full moving hull envelopes, including transparent gaps."""
    mask = Image.new("L", (WIDTH, HEIGHT + vertical_offset))
    d = ImageDraw.Draw(mask)
    d.rectangle((15, 25 + vertical_offset, 64, 106 + vertical_offset), fill=255)
    for ship in scene.ships:
        drift, bob = math.ceil(ship.drift), math.ceil(ship.bob)
        d.rectangle(
            (
                ship.x - drift - 2,
                ship.y - bob - 2,
                ship.x + ship.width + drift + 2,
                ship.y + 54 + bob,
            ),
            fill=255,
        )
    if scene.huge_ship:
        ship = scene.huge_ship
        d.rectangle(
            (ship.x - 2, ship.y - 2, ship.x + 302, ship.y + 103 + vertical_offset), fill=255
        )
    if scene.fleet_commits is not None:
        d.rectangle((0, HEIGHT - COMMIT_FOOTER_HEIGHT, WIDTH - 1, HEIGHT - 1), fill=255)
    return mask


def rain_drops(scene: Scene, *, vertical_offset: int = 0) -> tuple[Drop, ...]:
    """Independent seeded weather never changes the scene's layout or cargo."""
    blocked = blocked_water(scene, vertical_offset=vertical_offset)
    rng = random.Random(stable_seed(f"{scene.layout_seed}:rain"))
    drops = []
    for _ in range(44):
        for _ in range(1000):
            x = rng.randint(10, WIDTH - 11)
            y = rng.randint(91, HEIGHT - 11) + vertical_offset
            if blocked.crop((x - 6, y - 2, x + 7, y + 2)).getbbox() is None:
                drops.append(Drop(x, y, rng.random()))
                break
    return tuple(drops)


def draw_rain(base: Image.Image, drops: tuple[Drop, ...], t: float) -> Image.Image:
    """Rain falls behind art; impacts only touch currently transparent ocean."""
    rain = Image.new("RGBA", base.size)
    surface = Image.new("RGBA", base.size)
    d, s = ImageDraw.Draw(rain), ImageDraw.Draw(surface)
    for drop in drops:
        phase = ((t % 1) * 5 + drop.phase) % 1
        if phase < 0.68:
            progress = phase / 0.68
            hx = round(drop.x + (1 - progress) * 18)
            hy = round(-10 + (drop.y + 10) * progress)
            d.line((hx + 1, hy - 4, hx, hy - 1), fill=STREAK)
            d.point((hx, hy), fill=DROP_COLOR)
        elif phase < 0.96:
            impact(s, drop.x, drop.y, (phase - 0.68) / 0.28)
    rain.alpha_composite(base)
    clear = base.getchannel("A").point(lambda a: 255 - a)
    rain.paste(
        surface, (0, 0), Image.composite(surface.getchannel("A"), Image.new("L", base.size), clear)
    )
    return rain

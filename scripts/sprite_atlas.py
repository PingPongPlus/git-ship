"""Regenerate a transparent atlas of the original independently movable sprites."""

from importlib.resources import as_file, files
from pathlib import Path

from PIL import Image

from git_ship.config import Config
from git_ship.layout import layout
from git_ship.model import Profile
from git_ship.sprites import lighthouse_sprite, ship_sprite

with as_file(files("git_ship").joinpath("assets/demo.json")) as path:
    fleet = layout(Profile.read(path), Config())
atlas = Image.new("RGBA", (60 + 70 * len(fleet.ships), 100))
atlas.alpha_composite(lighthouse_sprite(), (4, 4))
for i, ship in enumerate(fleet.ships):
    atlas.alpha_composite(ship_sprite(ship.style, 60, ship.language.cargo or 0), (60 + i * 70, 20))
atlas.resize((atlas.width * 2, 200), Image.Resampling.NEAREST).save(
    Path("artwork/sprite-atlas.png")
)

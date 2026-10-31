from PIL import ImageColor

from git_ship.animation import Animator
from git_ship.config import Config
from git_ship.layout import Scene, Ship
from git_ship.model import Language
from git_ship.sprites import GOLD, INK, language_style


def test_trawler_hook_swings_from_fixed_boom_without_moving_cargo_or_label():
    config = Config(scale=1, lighthouse_beam=False, watermark=False)
    language = Language("Java", 100, 1.0, 0.0, 20)
    ship = Ship(
        language, language_style("Java", config, design="trawler"), 200, 40, 60, 0.0, 0.0, 0.0
    )
    animator = Animator(Scene("sailor", (ship,), 0.0), config)
    right, left = animator.frame(0.25), animator.frame(0.75)
    gold = (*ImageColor.getrgb(GOLD), 255)
    ink = (*ImageColor.getrgb(INK), 255)
    assert right.getpixel((242, 73)) == gold
    assert left.getpixel((238, 73)) == gold
    assert right.getpixel((240, 60)) == left.getpixel((240, 60)) == ink
    assert right.crop((221, 60, 244, 77)).tobytes() != left.crop((221, 60, 244, 77)).tobytes()
    assert right.crop((203, 50, 220, 78)).tobytes() == left.crop((203, 50, 220, 78)).tobytes()
    assert right.crop((208, 81, 250, 90)).tobytes() == left.crop((208, 81, 250, 90)).tobytes()
    assert animator.frame(0).tobytes() == animator.frame(1).tobytes()

import hashlib
from dataclasses import replace

import pytest
from PIL import Image, ImageChops, ImageColor

from git_ship.animation import Animator, ship_motion
from git_ship.config import Config
from git_ship.export import export, indexed_frames
from git_ship.layout import layout
from git_ship.model import Commit, Repository
from git_ship.sprites import FUNNEL_ORIGINS, language_style, ship_sprite


@pytest.mark.parametrize("name", ["Java", "Rust"])
def test_chimneys_connect_to_the_deck_at_every_ship_width(name):
    style = language_style(name, Config())
    funnel, mouth = FUNNEL_ORIGINS[style.design]
    for width in range(43, 63):
        alpha = ship_sprite(style, width).getchannel("A")
        assert all(alpha.getpixel((funnel + 3, y)) == 255 for y in range(mouth, 41))


def test_labels_real_names_and_bounded_sizing(demo):
    config = Config(ships=5)
    for name in ("C++", "C#", "Objective-C", "Jupyter Notebook", "Some Long Language", "F#"):
        style = language_style(name, config)
        assert 1 <= len(style.label) <= 6
        sprite = ship_sprite(style, 43)
        assert sprite.size == (43, 56)
    assert language_style("C++", config).label == "C++"
    assert language_style("C#", config).label == "C#"
    assert language_style("Haskell", Config(labels={"Haskell": "A B-C#"})).label == "A B-C#"
    repo = Repository(
        "all",
        demo.username,
        False,
        False,
        None,
        {"Java": 10**9, "C++": 5, "Python": 4, "Rust": 3, "F#": 2},
        tuple(
            Commit(f"{i:040x}", demo.username, "2026-09-30T12:00:00Z", (name,))
            for i, name in enumerate(("Java", "C++", "Python", "Rust", "F#"), start=1)
        ),
    )
    scene = layout(replace(demo, repositories=(repo,)), config)
    assert len(scene.ships) == 5
    for s in scene.ships:
        assert 43 <= s.width <= 62


def test_six_character_names_stay_on_opaque_hull_panels():
    for name in ("Java", "C++", "Python", "Rust"):
        style = replace(language_style(name, Config()), label="MMMMMM")
        for width in range(43, 63):
            labeled = ship_sprite(style, width)
            blank = ship_sprite(replace(style, label="      "), width)
            assert not ImageChops.subtract(
                labeled.getchannel("A"), blank.getchannel("A")
            ).getbbox(), (name, width)
            for painted, underlying in zip(
                labeled.get_flattened_data(), blank.get_flattened_data(), strict=True
            ):
                if painted != underlying:
                    assert underlying == (*ImageColor.getrgb(style.hull), 255), (name, width)


def test_deterministic_periodic_motion_and_independent_objects(demo):
    config = Config(scale=1, seed="motion-test")
    scene = layout(demo, config)
    assert scene == layout(demo, config)
    assert scene != layout(demo, replace(config, seed="another"))
    animation = Animator(scene, config)
    assert animation.frame(0).tobytes() == animation.frame(1).tobytes()
    assert animation.frame(0.25).tobytes() == Animator(scene, config).frame(0.25).tobytes()
    positions = {ship_motion(scene.ships[0], i / 100).x for i in range(100)}
    assert max(positions) - min(positions) >= 6
    assert len({ship_motion(s, 0.25) for s in scene.ships}) == 6
    # The seam is one ordinary timestep, not a teleport.
    frames = animation.frames()
    changes = [
        sum(1 for p in ImageChops.difference(a, b).get_flattened_data() if any(p))
        for a, b in zip(frames, frames[1:] + frames[:1], strict=True)
    ]
    assert changes[-1] <= max(changes[:-1])


def test_export_decoded_palette_alpha_timing_and_cleanup(demo, tmp_path):
    config = Config(seed="export-test", lighthouse_beam=False)
    report, intended = export(layout(demo, config), config, tmp_path)
    assert report["decoded_frames_match"]
    assert report["min_transparent_fraction"] >= 0.8
    assert report["gif_bytes"] < 2_000_000
    with Image.open(tmp_path / "git-ship.png") as png:
        assert png.mode == "RGBA" and png.size == (800, 320)
        assert png.tobytes() == intended[0].tobytes()
        assert set(png.getchannel("A").tobytes()) == {0, 255}
    with Image.open(tmp_path / "git-ship.gif") as gif:
        assert gif.n_frames == 100 and gif.info["transparency"] == 0
        decoded = []
        for i in range(gif.n_frames):
            gif.seek(i)
            assert gif.info["duration"] == 100 and gif.disposal_method == 2
            decoded.append(gif.convert("RGBA"))
        assert len({hashlib.sha256(f.tobytes()).hexdigest() for f in decoded}) > 50
        vacated = ImageChops.subtract(decoded[0].getchannel("A"), decoded[25].getchannel("A"))
        assert vacated.getbbox()  # Objects really moved, and their old pixels cleared.
        assert decoded[25].getchannel("A").histogram() == intended[25].getchannel("A").histogram()
    first = (tmp_path / "git-ship.gif").read_bytes()
    export(layout(demo, config), config, tmp_path)
    assert (tmp_path / "git-ship.gif").read_bytes() == first


@pytest.mark.parametrize("count", [0, 1, 2, 6])
def test_empty_quiet_and_small_fleets_still_animate(demo, tmp_path, count):
    config = Config(ships=count, scale=1, duration=2, fps=25)
    profile = replace(demo, contributions=0)
    report, frames = export(layout(profile, config), config, tmp_path)
    assert report["frames"] == 50 and report["duration_seconds"] == 2
    assert report["min_transparent_fraction"] >= 0.7
    assert len({f.tobytes() for f in frames}) > 1
    empty = replace(demo, repositories=())
    assert layout(empty, config).ships == ()


def test_shared_palette_preserves_opaque_black():
    a = Image.new("RGBA", (2, 1))
    a.putpixel((0, 0), (0, 0, 0, 255))
    indexed = indexed_frames([a])[0]
    assert indexed.getpixel((0, 0)) != 0
    assert indexed.getpixel((1, 0)) == 0

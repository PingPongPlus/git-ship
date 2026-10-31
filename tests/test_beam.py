from dataclasses import replace

from PIL import Image, ImageChops, ImageColor

from git_ship.animation import BEAM_LIGHT, BEAM_SHADE, LIGHT_ORIGIN, Animator, lighthouse_beam
from git_ship.config import Config
from git_ship.export import export
from git_ship.layout import layout


def test_rotating_beam_sweeps_foreshortens_and_has_an_exact_loop():
    frames = []
    for t in (0, 0.125, 0.25, 0.5, 0.875, 1):
        image = Image.new("RGBA", (400, 160))
        lighthouse_beam(image, t)
        frames.append(image)
        assert set(image.getchannel("A").tobytes()) <= {0, 255}
        assert image.getchannel("A").histogram()[0] / (400 * 160) > 0.96
    assert frames[0].tobytes() == frames[-1].tobytes()
    assert frames[2].getbbox() is None  # End-on projection collapses at a quarter turn.
    assert frames[0].getbbox()[2] > 380
    assert frames[3].getbbox()[2] <= LIGHT_ORIGIN[0] + 1
    assert frames[1].getbbox()[3] > frames[0].getbbox()[3]
    assert len({image.tobytes() for image in frames[:-1]}) == 5
    assert frames[0].getpixel(LIGHT_ORIGIN)[3] == 255


def test_beam_toggle_preserves_lighthouse_and_ship_art(demo):
    config = Config(scale=1, seed="beam-toggle", lighthouse_beam=False)
    scene = layout(demo, config)
    dark = Animator(scene, config)
    lit = Animator(scene, replace(config, lighthouse_beam=True))
    beam_colors = {(*ImageColor.getrgb(color), 255) for color in (BEAM_LIGHT, BEAM_SHADE)}
    assert lit.frame(0).tobytes() == lit.frame(1).tobytes()
    for t in (0, 0.1, 0.375, 0.8):
        before, after = dark.frame(t), lit.frame(t)
        # Ray is behind the complete scene: every existing opaque sprite,
        # label, ripple and smoke pixel is preserved exactly.
        difference = ImageChops.difference(before.convert("RGB"), after.convert("RGB"))
        assert not ImageChops.multiply(difference, before.getchannel("A").convert("RGB")).getbbox()
    assert not any(pixel in beam_colors for pixel in dark.frame(0).get_flattened_data())
    assert any(pixel in beam_colors for pixel in lit.frame(0).get_flattened_data())


def test_beam_exports_with_exact_palette_cleanup_and_transparent_background(demo, tmp_path):
    config = Config(scale=1, duration=2, seed="beam-export", lighthouse_beam=True)
    report, frames = export(layout(demo, config), config, tmp_path)
    assert report["decoded_frames_match"]
    assert report["min_transparent_fraction"] >= 0.8
    assert all(set(frame.getchannel("A").tobytes()) == {0, 255} for frame in frames)

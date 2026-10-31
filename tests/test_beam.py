from dataclasses import replace

from PIL import Image, ImageColor

from git_ship.animation import BEAM_LIGHT, LIGHT_ORIGIN, Animator, lighthouse_beam
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
        assert image.getchannel("A").histogram()[0] / (400 * 160) > 0.85
        assert image.getcolors() is not None
        assert all(
            not color[3] or color[:3] == ImageColor.getrgb(BEAM_LIGHT)
            for _, color in image.getcolors()
        )
    assert frames[0].tobytes() == frames[-1].tobytes()
    assert frames[2].getbbox() is None  # End-on projection collapses at a quarter turn.
    assert frames[0].getbbox()[2] > 380
    assert frames[3].getbbox()[2] <= LIGHT_ORIGIN[0] + 1
    assert frames[1].getbbox()[3] > frames[0].getbbox()[3]
    assert len({image.tobytes() for image in frames[:-1]}) == 5
    assert frames[0].getpixel(LIGHT_ORIGIN)[3] == 255


def test_beam_is_solid_over_empty_space_and_translucent_over_colored_pixels():
    empty = Image.new("RGBA", (400, 160))
    colored = Image.new("RGBA", (400, 160), (40, 80, 120, 255))
    lighthouse_beam(empty, 0)
    lighthouse_beam(colored, 0)
    assert empty.getpixel((200, 55)) == (255, 225, 91, 255)
    assert colored.getpixel((200, 55)) == (104, 124, 111, 255)
    assert colored.getpixel((200, 150)) == (40, 80, 120, 255)
    assert empty.crop((198, 54, 203, 58)).getchannel("A").histogram()[255] == 20


def test_beam_toggle_blends_light_over_lighthouse_and_ship_art(demo):
    config = Config(scale=1, seed="beam-toggle", lighthouse_beam=False, watermark=False)
    scene = layout(demo, config)
    dark = Animator(scene, config)
    lit = Animator(scene, replace(config, lighthouse_beam=True))
    beam_color = (*ImageColor.getrgb(BEAM_LIGHT), 255)
    assert lit.frame(0).tobytes() == lit.frame(1).tobytes()
    for t in (0, 0.1, 0.375, 0.8):
        before, after = dark.frame(t), lit.frame(t)
        mask = Image.new("RGBA", before.size)
        lighthouse_beam(mask, t)
        tinted = 0
        for original, illuminated, ray in zip(
            before.get_flattened_data(),
            after.get_flattened_data(),
            mask.get_flattened_data(),
            strict=True,
        ):
            if not ray[3]:
                assert illuminated == original
            elif original[3]:
                # Existing shape/color survives under 30% yellow light.
                assert illuminated == (
                    *(
                        round(base * 0.7 + yellow * 0.3)
                        for base, yellow in zip(original[:3], beam_color[:3], strict=True)
                    ),
                    255,
                )
                tinted += illuminated != original
            else:
                assert illuminated == beam_color
        if t in (0, 0.1):
            assert tinted > 0
    assert beam_color not in dark.frame(0).get_flattened_data()
    assert beam_color in lit.frame(0).get_flattened_data()


def test_beam_exports_with_exact_palette_cleanup_and_transparent_background(demo, tmp_path):
    config = Config(scale=1, duration=2, seed="beam-export", lighthouse_beam=True)
    report, frames = export(layout(demo, config), config, tmp_path)
    assert report["decoded_frames_match"]
    assert report["min_transparent_fraction"] >= 0.7
    assert all(set(frame.getchannel("A").tobytes()) == {0, 255} for frame in frames)

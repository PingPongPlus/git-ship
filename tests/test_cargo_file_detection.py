from dataclasses import replace

import pytest
from PIL import Image, ImageDraw

from git_ship.cargo_art import container
from git_ship.config import Config
from git_ship.font import paint_text
from git_ship.huge_ship import huge_ship_sprite, language_cargo_plan
from git_ship.languages import file_language
from git_ship.layout import layout
from git_ship.model import commit_filter_signature


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("README.md", "Markdown"),
        ("SECURITY.md", "Markdown"),
        (".github/workflows/git-ship.yml", "YAML"),
        ("action.yaml", "YAML"),
        ("build.gradle", "Gradle"),
        ("Main.java", "Java"),
        ("deleted.py", "Python"),
        ("config.json", "JSON"),
        ("Cargo.toml", "TOML"),
        ("image.png", None),
        ("unknown.blah", None),
        ("header.h", None),
    ],
)
def test_huge_detection_identifies_files_even_when_excluded_from_repository_bytes(
    filename, expected
):
    assert file_language(filename, {}, allow_unreported=True) == expected
    assert file_language(filename, {}) is None  # Existing fleet attribution is unchanged.


def test_repository_languages_still_resolve_ambiguous_extensions():
    assert file_language("header.h", {"C++": 100}, allow_unreported=True) == "C++"


def test_markdown_label_is_readable_instead_of_an_unclassified_git_box():
    actual = container("Markdown")
    expected = Image.new("RGBA", (27, 10), "#10212e")
    draw = ImageDraw.Draw(expected)
    draw.rectangle((1, 1, 25, 8), fill="#788e98")
    paint_text(draw, (8, 2), "MD", "#f3e8c9")
    assert actual.tobytes() == expected.tobytes()


def test_old_primary_caches_require_refetching_for_corrected_detection(demo):
    config = Config(huge_cargo_ship=True, cargo_logos=True)
    old = replace(
        demo,
        commit_coverage="complete-primary-language",
        cargo_window=30,
        observed_at="2026-10-01T23:59:59.999999+00:00",
        commit_filters=commit_filter_signature(config),
    )
    with pytest.raises(ValueError, match="fresh profile"):
        layout(old, config)


def test_language_groups_fill_adjacent_supported_stacks_instead_of_scattered_center_rows():
    counts = (("Markdown", 42), ("Python", 12), ("Java", 6))
    plan = language_cargo_plan(60, counts)
    actual = huge_ship_sprite(60, counts)
    for index, box in enumerate(plan["large"]):
        column, tier = divmod(index, 2)
        x, y = 72 + column * 28, 66 - tier * 10
        assert actual.crop((x, y, x + 27, y + 10)).tobytes() == container(box["label"]).tobytes()

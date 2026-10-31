from collections import Counter
from dataclasses import replace

import pytest

from git_ship.config import Config
from git_ship.export import export
from git_ship.layout import layout
from git_ship.sprites import SHIP_DESIGNS, language_style, ship_sprite


def test_each_language_can_use_every_existing_ship_design(demo):
    designs = {ship.language.name: set() for ship in layout(demo, Config(seed=0)).ships}
    # A language's data/color identity stays intact as its physical ship changes.
    for seed in range(50):
        for ship in layout(demo, Config(seed=seed)).ships:
            designs[ship.language.name].add(ship.style.design)
            base = language_style(ship.language.name, Config())
            assert (ship.style.label, ship.style.hull, ship.style.trim) == (
                base.label,
                base.hull,
                base.trim,
            )
    assert all(found == set(SHIP_DESIGNS) for found in designs.values())


def test_fleet_uses_every_design_before_repeating_and_honors_custom_labels(demo):
    config = Config(seed="mixed-fleet", labels={"Java": "CUSTOM"}, colors={"Java": "#123456"})
    scene = layout(demo, config)
    chosen = [ship.style.design for ship in scene.ships]
    assert len(set(chosen[: len(SHIP_DESIGNS)])) == min(len(chosen), len(SHIP_DESIGNS))
    assert max(Counter(chosen).values()) <= 2
    java = next(ship for ship in scene.ships if ship.language.name == "Java")
    assert java.style.label == "CUSTOM" and java.style.hull == "#123456"
    assert java.language.cargo == 7


def test_design_assignment_does_not_depend_on_placement_retries(demo):
    config = Config(seed="independent-shapes")
    with_header = layout(demo, config)
    without_header = layout(demo, replace(config, watermark=False))
    assert [ship.style.design for ship in with_header.ships] == [
        ship.style.design for ship in without_header.ships
    ]


def test_recorded_seed_replays_positions_designs_and_cargo(demo, tmp_path):
    config = Config(seed="record-the-whole-fleet", scale=1, duration=2)
    scene = layout(demo, config)
    report, _ = export(scene, config, tmp_path)
    replay = layout(demo, replace(config, seed=report["layout_seed"]))
    assert replay == scene
    assert [language["design"] for language in report["languages"]] == [
        ship.style.design for ship in scene.ships
    ]


def test_unknown_ship_design_is_rejected_instead_of_becoming_a_sailboat():
    style = replace(language_style("Java", Config()), design="unapproved-design")
    with pytest.raises(ValueError, match="unknown ship design"):
        ship_sprite(style, 60, 20)

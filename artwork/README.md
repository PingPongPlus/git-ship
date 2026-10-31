The original editable artwork lives in the installed package:

- `src/git_ship/sprites.py`: lighthouse, rocks, four ship designs, commit cargo, palette and art primitives.
- `src/git_ship/font.py`: original 5×7 bitmap glyphs, including `+`, `#`, spaces and hyphens.
- `src/git_ship/assets/languages.json`: the single language/style/abbreviation mapping.
- `src/git_ship/animation.py`: separate transient wakes, smoke, and lantern states.

Coordinates are logical pixels. All drawing is binary-alpha, integer-grid Pillow
primitives. Integer output scaling uses nearest-neighbor sampling. Hulls can grow
horizontally; text is painted at its native size and never stretched. The concept
reference is never loaded by the renderer. These sources and generated demo art
are covered by the project's MIT license; references are retained for provenance.

Cargo uses a reserved aft-deck area on every design: two columns of five
containers, each representing one distinct authored commit in the selected data
window. Zero known commits means no containers; there are no decorative cargo
blocks. The five-language atlas uses the same fixture counts as the CLI demo,
including the gold JavaScript (`JS`) freighter. Cargo stays inside the sprite and
moves with the hull; labels, funnels, cabin windows and sails remain unobstructed.

Regenerate the editable sprite atlas and demo with:

```sh
python scripts/sprite_atlas.py
git-ship render --demo --preview --output-dir examples/demo
```

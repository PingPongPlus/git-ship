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

Cargo uses a reserved aft-deck bank on every design: three columns, up to seven
tiers and twenty containers total. Each constant-size 5×4-pixel container
represents one distinct authored commit in the selected data window. Zero or
unknown activity means the entire ship is hidden. There are no decorative cargo
blocks. The six-language atlas uses the CLI fixture counts, including the gold JS
freighter, TS and a C++ ship with twenty containers. Cargo stays inside the sprite;
smoke passes behind it, and labels, cabins, funnels and sails remain unobstructed.
Normal renders choose fresh placements within six safe areas. To reproduce the
delivered demo, use `--seed demo`; this fixes positions while keeping the loop
periodic. The atlas itself is independent of scene positions.

Regenerate the editable sprite atlas and demo with:

```sh
python scripts/sprite_atlas.py
git-ship render --demo --seed demo --preview --output-dir examples/demo
```

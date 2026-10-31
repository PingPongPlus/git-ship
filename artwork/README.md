The original editable artwork lives in the installed package:

- `src/git_ship/sprites.py`: lighthouse, rocks, four ship designs, commit cargo, palette and art primitives.
- `src/git_ship/font.py`: original 5×7 bitmap glyphs, including `+`, `#`, spaces and hyphens.
- `src/git_ship/assets/languages.json`: the single language/style/abbreviation mapping.
- `src/git_ship/animation.py`: separate transient wakes, smoke, lantern states and rotating light ray.

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
Normal renders sample fresh positions across the sea while reserving each ship's
full motion envelope. Bounded retries and a randomized packing fallback keep up
to six ships clear of one another and the lighthouse. To reproduce the delivered
demo, use `--seed demo`; this fixes positions while keeping the loop periodic.
The atlas itself is independent of scene positions.

The optional lighthouse ray starts at the lantern and changes projected reach,
tilt and fan width over one exact loop, creating the impression of a rotating
lamp. It fills empty space with solid yellow and is applied after the scene's
artwork. Where it crosses an existing opaque pixel, RGB is blended at 30% yellow
and 70% original color so both the ray and underlying art remain visible. Alpha
stays binary for exact GIF export; pixels outside the cone are unchanged. Set
`lighthouse_beam = false` in TOML, `lighthouse-beam: 'false'` in the action, or
use `--no-lighthouse-beam` to disable it without changing the lantern blink.

Regenerate the editable sprite atlas and demo with:

```sh
python scripts/sprite_atlas.py
git-ship render --demo --seed demo --preview --output-dir examples/demo
```

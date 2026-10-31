The original editable artwork lives in the installed package:

- `src/git_ship/sprites.py`: lighthouse, rocks, seven ship designs, commit cargo, palette and art primitives.
- `src/git_ship/font.py`: original 5×7 bitmap glyphs, including `+`, `#`, spaces and hyphens.
- `src/git_ship/assets/languages.json`: language colors and abbreviations; rendered ship type is assigned separately.
- `src/git_ship/animation.py`: separate transient wakes, smoke, lantern states, rotating light ray and period watermark.

Coordinates are logical pixels. All drawing is binary-alpha, integer-grid Pillow
primitives. Integer output scaling uses nearest-neighbor sampling. Hulls can grow
horizontally; text is painted at its native size and never stretched. The concept
reference is never loaded by the renderer. These sources and generated demo art
are covered by the project's MIT license; references are retained for provenance.

Cargo uses a reserved aft-deck bank on every design: three columns, up to seven
tiers and twenty containers total. Each constant-size 5×4-pixel container
represents one distinct authored commit in the selected data window. Zero or
unknown activity means the entire ship is hidden. There are no decorative cargo
blocks. The six-language atlas uses the CLI fixture's labels, colors and cargo
counts, including JS, TS and a C++ ship with twenty containers. Cargo stays inside the sprite;
smoke passes behind it, and labels, cabins, funnels and sails remain unobstructed.
Normal renders sample fresh positions across the sea while reserving each ship's
full motion envelope. Bounded retries and a randomized packing fallback keep up
to six ships clear of one another and the lighthouse. To reproduce the delivered
demo, use `--seed demo`; this fixes positions and types while keeping the loop
periodic. The atlas uses the same seed for deterministic type assignments and
remains independent of scene positions.

The production pool contains seven shapes: steamship, tug, freighter, sailboat,
ferry, fishing trawler and tanker. The ferry, trawler and tanker pixel art was
approved before integration. Each render shuffles the pool and selects up to six
types without replacement, keeping every visible type unique. The type shuffle is derived separately
from the layout seed. It never changes a language's label, colors, custom
configuration or commit count; shapes are not permanently assigned to languages.

Approved reference PNGs are retained in [ship-designs](ship-designs/):
`ferry-cargo-0.png`, `ferry-cargo-20.png`, `trawler-cargo-0.png`,
`trawler-cargo-20.png`, `tanker-cargo-0.png` and `tanker-cargo-20.png`. The
editable production versions live in `src/git_ship/sprites.py`.

The trawler's rope and hook animate separately from the static hull. The rope
starts at the fixed boom tip while the hook sways by one pixel on narrow hulls
or two on wider ones, staying connected and repeating exactly over the loop.
It is drawn before the lighthouse tint. Only the steamship and tug use smoke
emitters; the smaller posts on the new designs are masts or vents.

The optional lighthouse ray starts at the lantern and changes projected reach,
tilt and fan width over one exact loop, creating the impression of a rotating
lamp. It fills empty space with solid yellow and is applied after the scene's
artwork. Where it crosses an existing opaque pixel, RGB is blended at 30% yellow
and 70% original color so both the ray and underlying art remain visible. Alpha
stays binary for exact GIF export; pixels outside the cone are unchanged. Set
`lighthouse_beam = false` in TOML, `lighthouse-beam: 'false'` in the action, or
use `--no-lighthouse-beam` to disable it without changing the lantern blink.

The optional top-left watermark uses gray lettering in the existing uppercase
pixel font. It reads `GIT-SHIP PAST MONTH COMMIT & SHIPPED CODE` for the month
preset and substitutes the selected day/week/month/year period or custom number
of days. A 14-pixel header reserves space above the ships. It is drawn after the
ray so the lettering keeps its own color. Set `watermark = false` in TOML,
`watermark: 'false'` in the action, or use `--no-watermark` to hide it.

Regenerate the editable sprite atlas and demo with:

```sh
python scripts/sprite_atlas.py
git-ship render --demo --seed demo --preview --output-dir examples/demo
```

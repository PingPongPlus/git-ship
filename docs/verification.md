# Verification record

Local verification: **2026-10-31**, macOS arm64, Python **3.15.0**, Pillow **13.0.0**.
CI covers Python **3.11/3.15** and runs the root composite action with Python **3.13**.
The public destination is [PingPongPlus/git-ship](https://github.com/PingPongPlus/git-ship).
The recorded checks below cover the `dynamic-ships` baseline (`4b01e6d`). The
`shipinclude1year` branch adds a rolling 365-day preset; that new preset is not
covered by these recorded checks. The default branch is unchanged. No `v1` or
Marketplace release is claimed. Hosted results are available under the
repository's Actions tab.

## Commands and results

Commands were run from the project root with its `.venv` unless noted.

| Command | Result |
| --- | --- |
| `/opt/homebrew/bin/python3 -m venv .venv` | Created Python 3.15 environment; the system Python 3.9.6 was too old. |
| `python -m pip install --no-build-isolation -e .` | Package and CLI installed successfully. |
| `ruff check .` / `ruff format --check .` | Passed. |
| `pytest -q` | **78 passed**, with no live API required. |
| `python -m build --no-isolation` | Built wheel and source archive, including JSON mappings, fixtures and the Linguist license. |
| `python -m pip install --no-deps --upgrade --target out/wheel-install dist/git_ship-0.1.0-py3-none-any.whl` | Installed built wheel into an isolated target for verification. |
| From `/private/tmp`, using the absolute interpreter path and `PYTHONPATH=.../out/wheel-install`: `python -m git_ship render --demo --duration 2 --scale 1 --output-dir .../out/wheel-render` | Installed-wheel import/render smoke test; bundled offline assets and mappings work outside the source checkout. |
| `python scripts/sprite_atlas.py` | Generated the six-language transparent sprite atlas, including 20 C++ containers. |
| `git-ship render --demo --seed demo --preview --output-dir examples/demo` | Generated and audited the full six-ship GIF/PNG, preview and contact sheet. |
| Dynamic layout tests | Checked quiet/unknown language filtering, active-language discovery below inactive candidates, the six-ship maximum, new layouts per render and exact seed replay. |
| Full motion-envelope tests | Checked 140 scenes: zero through six fully loaded ships across 20 seeds each; all envelopes remain inside the canvas and disjoint. |
| Fixture time-window tests | Day has no ships; week has JAVA/C++/JS/TS with cargo `[4,6,3,2]`; month has all six with cargo `[7,20,6,4,5,2]`. |
| Ruby `YAML.load_file` on action, CI, caller workflow and Dependabot | All four files parsed successfully. |
| Read-only GitHub CLI repository inspection | Destination verified **PUBLIC**, initially with no branch history. |
| Read-only public commit API call through `GitHubClient.changed_languages` | GitHub's real changed-file response was read and validated; no token supplied or data published. |

Earlier live public-profile smoke testing also fetched octocat's real CSS/HTML/JS
repository data and rendered three ships. Commit and file pagination, attribution,
caps, empty history and selected time windows are covered by deterministic fixtures.
Ordinary tests never depend on GitHub availability or write to a remote service.

## Cargo and time-window contracts

- One unique primary-author commit SHA per classified language becomes one container;
  a mixed-language commit can load several ships, but repeated files/SHAs do not
  multiply a ship's count. The visual cap is twenty.
- A language needs confirmed positive cargo to appear. Zero and unknown counts
  are filtered before selecting at most six languages by code-byte share. No
  qualifying languages means a lighthouse-only scene.
- Only selected public, owned repository/default-branch history is queried. Primary
  authors, UTC committer timestamps, deletes and renames are handled explicitly.
- Live periods are rolling 24-hour, 7-day, 30-day or 365-day windows. Tests at 03:23 UTC include
  yesterday's eligible commits, exclude the exact start boundary and future commits,
  and verify the same interval is passed to the optional contribution query.
- Commit/file pagination follows `Link` headers. Scanning considers every candidate
  until the active fleet and its capped counts are established;
  the 3000-file API limit fails clearly rather than undercounting silently.
- Filename matching uses pinned Linguist extensions/filenames/groups, longest suffix
  matching and repository-byte disambiguation, plus an uppercase `.C` override. It
  deliberately does not claim content-aware Linguist equivalence.
- Schema-1 caches are accepted with unknown cargo. Changing a sampled cache's window
  does not invent a count; ships with unknown activity are hidden with a warning.
- Each design has a reserved cargo bank, clear of rigging, funnels and labels.
  Tests check zero cargo adds no decorative containers and each requested container
  occupies its own non-overlapping 5×4-pixel footprint. Three columns fit up to seven
  tiers and twenty containers total. Zero, one, seven, ten and twenty containers are
  checked at minimum, middle and maximum hull widths.
- Funnel-to-deck continuity and six-character label clearance are checked across all
  supported widths. JavaScript and TypeScript follow the same pipeline as the other
  demo languages. Cargo occludes smoke drifting behind it.
- Each regeneration selects and jitters six safe areas using a fresh seed chosen
  once. Positions remain fixed through the loop. An explicit `--seed` makes the
  complete scene repeatable, and the report records `layout_seed` for replay.

## Action and publishing contracts

The action entry point is executed in tests with the real caller-style environment,
an arbitrary repository owner, `demo: true` and `data-window: day`. Tests inspect
the output window, lighthouse-only daily fixture, generated paths and workspace-escape
rejection. Hosted CI additionally invokes **`uses: ./`**, with `data-window: week`.

The copy-paste caller workflow schedules **daily** independently of the selected data
window. Manual execution exposes day/week/month/year choices; nightly runs read the
optional `GIT_SHIP_DATA_WINDOW` repository variable, defaulting to month. No owner,
profile repository or account credential is hard-coded in generation/publication.

The publisher is tested against a temporary **local bare Git repository**. It creates
only GIF/PNG asset paths on `output`, skips unchanged refreshes, preserves unrelated
output-branch files and leaves the default branch SHA untouched. It refuses to use
`output` when that is the default branch, and performs no force push.

## Current demo measurements

Fixture: `src/git_ship/assets/demo.json`, observed on **2026-10-01**.

| Measurement | Result |
| --- | --- |
| Logical grid / scale | 400×160 / 2× nearest neighbor |
| Export | **800×320 pixels** |
| Timing | **100 frames, 10 fps, 100 ms/frame, 10 seconds** |
| Loop | Infinite; no extra closing-frame hold |
| Layout seed | `demo` |
| GIF | **769,322 bytes**, below 2 MB target |
| PNG | **5,008 bytes**, genuine RGBA |
| Fully transparent pixels over every frame | **85.4453125%–85.7921875%** |
| Alpha / palette / disposal | Binary alpha, one shared palette, transparent index 0, disposal 2 |
| Decoded comparison | All 100 frames exactly match intended alpha and visible RGB |
| Cargo, in report order | JAVA 7 / C++ 20 / PYTHON 6 / RUST 4 / JS 5 / TS 2 |

Delivered art: `examples/demo/git-ship.gif`, `git-ship.png`, `report.json`,
`contact-sheet.png`, `preview.html`, `examples/reduced-motion.html`, and
`artwork/sprite-atlas.png`. Editable sources are documented in `artwork/README.md`.

The approved reference, still compositions and light/dark contact sheets were
inspected during implementation. The initial animation and smoke/wake revision were
also inspected in browser playback on both backgrounds. This revision's six
ships, twenty-container stack, readable labels and smoke clearance were inspected in the
regenerated art/contact sheet. Every exported revision is audited after decoding;
no trails or matte rectangles are accepted. Exact periodicity and seam-step size are
also covered by tests. Rendering twice with an explicit seed is checked for
byte-for-byte determinism; default renders deliberately choose fresh placements.

The local pause button selects PNG, and the recommended `picture` structure was
checked with the browser's no-preference setting and PNG fallback. OS preferences
were not changed. The profile's preceding daily workflow ran successfully and its
live README image embed was checked. Long-running daily scheduling still depends
on GitHub's scheduler. Optional contribution totals can be unavailable to installation
tokens; the documented peaceful fallback is intentional.

No personal access token, account permission change, `v1` release tag, Marketplace
listing, or hosted service is required or created by this implementation. Source
publication and CI are separate from installing the daily workflow in a user's own
profile repository.

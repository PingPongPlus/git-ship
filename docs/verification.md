# Verification record

Local verification: **2026-11-01**, macOS arm64, Python **3.15.0**, Pillow **13.0.0**.
CI covers Python **3.11/3.15** and runs the root composite action with Python **3.13**.
The public destination is [PingPongPlus/git-ship](https://github.com/PingPongPlus/git-ship).
This revision targets `main` and retains the rolling 365-day preset. It fixes
renamed-account commit attribution, samples ship positions across the sea,
shuffles the existing ship types, and includes a configurable rotating lighthouse ray,
period watermark and optional Huge Cargo Ship. No `v1` or Marketplace release is claimed. Hosted results are available under the
repository's Actions tab.

## Commands and results

Commands were run from the project root with its `.venv` unless noted.

| Command | Result |
| --- | --- |
| `/opt/homebrew/bin/python3 -m venv .venv` | Created Python 3.15 environment; the system Python 3.9.6 was too old. |
| `python -m pip install --no-build-isolation -e .` | Package and CLI installed successfully. |
| `ruff check .` / `ruff format --check .` | Passed. |
| `pytest -q` | **312 passed** in 9.09 seconds, with no live API required. |
| `python -m build --no-isolation` | Built wheel and source archive, including JSON mappings, fixtures and the Linguist license. |
| `python -m pip install --no-deps --upgrade --target out/wheel-install dist/git_ship-0.1.0-py3-none-any.whl` | Installed built wheel into an isolated target for verification. |
| From `/private/tmp`, using the absolute interpreter path and `PYTHONPATH=.../out/wheel-install`: `python -m git_ship render --demo --duration 2 --scale 1 --output-dir .../out/wheel-render` | Installed-wheel import/render smoke test; bundled offline assets and mappings work outside the source checkout. |
| `python scripts/sprite_atlas.py` | Generated the six-language transparent sprite atlas, including 20 C++ commits represented by five large containers. |
| `git-ship render --demo --seed demo --preview --output-dir examples/demo` | Generated and audited the full six-ship GIF/PNG, preview and contact sheet. |
| `git-ship render --demo --display-commits --seed counter-preview --preview --output-dir out/commit-counter` | Visually checked bottom-right `44 COMMITS`, with all 100 decoded GIF frames matching; 1,016,346 GIF bytes and 7,209 PNG bytes. |
| `git-ship render --demo --huge-cargo-ship --seed huge-demo --preview --output-dir examples/huge-demo` | Generated and decoded-audited the separate huge-ship demo: 44 distinct fixture commits, seven large and two small containers. |
| Dynamic layout tests | Check quiet/unknown language filtering, active-language discovery below inactive candidates, the six-ship maximum, placement across the sea, new layouts per render and exact seed replay. |
| Full motion-envelope tests | Checked 140 scenes: zero through six fully loaded ships across 20 seeds each; all envelopes remain inside the canvas and disjoint. |
| Dense packing fallback test | Forced the guaranteed-fit path with six maximum-width 62-pixel ships; all full motion envelopes remain inside the canvas and disjoint. |
| Approved ship-art tests | 24 checks cover the ferry, trawler and tanker artwork and cargo configurations; a separate motion test checks the trawler's connected periodic hook. |
| Grouped-cargo tests | Exhaustive counts 0–20 across all seven designs and three hull widths; checks also cover four-commit merge points, large-container `4` marks, weighted report counts and exact GIF cleanup. The focused cargo/approved-art suite passed 94 tests. |
| Fixture time-window tests | Day has no ships; week has JAVA/C++/JS/TS with cargo `[4,6,3,2]`; month has all six with cargo `[7,20,6,4,5,2]`. |
| Ruby `YAML.load_file` on action, CI, caller workflow and Dependabot | All four files parsed successfully. |
| Read-only GitHub CLI repository inspection | Destination verified **PUBLIC**, initially with no branch history. |
| Read-only public commit API call through `GitHubClient.changed_languages` | GitHub's real changed-file response was read and validated; no token supplied or data published. |

Earlier live public-profile smoke testing also fetched octocat's real CSS/HTML/JS
repository data and rendered three ships. Commit and file pagination, attribution,
caps, empty history and selected time windows are covered by deterministic fixtures.
Ordinary tests never depend on GitHub availability or write to a remote service.

## Cargo and time-window contracts

- One unique primary-author commit SHA contributes one unit to each classified
  language; a mixed-language commit can load several ships, but repeated
  files/SHAs do not multiply a ship's count. The display cap is twenty commits.
- Each large container represents four commits and each small container one.
  For a displayed count `n`, the drawing uses `n // 4` large containers and
  `n % 4` small ones. Nine commits become two large plus one small; twenty become
  five large. A `4` marks each large container. The grouping changes neither API
  attribution nor selected windows.
- A language needs confirmed positive cargo to appear. Zero and unknown counts
  are filtered before selecting at most six languages by code-byte share. No
  qualifying languages means a lighthouse-only scene.
- Only selected public, owned repository/default-branch history is queried. Primary
  authors, UTC committer timestamps, deletes and renames are handled explicitly.
- Author identity is checked from returned `author.login` values. The server-side
  `author=username` query is intentionally omitted: it can exclude old noreply
  addresses after an account rename, even when the response resolves those
  commits to the current account. Other users' commits remain excluded.
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
- Each design has a reserved cargo bank at logical `x=3..19`, `y=10..37`, clear
  of rigging, funnels and labels. Small containers use a constant 5×4-pixel
  footprint, large containers 8×7. The large containers stack in two columns and
  up to three tiers; remainder containers use a free lane. Zero cargo adds no
  decorative containers. Grouped cargo remains inside the existing bank at all
  supported hull widths.
- Reports retain `cargo` as a commit count, add each language's `large_containers`
  and `small_containers`, and expose `commits_per_large_container: 4` at the top
  level. The weighted total `4*large_containers + small_containers` equals the
  displayed commit count.
- Funnel-to-deck continuity and six-character label clearance are checked across all
  supported widths. JavaScript and TypeScript follow the same pipeline as the other
  demo languages. Cargo occludes smoke drifting behind it.
- Each regeneration samples the available sea using a fresh seed chosen once.
  Full motion envelopes remain disjoint and inside the canvas. Bounded retries
  fall back to randomized column widths and independent vertical splits when a
  dense fleet needs a guaranteed fit. Positions remain fixed through the loop.
  An explicit `--seed` makes the complete scene repeatable; the report records
  `layout_seed`, coordinates, ship designs, ray/watermark settings and watermark
  text.

## Ship-type assignment contracts

The production pool contains `steam`, `tug`, `freighter`, `sail`, `ferry`,
`trawler` and `tanker`. The three new pixel-art designs were approved before
integration. Each render shuffles the seven designs and selects up to six
without replacement, so every visible ship type is unique. The shuffle uses a separate random
stream derived from the layout seed, so an explicit seed replays both positions
and types. Language labels, colors, custom label/color settings and commit cargo
are preserved independently of shape. Each report language entry includes
`design`. The sprite atlas uses the fixed `demo` seed for reproducible type
assignments.

The trawler's hook sways periodically by one logical pixel on narrow hulls or
two on wider hulls, with the rope anchored to a fixed boom tip. The rope remains
connected and the hook returns exactly at the loop boundary. It participates in
the same lighthouse tint as the hull. The ferry, trawler and tanker add no smoke
emitters; their smaller posts are masts or vents.

Approved empty and originally twenty-small-container reference PNGs for each new
design remain unchanged under `artwork/ship-designs/`. Empty references are still
pixel-exact; loaded-reference comparisons mask the reserved cargo bank after the
grouping change, preserving approved hull and superstructure geometry. The fixed demo seed selects tanker,
trawler, freighter, sail, steam and tug; ferry remains available as the seventh
registered design without increasing the six-ship scene limit.

## Huge Cargo Ship contracts

The user approved the 300×110-pixel heavy hull before integration and selected
slower, calmer water. Approved native references remain under
`artwork/huge-ship/`. Comparisons preserve the hull, bridge, rigging and cargo
geometry outside the new exact-total/overflow counter areas. The wake rolls once
per loop, with a low bow curl and no airborne spray. Body drift/bob stays within
one logical pixel; multiple-seed tests keep the full ship and water inside the
400×160 canvas. The new demo appears directly below the standard demo in the
short README.

- `huge_cargo_ship` defaults to false, with matching CLI and action controls.
  Enabling it replaces the entire language fleet with one aggregate vessel.
- Complete metadata pagination counts every qualifying unique authored SHA
  across the selected public repositories, including docs-only changes and
  repositories with no language bytes. Mixed-language/shared commits count once.
  No standard 20-commit or six-language early stop is used. Explicit empty Git
  repository responses count as empty; other API failures remain errors.
- Large containers hold six commits, and small remainder boxes hold one.
  The deck fits 30 large boxes and up to five small boxes. The exact total is
  always shown; `+N` shows overflow commits without changing container weights.
  Tests cover the capacity boundary, 197 commits = 30 visible large + five
  small + 12 overflow, and counters within the native canvas.
- Schema-3 records distinguish sampled language data from complete metadata or
  complete classified history. Aggregate totals reject sampled/legacy profiles,
  missing history and changed window/observation/filters. Metadata-only caches
  cannot render a language fleet. Schema-1/2 caches remain supported in the
  standard mode. Explicit full classified fixtures work in both modes.
- Huge-mode reports use `languages: []`, exact `total_commits`, six-commit
  grouping, total/visible box counts and overflow; they do not invent an
  aggregate programming language. A zero-commit period keeps only the lighthouse
  and enabled decorations.
- Real CLI/action tests verify on/off and empty-input precedence, invalid flags,
  month selection and cache-mode diagnostics. Both renderers retain the exact
  shared palette, binary alpha, full-frame disposal and decoded-frame audits.

A read-only live aggregate audit for PingPongPlus's rolling 30-day window counted
**59 distinct authored commits across 19 selected public repositories** in **22
requests**, with complete metadata coverage and no warnings. It stored a
credential-free schema-3 profile locally; no huge-mode image was published by
this audit. These counts describe that observation instant, not a fixed account
total. Normal scheduled profile generation remains independently configurable.

## Renamed-account undercount investigation

The successful profile run before this fix reported `activity_window_days: 365`
and Java cargo **3**, establishing an actual data undercount rather than an
incorrect selected window. A read-only comparison against public Air-Client
history found that `author=PingPongPlus` returned five commits using the current
address, while the unfiltered history included many commits using the old
`pingminus` noreply address with the same linked `author.login: PingPongPlus`.
The fix removes only that server-side author query. The local linked-author,
timestamp, language and SHA checks still apply. A regression fixture reproduces
the dropped old-address records and also verifies that another account's commit
does not count.

A fresh authenticated public-profile fetch after the fix completed in **292
requests** with no warnings. In the same 365-day window it produced Java cargo
**20**, C++ **20**, Python **5**, TypeScript **6**, JavaScript **8**, and GLSL
**20**. The Java result confirms the change from three to the 20-commit display cap; twenty
represents at least twenty qualifying distinct commits, not an exact total above
the cap. This audit read live data; ordinary tests remain offline.

## Lighthouse ray contracts

The ray originates at the lantern and rotates once per loop, changing projected
length, tilt and fan width. It is applied after all scene artwork. Empty pixels
inside the cone become solid yellow; existing opaque pixels receive an RGB tint
of 30% yellow and 70% original color. Alpha remains binary, preserving the same
appearance in GIF without discarding the underlying artwork. Pixels outside the
cone are unchanged. Tests cover its exact loop, changing projection, solid fill,
color blending, disable setting and exact decoded GIF cleanup.
`lighthouse_beam = false`, `--no-lighthouse-beam`, or
the action input `lighthouse-beam: 'false'` disables the ray while retaining the
lantern blink. The default is enabled.

## Watermark contracts

The default-enabled top-left label uses the existing uppercase pixel font and
gray lettering. For the month preset it reads
`GIT SHIP — COMMITS FROM THE PAST MONTH`; day, week, year and custom day counts
follow the selected activity window. Layout reserves a 14-pixel header for the
label, and drawing it after the ray keeps the lettering untinted. The report
records `watermark` and `watermark_text`. `watermark = false`, `--no-watermark`,
or the action input `watermark: 'false'` hides the label. It has no effect on
commit attribution or cargo counts.

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
| Lighthouse ray | Enabled |
| Watermark | Enabled; `GIT SHIP — COMMITS FROM THE PAST MONTH` |
| Ship designs, in report order | tanker / trawler / freighter / sail / steam / tug |
| GIF | **975,589 bytes**, below 2 MB target |
| PNG | **7,007 bytes**, genuine RGBA |
| Fully transparent pixels over every frame | **74.4734375%–84.49375%** |
| Alpha / palette / disposal | Binary alpha, one shared palette, transparent index 0, disposal 2 |
| Decoded comparison | All 100 frames exactly match intended alpha and visible RGB |
| Represented commits, in report order | JAVA 7 / C++ 20 / PYTHON 6 / RUST 4 / JS 5 / TS 2 |
| Large/small container counts, in report order | 1/3, 5/0, 1/2, 1/0, 1/1, 0/2 |

The solid ray intentionally occupies otherwise empty pixels while sweeping,
reducing the demo's minimum transparency to about 74.47% with the watermark
enabled. Tests continue to require at least 80% transparency for the fleet with
the ray disabled. With the
ray enabled, exact binary alpha, palette colors and decoded cleanup remain
verified. The regenerated contact sheet was inspected for readable Java, Rust
and JavaScript artwork under the yellow tint, clear header lettering that fits
above the ships, the trawler's visible hook motion, and readable `4` marks on
the grouped cargo's large containers.

Delivered art: `examples/demo/git-ship.gif`, `git-ship.png`, `report.json`,
`contact-sheet.png`, `preview.html`, `examples/reduced-motion.html`, and
`artwork/sprite-atlas.png`. Editable sources are documented in `artwork/README.md`.

Huge demo: `examples/huge-demo/`, using seed `huge-demo`, the same month fixture,
and the new watermark wording. It exports **800×320**, **100 frames at 10 fps**,
**10 seconds**, **932,101 GIF bytes** and **6,104 PNG bytes**. Transparency ranges
from **63.321875% to 76.6515625%** across the loop. Its larger ship has its own
transparency checks; the standard fleet's 80% ray-off check remains unchanged.
The 44-commit total is represented by seven six-commit containers and two small
ones, with no overflow. Both modes' regenerated contact sheets were inspected.

The approved reference, still compositions and light/dark contact sheets were
inspected during implementation. The initial animation and smoke/wake revision were
also inspected in browser playback on both backgrounds. This revision's six
ships, free placement, sweeping ray, grouped cargo, readable labels and smoke clearance were inspected in the
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

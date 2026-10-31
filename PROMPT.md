# Build Git Ship

Build a complete, usable open-source project called **Git Ship**, with the CLI and repository name `git-ship`.

The main project root is `/Users/niklas/Desktop/Dev/git-ship`. Work directly in that directory and read any applicable `AGENTS.md` first. The approved visual reference is `references/concept-transparent.png` relative to the project root. Earlier concepts in `references/archive/` are historical context; the transparent reference and this brief define the current direction.

Implement the project, run it, inspect the resulting animation, fix defects, and deliver working code, artwork, documentation, and automation. Make routine implementation decisions yourself. This request authorizes local implementation. Publishing a repository, configuring account permissions, releasing an action, or pushing commits requires separate authorization.

## Product and intended use

Generate a personalized, animated pixel-art decoration for a GitHub profile README. A small lighthouse represents the user, and ships named after programming languages represent their language usage. The README page background itself becomes the ocean and sky through transparency.

**GitHub Actions is a first-class deliverable and the main end-user setup.** Users should be able to add a copy-paste workflow, supply their username or use the repository owner, add one README image reference, and have their personalized animation regenerate nightly. Also support manual workflow execution and a local CLI. The normal public-profile setup should use the workflow's built-in `GITHUB_TOKEN`, with its limitations documented. No hosted application or external image service is needed for the default setup.

Ship an animated GIF and a matching static transparent PNG. The final result must genuinely animate; a still concept, a whole-image pan, or a subtle color flicker alone is insufficient.

## Language and architecture

Use **Python and Pillow** with minimal additional runtime dependencies. Use a supported Python version, package the project through `pyproject.toml`, and provide an installable `git-ship` CLI. Prefer standard-library HTTP, configuration parsing, and CLI facilities where practical. Add useful type annotations and meaningful tests. Consult current official documentation when choosing dependency versions and GitHub Action versions.

Keep GitHub fetching, normalized profile data, deterministic scene layout, pixel sprites, animation state, and image export separate. Rendering must run offline from fixtures. Keep a single source of truth for configuration and data mappings. Avoid a web application, database, frontend framework, account system, or unnecessary abstraction layers.

## Approved visual direction

Match `references/concept-transparent.png`: a sparse, clean composition of small pixel sprites floating in transparent space. Typical frames should have **at least 80% fully transparent pixels** at default settings.

Visible elements:

- A small ivory/red lighthouse at the left, a dark roof, a tiny warm-yellow lantern, and a few minimal rocks beneath it.
- A small fleet of language-named ships, generously spaced and slightly staggered vertically.
- A handful of short, broken wave/wake strokes immediately under and behind the ships, plus a couple near the lighthouse base.
- Small chimney smoke puffs where appropriate.

Keep the remaining canvas transparent. Do not draw a filled ocean, sky, horizon, coastline, village, house, dock, trees, stars, moon, clouds, broad beam, gradient, opaque backdrop, or checkerboard pattern.

Use a consistent logical pixel grid, clear silhouettes, a restrained shared palette, minimal shading, and roughly 3-5 main colors per sprite. Start around **400 x 160 logical pixels** and export at **2x integer scale** with nearest-neighbor sampling. Adjust dimensions only when necessary for legibility. No anti-aliasing, soft edges, detailed textures, photographic lighting, or smooth vector shapes.

Construct original, independently movable scene elements and include their editable source. The concept image is a reference for composition and style; render the ships, lighthouse, and wakes as separate elements.

## Ships and readable names

Provide these four ships in offline demo mode:

| Hull name | Design |
|---|---|
| `JAVA` | Compact muted gold/burgundy steamship, one funnel, tiny smoke puffs. |
| `C++` | Blue freighter with a few simple container blocks. |
| `PYTHON` | Teal sailboat with a simple cream sail. |
| `RUST` | Small rust-red tugboat. |

Paint names on hulls with clean bitmap lettering. Keep hull lettering attached to the moving sprite, stable, and readable at normal README display widths. Support the characters in real language names, including `+`, `#`, spaces, and hyphens. Provide configurable labels or sensible abbreviations for long names.

Use actual languages in live mode. Support other languages through deterministic ship variants and configurable colors. Display the available languages up to the configured ship count; do not invent data to fill the fleet. Default to four ships, with at most five visible. Bound ship sizes and prevent overlap between hulls, names, wakes, and the lighthouse. The scenery must remain attractive for an empty or low-activity profile. Make names, outlines, rocks, and wakes readable on both light and dark page backgrounds.

## GitHub data and its meaning

Use official GitHub APIs to fetch public data. Read the token from `GITHUB_TOKEN`; never print it or place it in generated files. Handle pagination, rate limits, invalid usernames, empty data, and API failures with clear errors. Store fixtures and optional cached normalized data without credentials.

- Select languages from public, owned, non-fork repositories by default, with configurable inclusion/exclusion.
- Rank languages using reported language byte counts. Describe this as code share across the selected repositories, rather than coding time or developer skill.
- Let language share affect ship size within conservative bounds so every label stays readable.
- Let recent activity in repositories using a language influence that ship's movement, wake, or smoke. Clearly document this repository-level proxy; do not claim precise per-language commit attribution.
- Let contribution totals gently influence overall animation activity, with clamped extremes.
- Seed cosmetic variation from the username to preserve a stable identity across updates.
- Keep quiet profiles peaceful and visually complete.

Document the exact windows and formulas used. Make optional release-based details a later enhancement after the core pipeline works. Only show release events when backed by fetched release data.

## Animation and transparency

Default to a seamless **10-second, 10-fps loop**. Make duration and frame rate configurable within sensible export limits.

- Ships gently bob and visibly drift or sail. Keep the motion calm and headings consistent with movement.
- Each moving ship creates a few short pixel wake strokes. The strokes appear, move or change shape, and disappear back to full transparency.
- Smoke puffs rise or drift in a repeating cycle. Keep smoke sparse.
- Add a tiny lantern flicker or similarly restrained lighthouse animation.
- Keep most of the frame empty throughout playback.

Use deterministic frame time and periodic motion. Plan loop continuity explicitly, including wakes and smoke. Handle offscreen transitions without visible teleports or a pause at the seam. Avoid duplicating the first frame as an extra final hold.

PNG must have genuine alpha. GIF must preserve a transparent palette index and correct disposal behavior. Account for GIF's binary transparency: use clean opaque or transparent pixels, and avoid matte-colored halos. Moving objects and wakes must not leave accumulated trails, opaque rectangles, or ghost sprites.

A shared GIF palette should keep colors stable. Preserve transparency during palette conversion and optimization. Aim for a GIF below **2 MB** with default settings; report actual size and any tradeoffs rather than compromising readability to meet the target.

## Local commands and configuration

Provide commands equivalent to:

```sh
git-ship render --demo --output-dir out
git-ship render --username YOUR_USERNAME --output-dir out
git-ship render --config examples/config.toml --output-dir out
```

Use stable output names such as `git-ship.gif` and `git-ship.png`. Demo mode must work fully offline without credentials and produce deterministic outputs. Support a fixed observation date in tests and demos so time-based changes remain reproducible.

Configuration should cover username, repository filters, ship count, language labels/colors, seed, output scale, frame rate, duration, and activity window. Validate values and bound workload before allocating all animation frames.

## Reusable GitHub Action and example workflow

Provide a root `action.yml` that other repositories can call with `uses: OWNER/git-ship@v1` once published. A composite action is a reasonable starting point. Implement an actual working action, not only an illustrative workflow.

Define and document inputs such as username, output directory, and optional configuration path, and expose the generated image paths as action outputs. Explain dependency installation, token handling, and the permissions needed by each step. Separate image generation from publishing so callers can choose their publication strategy.

Include a complete example profile-repository workflow that:

1. Runs on a nightly schedule and `workflow_dispatch`.
2. Checks out the profile repository and invokes Git Ship with the repository owner's username by default.
3. Uses the built-in `GITHUB_TOKEN` for public-profile data where supported.
4. Publishes only the generated assets to an explicitly designated `output` branch using the permissions required for that publication step.
5. Commits only when the generated assets change.
6. Uses appropriate concurrency control and clear failure messages.

Protect the caller's default branch and unrelated files. Avoid committing artwork to the default branch in the recommended workflow, where the automation could influence its own contribution input. Explain cron timezone and scheduling delays in the documentation. Do not claim a published `@v1` action exists before it is released; use clear placeholders and validate local action execution in this project's CI.

Provide a copy-paste Markdown embed using the user's own output-branch asset URL, descriptive alt text, and a static PNG alternative for reduced-motion use. Document the supported reduced-motion snippet and test it on GitHub where possible. Explain setup permissions and token limitations without asking users to create an unnecessary personal access token.

## Visual verification and tests

First prove a strong still composition matching the approved reference. Then build and inspect the real animation. Generate contact sheets and a small local preview document that displays the same transparent GIF over both light and dark backgrounds at representative README widths. Preview backgrounds are only for verification; keep exported artwork transparent.

Inspect full playback, not only isolated frames. Check readable names, sprite spacing, actual movement, wake cleanup, smoke, palette stability, transparency, light/dark visibility, and loop continuity. Compare decoded GIF frames to intended frames to detect disposal or palette regressions.

Test meaningful contracts: fixture parsing, pagination handling, language ranking and filtering, bounded sizing, deterministic rendering, missing/empty data, label handling, offline CLI execution, image dimensions, actual multiple-frame animation, frame timing, transparent areas, and no residual pixels after an object moves. Use fixtures for CI and avoid a live API requirement in ordinary tests.

CI must run on pull requests and pushes and perform appropriate checks, an offline render, and a local reusable-action smoke test. Keep deployment/publication separate from PR verification.

## Deliverables and completion

Deliver the Python package and CLI, original editable sprites, demo transparent GIF/PNG, preview/contact-sheet artifacts, tests, CI, root reusable action, complete user workflow, example configuration, and a README covering installation, setup, data meanings, customization, limitations, and troubleshooting.

Keep the approved reference and this prompt available. Preserve earlier references in their archive. When finished, report the commands run and their results, output paths, animation dimensions/frame count/frame rate/duration, file size, transparency measurements, and any remaining limitations. Do not describe incomplete work as finished.

# Git Ship

Turn your public programming and scripting commits into an animated fleet for your profile README. No server or personal access token needed.

<picture>
  <source media="(prefers-reduced-motion: reduce)" srcset="examples/demo/git-ship.png">
  <img src="examples/demo/git-ship.gif" width="800" alt="Pixel ships carrying commit cargo beside a lighthouse.">
</picture>

## Huge Cargo Ship (optional)

<picture>
  <source media="(prefers-reduced-motion: reduce)" srcset="examples/huge-demo/git-ship.png?v=rain-20261101">
  <img src="examples/huge-demo/git-ship.gif?v=rain-20261101" width="800" alt="One heavy cargo ship with falling rain, tiny ocean impact ripples and language cargo.">
</picture>

One heavy ship carries your programming commits. **Large container = 6 commits; small = 1.** The hull counter shows **all authored commits** in the selected period. Overflow shows code cargo beyond deck capacity.

Enable it with `huge-cargo-ship: 'true'` under the workflow's **Generate fleet → with:** section.
Add `cargo-logos: 'true'` for language-marked containers: six Java commits make one Java container. Leftovers share mixed containers; each commit counts once. Rain is enabled in this demo with `rain: 'true'`.

## Set up in 4 steps

1. Open or create your **public profile repository**: `YOUR_USERNAME/YOUR_USERNAME`.
2. Copy [this workflow](examples/profile-workflow.yml) into `.github/workflows/git-ship.yml` in that repository. Commit it to the default branch.
3. Open **Actions → Git Ship → Run workflow**. Wait for the run to finish successfully. It creates the `output` branch with your images.
4. Add this to your profile `README.md`, replacing **every** `YOUR_USERNAME`:

```html
<picture>
  <source media="(prefers-reduced-motion: no-preference)"
    srcset="https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_USERNAME/output/git-ship.gif">
  <img width="800"
    src="https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_USERNAME/output/git-ship.png"
    alt="My commits as pixel ships">
</picture>
```

That's it. Your fleet updates **daily** using the **past month** of data by default.

## Options

| Change | How |
| --- | --- |
| Data period | Choose `day`, `week`, `month`, or `year` when running manually. These mean 1, 7, 30, or 365 days. |
| Automatic data period | Set the repository variable `GIT_SHIP_DATA_WINDOW` to one of those values. [Instructions](docs/advanced.md#choose-your-data-window). |
| Hourly updates | Change the workflow cron to `'23 * * * *'`. |
| Hide the light beam | Add `lighthouse-beam: 'false'` under the **Generate fleet** step's `with:` section. |
| Rain and ocean ripples | Add `rain: 'true'` in the same place. [Preview](examples/rain-demo/git-ship.gif). |
| Hide the watermark | Add `watermark: 'false'` in the same place. |
| Show commit total | Add `display-commits: 'true'` to show the fleet's full total at the bottom right. |
| Include docs/config commits | Add `include-non-code: 'true'`. By default, only programming and scripting commits count. |

## Reading the standard fleet

Only languages you committed to appear, with up to **6 ships** in fresh random locations and ship types on each run.

- **Small container:** 1 commit.
- **Large container marked 4:** 4 commits.
- Each ship shows up to **20 commits** from your public, owned repositories' default branches.

Missing image? Check the workflow run under **Actions**. Publishing needs `contents: write` and permission to update the `output` branch. GitHub's image cache can take a little time to refresh.

## Project goals

- [ ] Add more distinct ship designs and animations.
- [ ] Expand pixel-art logos for more programming and scripting languages.
- [ ] Add more large ship variants with different silhouettes and cargo layouts.

[Contribute](CONTRIBUTING.md) · [Advanced guide & local CLI](docs/advanced.md) · [Custom configuration](examples/config.toml) · [MIT license](LICENSE)

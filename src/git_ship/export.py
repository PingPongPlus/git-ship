"""Exact shared-palette export, followed by a full decoded-frame audit."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from array import array
from pathlib import Path
from typing import Any

from PIL import GifImagePlugin, Image, ImageChops

from .animation import Animator
from .config import Config
from .huge_ship import (
    COMMITS_PER_LARGE,
    HUGE_HEIGHT,
    HUGE_WIDTH,
    huge_cargo_counts,
    language_cargo_plan,
)
from .layout import Scene
from .sprites import CARGO_GROUP_SIZE, cargo_groups
from .watermark import commit_label, watermark_label


def indexed_frames(frames: list[Image.Image]) -> list[Image.Image]:
    colors: set[tuple[int, int, int, int]] = set()
    for frame in frames:
        found = frame.getcolors(256)
        if found is None:
            raise ValueError("artwork exceeds the 255 opaque color shared-palette limit")
        colors.update(color for _, color in found if color[3])
    if len(colors) > 255 or any(c[3] != 255 for c in colors):
        raise ValueError("GIF artwork requires at most 255 colors with binary alpha")
    ordered = [(0, 0, 0, 0), *sorted(colors)]
    mapping = {int.from_bytes(bytes(c), sys.byteorder): i for i, c in enumerate(ordered)}
    palette = [channel for color in ordered for channel in color[:3]]
    palette += [0] * (768 - len(palette))
    result = []
    for frame in frames:
        pixels = array("I", frame.tobytes())
        indexed = Image.frombytes("P", frame.size, bytes(mapping[p] for p in pixels))
        indexed.putpalette(palette)
        indexed.info["transparency"] = 0
        result.append(indexed)
    return result


def verify_gif(path: Path, intended: list[Image.Image], config: Config) -> dict[str, Any]:
    transparent = []
    durations = []
    with Image.open(path) as gif:
        if gif.n_frames != len(intended) or gif.info.get("loop") != 0:
            raise ValueError("GIF frame count or infinite-loop metadata changed during encoding")
        for i, source in enumerate(intended):
            gif.seek(i)
            decoded = gif.convert("RGBA")
            # RGB under transparent pixels is immaterial; alpha and visible RGB
            # must match exactly, including pixels vacated by moving objects.
            if ImageChops.difference(source.getchannel("A"), decoded.getchannel("A")).getbbox():
                raise ValueError(f"GIF transparency/disposal regression in frame {i}")
            difference = ImageChops.difference(source.convert("RGB"), decoded.convert("RGB"))
            if ImageChops.multiply(difference, source.getchannel("A").convert("RGB")).getbbox():
                raise ValueError(f"GIF palette regression in frame {i}")
            if gif.disposal_method != 2:
                raise ValueError("GIF must restore the transparent background after every frame")
            transparent.append(
                decoded.getchannel("A").histogram()[0] / (decoded.width * decoded.height)
            )
            durations.append(gif.info["duration"])
    if set(durations) != {1000 // config.fps}:
        raise ValueError("GIF frame timing changed during encoding")
    return {
        "width": intended[0].width,
        "height": intended[0].height,
        "frames": len(intended),
        "fps": config.fps,
        "duration_seconds": sum(durations) / 1000,
        "gif_bytes": path.stat().st_size,
        "min_transparent_fraction": min(transparent),
        "max_transparent_fraction": max(transparent),
        "decoded_frames_match": True,
    }


def export(
    scene: Scene, config: Config, output_dir: Path
) -> tuple[dict[str, Any], list[Image.Image]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    animator = Animator(scene, config)
    frames = animator.frames()
    indexed = indexed_frames(frames)
    # Keep previously good assets intact if encoding/auditing fails.
    with tempfile.TemporaryDirectory(prefix=".git-ship-", dir=output_dir) as scratch:
        root = Path(scratch)
        gif_path = root / "git-ship.gif"
        # Pillow's high-level save merges identical adjacent frames. A quiet
        # lighthouse-only scene still needs the requested frame timing/count.
        # Its public GIF block helpers keep every full frame, one global palette,
        # no local palettes, no delta rectangles and no accidental final hold.
        header, _ = GifImagePlugin.getheader(
            indexed[0], info={"loop": 0, "transparency": 0, "background": 0, "optimize": False}
        )
        with gif_path.open("wb") as stream:
            for block in header:
                stream.write(block)
            for frame in indexed:
                for block in GifImagePlugin.getdata(
                    frame, duration=1000 // config.fps, disposal=2, transparency=0
                ):
                    stream.write(block)
            stream.write(b";")
        report = verify_gif(gif_path, frames, config)
        report["activity_window_days"] = config.activity_window
        report["mode"] = "huge-cargo-ship" if config.huge_cargo_ship else "fleet"
        report["huge_cargo_ship"] = config.huge_cargo_ship
        report["cargo_logos"] = config.cargo_logos and config.huge_cargo_ship
        report["commits_per_large_container"] = (
            COMMITS_PER_LARGE if config.huge_cargo_ship else CARGO_GROUP_SIZE
        )
        report["layout_seed"] = scene.layout_seed
        report["lighthouse_beam"] = config.lighthouse_beam
        report["watermark"] = config.watermark
        report["watermark_text"] = (
            watermark_label(config.activity_window) if config.watermark else None
        )
        report["display_commits"] = scene.fleet_commits is not None
        report["commit_counter_text"] = (
            commit_label(scene.fleet_commits) if scene.fleet_commits is not None else None
        )
        if scene.fleet_commits is not None:
            report["total_commits"] = scene.fleet_commits
        frames[0].save(root / "git-ship.png")
        report["png_bytes"] = (root / "git-ship.png").stat().st_size
        report["languages"] = [
            {
                "name": s.language.name,
                "label": s.style.label,
                "design": s.style.design,
                "code_share": round(s.language.share, 6),
                "activity": round(s.language.activity, 6),
                "width": s.width,
                "x": s.x,
                "y": s.y,
                "cargo": s.language.cargo,
                "large_containers": cargo_groups(s.language.cargo or 0)[0],
                "small_containers": cargo_groups(s.language.cargo or 0)[1],
            }
            for s in scene.ships
        ]
        if config.huge_cargo_ship:
            counts = huge_cargo_counts(scene.total_commits)
            report["total_commits"] = counts["total"]
            report["large_containers"] = counts["large"]
            report["small_containers"] = counts["small"]
            report["displayed_large_containers"] = counts["visible_large"]
            report["displayed_small_containers"] = counts["visible_small"]
            report["overflow_commits"] = counts["overflow_commits"]
            if scene.cargo_languages is not None:
                report["cargo_languages"] = dict(scene.cargo_languages)
                report["cargo_containers"] = language_cargo_plan(
                    scene.total_commits, scene.cargo_languages
                )
            report["huge_ship"] = (
                {
                    "x": scene.huge_ship.x,
                    "y": scene.huge_ship.y,
                    "width": HUGE_WIDTH,
                    "height": HUGE_HEIGHT,
                }
                if scene.huge_ship
                else None
            )
        (root / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        for name in ("git-ship.gif", "git-ship.png", "report.json"):
            os.replace(root / name, output_dir / name)
    return report, frames

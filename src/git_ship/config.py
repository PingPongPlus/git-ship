"""One validated configuration contract for the CLI, renderer and action."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field, fields
from datetime import date
from pathlib import Path
from typing import Any

USERNAME = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?\Z")
LABEL = re.compile(r"[A-Z0-9+# .-]{1,6}\Z")
HEX = re.compile(r"#[0-9a-fA-F]{6}\Z")
WIDTH, HEIGHT = 400, 160
DATA_WINDOWS = {"day": 1, "week": 7, "month": 30, "year": 365}
MAX_SHIPS = 6


@dataclass(frozen=True)
class Config:
    username: str = ""
    ships: int = MAX_SHIPS
    scale: int = 2
    fps: int = 10
    duration: int = 10
    activity_window: int = 30
    seed: str | int | None = None
    lighthouse_beam: bool = True
    watermark: bool = True
    huge_cargo_ship: bool = False
    cargo_logos: bool = False
    display_commits: bool = False
    rain: bool = False
    include_forks: bool = False
    include_archived: bool = True
    include: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()
    labels: dict[str, str] = field(default_factory=dict)
    colors: dict[str, str] = field(default_factory=dict)
    observation_date: date | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.username, str) or (
            self.username and not USERNAME.fullmatch(self.username)
        ):
            raise ValueError("username must be a GitHub login (1–39 letters, digits or hyphens)")
        for name, low, high in (
            ("ships", 0, MAX_SHIPS),
            ("scale", 1, 4),
            ("duration", 2, 20),
            ("activity_window", 1, 365),
        ):
            value = getattr(self, name)
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f"{name} must be an integer in {low}..{high}")
        if type(self.fps) is not int or self.fps not in (5, 10, 20, 25):
            raise ValueError("fps must be 5, 10, 20 or 25 (exact GIF centiseconds)")
        if self.duration * self.fps > 300:
            raise ValueError("export is limited to 300 frames; reduce duration or fps")
        # RGBA input, paletted output and decoding have separate allocations.
        if WIDTH * HEIGHT * self.scale**2 * self.duration * self.fps > 80_000_000:
            raise ValueError(
                "export exceeds 80 million frame-pixels; reduce scale, duration or fps"
            )
        for name in (
            "include_forks",
            "include_archived",
            "lighthouse_beam",
            "watermark",
            "huge_cargo_ship",
            "cargo_logos",
            "display_commits",
            "rain",
        ):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"{name} must be true or false")
        for name in ("include", "exclude"):
            value = getattr(self, name)
            if not isinstance(value, (list, tuple)) or not all(isinstance(p, str) for p in value):
                raise ValueError(f"{name} must be an array of repository glob strings")
        if self.seed is not None and type(self.seed) not in (str, int):
            raise ValueError("seed must be a string or integer")
        if self.observation_date is not None and type(self.observation_date) is not date:
            raise ValueError("observation_date must be an ISO date, such as 2026-10-01")
        for name in ("labels", "colors"):
            values = getattr(self, name)
            if not isinstance(values, dict) or not all(
                isinstance(k, str) and isinstance(v, str) for k, v in values.items()
            ):
                raise ValueError(f"{name} must be a table of language = string entries")
        for label in self.labels.values():
            if not LABEL.fullmatch(label):
                raise ValueError("labels must be 1–6 uppercase letters/digits or + # space . -")
        if any(not HEX.fullmatch(color) for color in self.colors.values()):
            raise ValueError("colors must use #RRGGBB notation")


def load_config(path: Path | None, overrides: dict[str, Any] | None = None) -> Config:
    raw = tomllib.loads(path.read_text(encoding="utf-8")) if path else {}
    allowed = {f.name for f in fields(Config)}
    unknown = raw.keys() - allowed
    if unknown:
        raise ValueError(f"unknown configuration keys: {', '.join(sorted(unknown))}")
    raw.update({k: v for k, v in (overrides or {}).items() if v is not None})
    if isinstance(raw.get("observation_date"), str):
        raw["observation_date"] = date.fromisoformat(raw["observation_date"])
    for name in ("include", "exclude"):
        if name in raw and isinstance(raw[name], list):
            raw[name] = tuple(raw[name])
    return Config(**raw)

"""Filename attribution using vendored GitHub Linguist metadata, not file contents.

This small heuristic does not reproduce Linguist's content detection or repository
.gitattributes. Ambiguous extensions are resolved using repository language bytes.
"""

from __future__ import annotations

import json
from importlib.resources import files
from pathlib import PurePosixPath

DATA = json.loads(files("git_ship").joinpath("assets/file-languages.json").read_text())


def _index(key: str) -> dict[str, tuple[str, ...]]:
    index: dict[str, list[str]] = {}
    for language, spec in DATA["languages"].items():
        for value in spec.get(key, ()):
            index.setdefault(value, []).append(language)
    return {value: tuple(names) for value, names in index.items()}


FILENAMES = _index("filenames")
EXTENSIONS = _index("extensions")
EXTENSIONS.update({ext: tuple(names) for ext, names in DATA.get("overrides", {}).items()})


def file_language(filename: str, available: dict[str, int]) -> str | None:
    path = PurePosixPath(filename)
    candidates = FILENAMES.get(path.name, ())
    if not candidates:
        suffixes = path.suffixes
        for i in range(len(suffixes)):
            candidates = EXTENSIONS.get("".join(suffixes[i:]), ())
            if candidates:
                break
    matches = set()
    for name in candidates:
        group = DATA["languages"][name].get("group", name)
        reported = group if group in available else name
        if available.get(reported, 0) > 0:
            matches.add(reported)
    return min(matches, key=lambda n: (-available[n], n)) if matches else None

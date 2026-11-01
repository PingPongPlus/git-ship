"""Approved original language symbols on the huge ship's 27×10 container grid."""

from PIL import Image, ImageDraw

from .config import Config
from .font import paint_text
from .sprites import language_style

HULL_EDGE = "#10212e"
INK = "#142736"
WHITE = "#f3e8c9"
MINI = {
    "A": [2, 5, 7, 5, 5],
    "J": [1, 1, 1, 5, 2],
    "V": [5, 5, 5, 5, 2],
    "P": [6, 5, 6, 4, 4],
    "Y": [5, 5, 2, 2, 2],
    "R": [6, 5, 6, 5, 5],
    "S": [3, 4, 2, 1, 6],
    "C": [3, 4, 4, 4, 3],
    "+": [0, 2, 7, 2, 0],
    "G": [3, 4, 5, 5, 3],
    "I": [7, 2, 2, 2, 7],
    "T": [7, 2, 2, 2, 2],
    "O": [2, 5, 5, 5, 2],
    "L": [4, 4, 4, 4, 7],
    "U": [5, 5, 5, 5, 7],
}
STYLES = {
    "Java": ("#a34e44", "JAVA"),
    "Python": ("#337ea1", "PY"),
    "JavaScript": ("#dfbe62", "JS"),
    "Rust": ("#ad7658", "RS"),
    "C++": ("#39799c", "C++"),
    "Git": ("#788e98", "GIT"),
    "C": ("#5c6bc0", "C"),
    "Go": ("#00add8", "GO"),
    "TypeScript": ("#3178c6", "TS"),
    "Lua": ("#000080", "LUA"),
}


def tiny(draw, x, y, text, color):
    for char in text:
        for row, bits in enumerate(MINI[char]):
            for col in range(3):
                if bits & (1 << (2 - col)):
                    draw.point((x + col, y + row), fill=color)
        x += 4


def container(language):
    tile = Image.new("RGBA", (27, 10), HULL_EDGE)
    d = ImageDraw.Draw(tile)
    if language not in STYLES:
        d.rectangle((1, 1, 25, 8), fill="#788e98")
        labels = {"Mixed": "MIX", "Markdown": "MD", "Text": "TXT"}
        label = labels.get(language, language_style(language, Config()).label[:4])
        paint_text(d, ((27 - (len(label) * 6 - 1)) // 2, 2), label, WHITE)
        return tile
    color, label = STYLES[language]
    d.rectangle((1, 1, 25, 8), fill=color)
    for x in (2, 24):
        d.line((x, 2, x, 7), fill=INK)
    # Original tiny symbols, drawn by hand on a seven-pixel-high grid.
    if language == "Java":
        d.point((6, 1), fill="#ffe2a1")
        d.point((5, 2), fill="#ffe2a1")
        d.rectangle((4, 4, 8, 6), fill=WHITE)
        d.line((9, 4, 10, 4, 10, 5, 9, 5), fill=WHITE)
        d.line((4, 8, 8, 8), fill=WHITE)
    elif language == "Python":
        d.rectangle((4, 2, 8, 4), fill="#f5d768")
        d.rectangle((3, 3, 5, 5), fill="#f5d768")
        d.rectangle((6, 5, 10, 7), fill=WHITE)
        d.rectangle((9, 4, 11, 6), fill=WHITE)
        d.point((7, 2), fill=INK)
        d.point((7, 7), fill=INK)
    elif language == "JavaScript":
        d.rectangle((4, 2, 11, 7), fill=INK)
        d.rectangle((5, 2, 10, 6), fill="#f5d768")
    elif language == "Rust":
        for x, y in (
            (5, 1),
            (7, 1),
            (9, 1),
            (3, 3),
            (11, 3),
            (3, 5),
            (11, 5),
            (5, 7),
            (7, 7),
            (9, 7),
        ):
            d.point((x, y), fill=WHITE)
        d.ellipse((4, 2, 10, 6), fill=WHITE)
        d.rectangle((6, 3, 8, 5), fill=INK)
    elif language == "C++":
        d.polygon(((7, 1), (11, 3), (11, 6), (7, 8), (3, 6), (3, 3)), fill=WHITE)
        d.rectangle((6, 3, 8, 6), fill=color)
        d.point((8, 3), fill=WHITE)
    elif language == "C":
        d.polygon(((7, 1), (11, 3), (11, 6), (7, 8), (3, 6), (3, 3)), fill="#c3d2ff")
        tiny(d, 6, 2, "C", "#283593")
    elif language == "Go":
        # A tiny gopher face: ears, two eyes, nose and paired front teeth.
        pixels = (
            ".b.....b.",
            "bbbbbbbbb",
            ".bwwbwwb.",
            ".bwkbwkb.",
            ".bbbbbbb.",
            "..bnnnb..",
            "..bwtwb..",
            "...bbb...",
        )
        palette = {"b": "#9de2ed", "w": "#ffffff", "k": INK, "n": "#d8b997", "t": INK}
        for row, pixels_row in enumerate(pixels):
            for col, pixel in enumerate(pixels_row):
                if pixel != ".":
                    d.point((3 + col, 1 + row), fill=palette[pixel])
    elif language == "TypeScript":
        # An inset square badge with a fixed 3x5 TS mark, never a system font.
        d.rectangle((3, 1, 11, 8), fill="#235a97")
        tiny(d, 4, 2, "TS", "#ffffff")
    elif language == "Lua":
        # Moon, crater, satellite and a broken orbital arc on Lua navy.
        d.ellipse((4, 3, 9, 8), fill="#ffffff")
        d.rectangle((7, 4, 8, 5), fill=color)
        d.rectangle((10, 1, 11, 2), fill="#ffffff")
        for point in ((4, 1), (2, 4), (3, 8), (10, 7), (11, 4)):
            d.point(point, fill="#8c9ddd")
    else:
        d.polygon(((7, 1), (11, 5), (7, 8), (3, 5)), fill="#e59a6b")
        d.line((5, 3, 8, 6), fill=INK)
        d.line((7, 5, 9, 3), fill=INK)
    tiny(
        d,
        11 if language == "Java" else 13,
        3,
        label,
        INK if language in {"JavaScript", "Go"} else WHITE,
    )
    return tile

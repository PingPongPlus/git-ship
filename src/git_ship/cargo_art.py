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
}
STYLES = {
    "C": ("#537587", "C"),
    "Go": ("#3e8292", "GO"),
    "TypeScript": ("#346888", "TS"),
    "Lua": ("#000080", "LUA"),
    "Java": ("#a34e44", "JAVA"),
    "Python": ("#337ea1", "PY"),
    "JavaScript": ("#dfbe62", "JS"),
    "Rust": ("#ad7658", "RS"),
    "C++": ("#39799c", "C++"),
    "Git": ("#788e98", "GIT"),
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
        d.ellipse((4, 2, 10, 6), outline=WHITE, width=1)
    elif language == "Go":
        d.text((4, 2), "G", fill=WHITE)
    elif language == "TypeScript":
        d.text((4, 2), "TS", fill=WHITE)
    elif language == "Lua":
        d.text((4, 2), "L", fill=WHITE)
    else:
        d.polygon(((7, 1), (11, 5), (7, 8), (3, 5)), fill="#e59a6b")
        d.line((5, 3, 8, 6), fill=INK)
        d.line((7, 5, 9, 3), fill=INK)
    tiny(d, 11 if language == "Java" else 13, 3, label, INK if language == "JavaScript" else WHITE)
    return tile

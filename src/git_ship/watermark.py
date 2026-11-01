"""Small pixel caption showing the activity period selected for this fleet."""

from PIL import Image, ImageDraw

from .config import HEIGHT, WIDTH
from .font import paint_text, text_width

WATERMARK_HEIGHT = 14
COMMIT_FOOTER_HEIGHT = 12
WATERMARK_COLOR = "#8da0a6"
WATERMARK_SHADOW = "#172f42"


def watermark_label(days: int) -> str:
    period = {1: "day", 7: "week", 30: "month", 365: "year"}.get(days, f"{days} days")
    return f"Git Ship — commits from the past {period}"


def draw_watermark(image: Image.Image, days: int) -> None:
    draw = ImageDraw.Draw(image)
    label = watermark_label(days).upper()
    paint_text(draw, (6, 5), label, WATERMARK_SHADOW)
    paint_text(draw, (5, 4), label, WATERMARK_COLOR)


def commit_label(total: int) -> str:
    return f"{total} COMMIT" if total == 1 else f"{total} COMMITS"


def draw_commit_total(image: Image.Image, total: int) -> None:
    label = commit_label(total)
    x, y = WIDTH - 5 - text_width(label), HEIGHT - 11
    draw = ImageDraw.Draw(image)
    paint_text(draw, (x + 1, y + 1), label, WATERMARK_SHADOW)
    paint_text(draw, (x, y), label, WATERMARK_COLOR)

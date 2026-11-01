"""Small pixel caption showing the activity period selected for this fleet."""

from PIL import Image, ImageDraw

from .font import paint_text

WATERMARK_HEIGHT = 14
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

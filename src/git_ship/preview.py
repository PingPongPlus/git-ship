"""Local verification artifacts; background colors never enter exported art."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw


def write_preview(output: Path, frames: list[Image.Image], duration: int) -> None:
    width, height = frames[0].size
    sheet = Image.new("RGB", (width * 2, (height + 30) * 4), "#f6f3ec")
    d = ImageDraw.Draw(sheet)
    for row, fraction in enumerate((0, 0.25, 0.5, 0.75)):
        frame = frames[round(fraction * len(frames))]
        for col, background in enumerate(("#f6f3ec", "#0d1117")):
            x, y = col * width, row * (height + 30)
            d.rectangle((x, y, x + width, y + height + 29), fill=background)
            d.text(
                (x + 12, y + 10),
                f"{fraction * duration:g}s / {'LIGHT' if col == 0 else 'DARK'}",
                fill="#647888",
            )
            sheet.paste(frame, (x, y + 30), frame)
    sheet.save(output / "contact-sheet.png")
    (output / "preview.html").write_text(
        """<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Git Ship · animation proof</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#e9e7e0;color:#192e40;
font:15px/1.6 system-ui,sans-serif;padding:40px 24px}main{max-width:1050px;margin:auto}
h1{font-size:32px;margin:0}p{max-width:720px}header{margin-bottom:28px}
button,a{color:inherit}button{font:inherit;padding:7px 16px;border:1px solid #82939b;
background:transparent;border-radius:6px;cursor:pointer}.panel{margin:20px 0;padding:22px;
border:1px solid #bec8c8;border-radius:12px;overflow:auto}.light{background:#fff;color:#192e40}
.dark{background:#0d1117;color:#d8e9df;border-color:#30363d}h2{font-size:12px;letter-spacing:2px}
img{display:block;image-rendering:pixelated;max-width:100%;height:auto;margin:auto}
.small img{width:400px}.full img{width:800px}.stamp{font:12px ui-monospace,monospace}
</style><main><header><div class="stamp">GIT SHIP / LOCAL PROOF</div>
<h1>A little fleet. An open sea.</h1>
<p>These are the same transparent GIF on light and dark README backgrounds.
Watch the hulls bob, wakes clear, smoke rise, and lantern flicker through the loop.
The static image is frame zero. Exported artwork contains no background.</p>
<button id="motion">Pause animation</button> <a href="contact-sheet.png">Contact sheet</a>
</header>
<section class="panel light full"><h2>LIGHT · 800 PX</h2>
<img src="git-ship.gif" alt="Animated language fleet"></section>
<section class="panel dark full"><h2>DARK · 800 PX</h2>
<img src="git-ship.gif" alt="Animated language fleet"></section>
<section class="panel light small"><h2>LIGHT · 400 PX</h2>
<img src="git-ship.gif" alt="Animated language fleet at compact width"></section>
<section class="panel dark small"><h2>DARK · 400 PX</h2>
<img src="git-ship.gif" alt="Animated language fleet at compact width"></section>
<script>
let paused=matchMedia('(prefers-reduced-motion: reduce)').matches;
function update(){
document.querySelectorAll('img').forEach(i=>i.src=paused?'git-ship.png':'git-ship.gif');
document.querySelector('button').textContent=paused?'Play animation':'Pause animation'}
document.querySelector('button').onclick=()=>{paused=!paused;update()};update();
</script></main></html>""",
        encoding="utf-8",
    )

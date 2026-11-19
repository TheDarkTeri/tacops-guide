"""Turns the generated guide page into a standalone GitHub Pages site: index.html, a link-preview image and a favicon.
Run after gen_guide.py: py build_site.py <folder holding tacops-survival-guide.html and icons/> <site folder>"""
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SRC = Path(sys.argv[1])
SITE = Path(sys.argv[2])
URL = "https://thedarkteri.github.io/tacops-guide/"
TITLE = "TacOps Survival Guide"
DESCRIPTION = "Every recipe in the TacOps mod, where to find the materials, and how to keep your guns working in survival."
GUNS = ["tactical_rifle", "pistol", "shotgun", "m80_zolja"]

SITE.mkdir(parents=True, exist_ok=True)

# The page: the guide is written as a fragment for an Artifact (title, links and styles, then the body), so give it the
# document around it, with the small reset the Artifact host supplied
page = (SRC / "tacops-survival-guide.html").read_text(encoding="utf-8")
split = page.index('<header class="hero">')
head, body = page[:split], page[split:]
head = head.replace('<title>TacOps Survival Guide</title>\n', "").replace('<meta name="claude:viewport-fit-sides" content="cover">\n', "")
document = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{TITLE}</title>
<meta name="description" content="{DESCRIPTION}">
<meta name="theme-color" content="#4d5b28">
<link rel="icon" type="image/png" href="favicon.png">
<meta property="og:type" content="website">
<meta property="og:site_name" content="TacOps">
<meta property="og:title" content="{TITLE}">
<meta property="og:description" content="{DESCRIPTION}">
<meta property="og:url" content="{URL}">
<meta property="og:image" content="{URL}og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<style>
:root {{ color-scheme: light; }}
body {{ margin: 0; }}
[hidden] {{ display: none !important; }}
</style>
{head.strip()}
</head>
<body>
{body.strip()}
</body>
</html>
'''
(SITE / "index.html").write_text(document, encoding="utf-8", newline="\n")

# Favicon: the rifle's inventory icon
Image.open(SRC / "icons" / "tactical_rifle.png").save(SITE / "favicon.png", optimize=True)

# Link preview, 1200x630: the title over a hotbar of the four guns, in the page's dark palette
W, H = 1200, 630
bg, ink, muted, accent = (20, 24, 21), (226, 230, 222), (152, 161, 147), (168, 187, 114)
og = Image.new("RGBA", (W, H), bg + (255,))
draw = ImageDraw.Draw(og)


def font(size, weight):
    f = ImageFont.truetype("C:/Windows/Fonts/bahnschrift.ttf", size)
    f.set_variation_by_name(weight)
    return f


draw.text((80, 92), "TACOPS 1.1.0  ·  MINECRAFT 26.3  ·  FABRIC", font=font(26, "SemiBold"), fill=muted)
draw.text((76, 136), "Survival Guide", font=font(104, "Bold"), fill=ink)
draw.rectangle((80, 268, 200, 274), fill=accent)
draw.text((80, 300), "Every recipe, every material, and how to", font=font(36, "Regular"), fill=muted)
draw.text((80, 344), "keep your guns working.", font=font(36, "Regular"), fill=muted)

# A Minecraft hotbar: light grey panel with bevelled slots, each gun at twice its 64px render
slot, pad = 144, 12
bar_w, bar_h = slot * len(GUNS) + pad * 2, slot + pad * 2
x0, y0 = 80, H - bar_h - 56
draw.rectangle((x0, y0, x0 + bar_w - 1, y0 + bar_h - 1), fill=(198, 198, 198))
draw.rectangle((x0, y0, x0 + bar_w - 1, y0 + 5), fill=(255, 255, 255))
draw.rectangle((x0, y0, x0 + 5, y0 + bar_h - 1), fill=(255, 255, 255))
draw.rectangle((x0, y0 + bar_h - 6, x0 + bar_w - 1, y0 + bar_h - 1), fill=(85, 85, 85))
draw.rectangle((x0 + bar_w - 6, y0, x0 + bar_w - 1, y0 + bar_h - 1), fill=(85, 85, 85))
for i, gun in enumerate(GUNS):
    sx, sy = x0 + pad + i * slot, y0 + pad
    draw.rectangle((sx, sy, sx + slot - 1, sy + slot - 1), fill=(139, 139, 139))
    draw.rectangle((sx, sy, sx + slot - 1, sy + 3), fill=(55, 55, 55))
    draw.rectangle((sx, sy, sx + 3, sy + slot - 1), fill=(55, 55, 55))
    draw.rectangle((sx, sy + slot - 4, sx + slot - 1, sy + slot - 1), fill=(255, 255, 255))
    draw.rectangle((sx + slot - 4, sy, sx + slot - 1, sy + slot - 1), fill=(255, 255, 255))
    icon = Image.open(SRC / "icons" / f"{gun}.png").convert("RGBA").resize((128, 128), Image.NEAREST)
    og.alpha_composite(icon, (sx + 8, sy + 8))
og.convert("RGB").save(SITE / "og.png", optimize=True)

# GitHub Pages serves the files as they are
(SITE / ".nojekyll").write_text("", encoding="utf-8")

# What it takes to rebuild the page, kept with it
tools = SITE / "tools"
(tools / "icons" / "vanilla").mkdir(parents=True, exist_ok=True)
for name in ("gen_guide.py", "guide_template.html", "build_site.py"):
    shutil.copy(SRC / name, tools / name)
for icon in (SRC / "icons").glob("*.png"):
    shutil.copy(icon, tools / "icons" / icon.name)
for icon in (SRC / "icons" / "vanilla").glob("*.png"):
    shutil.copy(icon, tools / "icons" / "vanilla" / icon.name)

(SITE / "README.md").write_text(f'''# {TITLE}

A survival guide for [TacOps](https://modrinth.com/mod/tacops), the tactical shooter mod for Minecraft (Fabric): every
crafting recipe, where to find the materials, and how to keep your guns working.

**Read it at {URL}**

## Rebuilding

The recipes come straight from the mod's generated data, and the item icons are renders from the game. With Python and
Pillow, from this repository:

```
py tools/gen_guide.py <path to the TacOps mod project> tools
py tools/build_site.py tools .
```
''', encoding="utf-8", newline="\n")
print("built", SITE, sorted(p.name for p in SITE.iterdir()))

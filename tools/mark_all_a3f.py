"""Mark all A zone 3F nodes on the floor plan to identify false positives"""
import json
from pathlib import Path
from PIL import Image, ImageDraw

BASE = Path("E:/2025-2026-2/BIT-Nav-2026")

with open(BASE / "data/wencui_building_v6.json", encoding="utf-8") as f:
    data = json.load(f)
nodes = data["nodes"]

SCALE = 3
HALL_PX_HIRES = 164 * SCALE
HALL_PY_HIRES = 564 * SCALE

img = Image.open(BASE / "data/floorplans_hires/3F_hires.jpg").convert("RGB")
draw = ImageDraw.Draw(img)

# Draw 报告厅 reference
draw.ellipse([HALL_PX_HIRES-20, HALL_PY_HIRES-20, HALL_PX_HIRES+20, HALL_PY_HIRES+20],
             outline=(0, 100, 255), width=5)

# Mark all A zone 3F nodes
a_3f = [(k,v) for k,v in nodes.items() if v.get('zone')=='A' and v.get('floor')=='3F']
for nid, n in a_3f:
    ux, uy = n.get('ux', 0), n.get('uy', 0)
    hx, hy = ux * SCALE, uy * SCALE
    has_ocr = 'ocr_conf' in n
    # Red = OCR confirmed, Orange = not confirmed
    color = (220, 0, 0) if has_ocr else (200, 120, 0)
    R = 18
    draw.ellipse([hx-R, hy-R, hx+R, hy+R], outline=color, width=4)
    # Short label
    short = nid.replace('A-', '')
    draw.text((hx+R+2, hy-8), short, fill=color)

# Save full (downscaled for viewing)
w, h = img.size
out = img.resize((w//3, h//3), Image.Resampling.LANCZOS)
out.save(BASE / "data/marked_A3F_all.jpg", quality=85)
print(f"Saved: marked_A3F_all.jpg ({out.size})")

# Also save east-side crop (where valid A rooms should be)
# ux=500-744, uy=200-900 -> hires: x=1500-2232, y=600-2700
crop = img.crop((1450, 500, 2235, 2800))
crop_small = crop.resize((crop.width//2, crop.height//2), Image.Resampling.LANCZOS)
crop_small.save(BASE / "data/marked_A3F_east.jpg", quality=85)
print(f"East crop: marked_A3F_east.jpg ({crop_small.size})")

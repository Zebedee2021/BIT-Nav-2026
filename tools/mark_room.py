"""Mark a room on the hires floor plan and save the image"""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

BASE = Path("E:/2025-2026-2/BIT-Nav-2026")

with open(BASE / "data/wencui_building_v6.json", encoding="utf-8") as f:
    data = json.load(f)

NODE_ID = "A-301"
node = data["nodes"][NODE_ID]
floor = node["floor"]  # "3F"
ux, uy = node["ux"], node["uy"]
east_m, south_m = node["east_m"], node["south_m"]
ocr_raw = node.get("ocr_raw", "?")
ocr_conf = node.get("ocr_conf", 0)

# Scale to hires image (15px/m vs 5px/m = factor 3)
SCALE = 3
HALL_PX_HIRES = 164 * SCALE   # 492
HALL_PY_HIRES = 564 * SCALE   # 1692

hx = round(164 + east_m / 0.2) * SCALE   # ux * 3
hy = round(564 + south_m / 0.2) * SCALE  # uy * 3

print(f"{NODE_ID}: floor={floor}, ux={ux}, uy={uy}")
print(f"  east_m={east_m}, south_m={south_m}")
print(f"  Hires pixel: ({hx}, {hy})")
print(f"  OCR raw: {repr(ocr_raw)}, conf={ocr_conf:.3f}")

hires_path = BASE / f"data/floorplans_hires/{floor}_hires.jpg"
img = Image.open(hires_path).convert("RGB")
draw = ImageDraw.Draw(img)

# Draw crosshair
R = 40
draw.ellipse([hx-R, hy-R, hx+R, hy+R], outline=(255, 0, 0), width=5)
draw.line([hx-R*2, hy, hx+R*2, hy], fill=(255, 0, 0), width=3)
draw.line([hx, hy-R*2, hx, hy+R*2], fill=(255, 0, 0), width=3)

# Label
label = f"{NODE_ID}\n({east_m}m E, {south_m}m S)"
draw.rectangle([hx+R+5, hy-25, hx+R+280, hy+25], fill=(255,255,200), outline=(200,0,0))
draw.text((hx+R+10, hy-20), label, fill=(180, 0, 0))

# Also mark 报告厅 center for reference
draw.ellipse([HALL_PX_HIRES-15, HALL_PY_HIRES-15, HALL_PX_HIRES+15, HALL_PY_HIRES+15],
             outline=(0, 100, 255), width=4)
draw.text((HALL_PX_HIRES+20, HALL_PY_HIRES-10), "报告厅中心", fill=(0, 100, 255))

# Crop to region of interest (±400px around marked point)
pad = 400
x0 = max(0, hx - pad)
y0 = max(0, hy - pad)
x1 = min(img.width, hx + pad)
y1 = min(img.height, hy + pad)
crop = img.crop((x0, y0, x1, y1))

out_path = BASE / f"data/marked_{NODE_ID}_{floor}.jpg"
crop.save(out_path, quality=90)
print(f"\nSaved: {out_path}")

# Also save full floor image for context
out_full = BASE / f"data/marked_{NODE_ID}_{floor}_full.jpg"
# Resize for viewing
w, h = img.size
img_small = img.resize((w//3, h//3), Image.Resampling.LANCZOS)
img_small.save(out_full, quality=85)
print(f"Full view: {out_full}")

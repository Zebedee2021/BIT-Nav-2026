"""Debug A zone OCR - especially 4F which has 0% coverage"""
import numpy as np
from PIL import Image
import easyocr
import re

print('Init EasyOCR...')
reader = easyocr.Reader(['ch_sim', 'en'], gpu=False, verbose=False)

CROP = (76, 100, 2841, 1820)
CROP_W, CROP_H = 2765, 1720
OUT_W, OUT_H = 745, 1205

def unified_box_to_orig(ux_min, uy_min, ux_max, uy_max):
    def ux_to_cy(ux): return CROP_H - 1 - ux * CROP_H / OUT_W
    def uy_to_cx(uy): return uy * CROP_W / OUT_H
    oy_top   = int(ux_to_cy(ux_max) + CROP[1])
    oy_bot   = int(ux_to_cy(ux_min) + CROP[1])
    ox_left  = int(uy_to_cx(uy_min) + CROP[0])
    ox_right = int(uy_to_cx(uy_max) + CROP[0])
    return (max(0,ox_left), max(0,oy_top), min(3000,ox_right), min(2000,oy_bot))

# 4F A zone nodes: ux=314-606, uy=894-1204
# Check the search box
box_4f = unified_box_to_orig(280, 870, 650, 1210)
print(f'4F A zone search box (unified 280-650, 870-1210) -> orig {box_4f}')

for floor in ['4F', '5F', '3F']:
    print(f'\n=== {floor} A zone region ===')
    img = Image.open(f'data/floorplans/{floor}_official.jpg').convert('RGB')
    crop = img.crop(box_4f)
    img_np = np.array(crop)
    results = reader.readtext(img_np, detail=1, paragraph=False)

    print(f'  Total detections: {len(results)}')
    for b, text, conf in sorted(results, key=lambda x:-x[2]):
        if conf > 0.3:
            cx = sum(p[0] for p in b)/4
            cy = sum(p[1] for p in b)/4
            print(f'    conf={conf:.2f} text={repr(text)} at local({cx:.0f},{cy:.0f})')

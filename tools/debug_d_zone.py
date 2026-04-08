"""Debug D zone OCR - check what labels appear in the search region"""
import numpy as np
from PIL import Image
import easyocr

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

# D zone box (150, 450, 660, 1204)
d_box = unified_box_to_orig(150, 450, 660, 1204)
print(f'D zone search box (unified) -> orig {d_box}')

# D-304 expected position: ux=563, uy=955
# ux=563 -> oy = CROP_H-1-563*CROP_H/OUT_W + CROP[1] = 1720-1-1300+100 = 519
# uy=955 -> ox = 955*CROP_W/OUT_H + CROP[0] = 2192+76 = 2268
print('D-304 expected orig pos: ~(2268, 519)')
print('D-308 expected orig pos: ux=569,uy=520 -> ox=', int(520*2765/1205+76), 'oy=', int(1720-1-569*1720/745+100))

for floor in ['3F', '4F']:
    print(f'\n=== {floor} D zone ===')
    img = Image.open(f'data/floorplans/{floor}_official.jpg').convert('RGB')
    crop = img.crop(d_box)
    img_np = np.array(crop)
    results = reader.readtext(img_np, detail=1, paragraph=False)

    print(f'  Detections: {len(results)}')
    for b, text, conf in sorted(results, key=lambda x:-x[2]):
        if conf > 0.3:
            cx = sum(p[0] for p in b)/4
            cy = sum(p[1] for p in b)/4
            # Approximate unified coords
            gx = cx + d_box[0]
            gy = cy + d_box[1]
            print(f'    conf={conf:.2f} text={repr(text)} orig({gx:.0f},{gy:.0f})')

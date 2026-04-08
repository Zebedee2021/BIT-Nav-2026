"""Debug M and H zone OCR patterns"""
import json, re
import numpy as np
from PIL import Image
import easyocr

print('Init EasyOCR...')
reader = easyocr.Reader(['ch_sim', 'en'], gpu=False, verbose=False)

with open('data/wencui_building_v6.json', encoding='utf-8') as f:
    data = json.load(f)
nodes = data['nodes']

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

# M zone: check current positions
m_nodes = {k:v for k,v in nodes.items() if v.get('zone')=='M'}
m_uxs = [v.get('ux',0) for v in m_nodes.values()]
m_uys = [v.get('uy',0) for v in m_nodes.values()]
print(f'M zone: {len(m_nodes)} nodes, ux={min(m_uxs)}-{max(m_uxs)}, uy={min(m_uys)}-{max(m_uys)}')

m_box = unified_box_to_orig(min(m_uxs)-30, min(m_uys)-30, max(m_uxs)+30, max(m_uys)+30)
print(f'M zone orig box: {m_box}')

# H zone: check current positions
h_nodes = {k:v for k,v in nodes.items() if v.get('zone')=='H'}
h_uxs = [v.get('ux',0) for v in h_nodes.values()]
h_uys = [v.get('uy',0) for v in h_nodes.values()]
print(f'H zone: {len(h_nodes)} nodes, ux={min(h_uxs)}-{max(h_uxs)}, uy={min(h_uys)}-{max(h_uys)}')

for zone_name, z_nodes, box in [
    ('M', m_nodes, m_box),
    ('H', unified_box_to_orig(0, 370, 250, 820)),
]:
    print(f'\n=== {zone_name} zone, 1F ===')
    img = Image.open('data/floorplans/1F_official.jpg').convert('RGB')
    crop = img.crop(box)
    results = reader.readtext(np.array(crop), detail=1, paragraph=False)
    print(f'  Detections: {len(results)}')
    for b, text, conf in sorted(results, key=lambda x:-x[2]):
        if conf > 0.35 and re.search(r'\d{2,}', text):
            cx = sum(p[0] for p in b)/4 + box[0]
            cy = sum(p[1] for p in b)/4 + box[1]
            print(f'  conf={conf:.2f} text={repr(text)} orig({cx:.0f},{cy:.0f})')

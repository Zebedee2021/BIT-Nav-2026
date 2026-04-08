#!/usr/bin/env python3
"""标记 A 区所有房间在 3F 楼层图上"""
import json
from PIL import Image, ImageDraw, ImageFont
import os

with open('data/wencui_building_v6.json', encoding='utf-8') as f:
    data = json.load(f)

nodes = data['nodes']

# 加载 3F 楼层图
img = Image.open('data/floorplans_hires/3F_hires.jpg')
img_w, img_h = img.size
draw = ImageDraw.Draw(img)

# 圆楼在图片中的实际位置
# 从图中观察，圆楼中心大约在 (400, 1800)
circular_px, circular_py = 400, 1800

# 比例尺校准
# 从 v6 数据分析，ux/uy 到 east_m/south_m 的比例是 5
# 但楼层图可能是示意图，需要手动调整
# 当前使用 12，使 A-301 大致在正确位置
scale = 12

# 获取所有 3F A 区房间
a_rooms = [(nid, n) for nid, n in nodes.items() 
           if n.get('floor') == '3F' and n.get('zone') == 'A' and n.get('type') == 'room']

# 字体
try:
    font = ImageFont.truetype("C:/Windows/Fonts/simhei.ttf", 30)
    font_small = ImageFont.truetype("C:/Windows/Fonts/simhei.ttf", 20)
except:
    font = ImageFont.load_default()
    font_small = ImageFont.load_default()

# 绘制 A 区房间
for nid, n in a_rooms:
    east_m = n.get('east_m', 0)
    south_m = n.get('south_m', 0)
    
    # 以圆楼为原点计算像素坐标
    # east_m 向东（右）为正
    # south_m 向南（下）为正
    px = circular_px + east_m * scale
    py = circular_py + south_m * scale
    
    # 小圆点
    r = 8
    draw.ellipse([(px-r, py-r), (px+r, py+r)], fill='green', outline='white', width=2)
    
    # 只标记特定房间
    if nid in ['A-301', 'A-302', 'A-303', 'A-320', 'A-321', 'A-328', 'A-329', 'A-330']:
        draw.text((px+10, py-10), nid, fill='red', font=font_small)

# 绘制圆楼原点（使用观察到的位置）
origin_px = circular_px
origin_py = circular_py
cross_size = 30
draw.line([(origin_px - cross_size, origin_py), (origin_px + cross_size, origin_py)], 
          fill='red', width=4)
draw.line([(origin_px, origin_py - cross_size), (origin_px, origin_py + cross_size)], 
          fill='red', width=4)
draw.text((origin_px + 30, origin_py - 20), "圆楼原点", fill='red', font=font)

# 保存
output_path = 'data/visualizations/3F_hires_A_zone_marked.jpg'
os.makedirs(os.path.dirname(output_path), exist_ok=True)
img.save(output_path, quality=95)
print(f"已保存: {output_path}")
print(f"A 区房间数: {len(a_rooms)}")

# 打印 A-301 信息
a301 = nodes['A-301']
px = circular_px + a301['east_m'] * scale
py = circular_py + a301['south_m'] * scale
print(f"\nA-301:")
print(f"  east_m={a301['east_m']}, south_m={a301['south_m']}")
print(f"  px={px:.1f} ({px/img_w*100:.1f}%)")
print(f"  py={py:.1f} ({py/img_h*100:.1f}%)")

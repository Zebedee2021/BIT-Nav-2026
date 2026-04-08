#!/usr/bin/env python3
"""检查 C-103 位置和 1F 楼层图范围"""
import json
from PIL import Image, ImageDraw

# 加载 v7 数据
with open('data/wencui_building_v7.json', encoding='utf-8') as f:
    data = json.load(f)

# 检查 1F 图
img = Image.open('data/floorplans_hires/1F_hires.jpg')
print(f'1F hires 尺寸: {img.size}')

# C-103 位置
node = data['nodes'].get('C-103')
if node:
    print(f'\nC-103: east_m={node.get("east_m")}, south_m={node.get("south_m")}')
    
    # 计算像素位置
    HIRES_ORIGIN_X = 164 * 3  # 492
    HIRES_ORIGIN_Y = 563 * 3  # 1689
    HIRES_PX_PER_M = 15
    
    px = HIRES_ORIGIN_X + node['east_m'] * HIRES_PX_PER_M
    py = HIRES_ORIGIN_Y + node['south_m'] * HIRES_PX_PER_M
    
    print(f'C-103 像素位置: ({px:.1f}, {py:.1f})')
    print(f'1F 图范围: x[0, {img.size[0]}], y[0, {img.size[1]}]')
    print(f'  x 在范围内: {0 <= px < img.size[0]}')
    print(f'  y 在范围内: {0 <= py < img.size[1]}')
    
    # 检查所有 C 区 1F 房间
    print('\nC 区 1F 房间位置:')
    c_rooms = []
    for nid, n in data['nodes'].items():
        if nid.startswith('C-') and n.get('floor') == '1F' and n.get('type') == 'room':
            if n.get('east_m') is not None and n.get('south_m') is not None:
                px = HIRES_ORIGIN_X + n['east_m'] * HIRES_PX_PER_M
                py = HIRES_ORIGIN_Y + n['south_m'] * HIRES_PX_PER_M
                in_bounds = 0 <= px < img.size[0] and 0 <= py < img.size[1]
                c_rooms.append((nid, px, py, in_bounds))
                print(f'  {nid}: ({px:.0f}, {py:.0f}) - {"在图内" if in_bounds else "超出图外"}')
    
    # 在图上标记所有 C 区房间
    draw = ImageDraw.Draw(img)
    for nid, px, py, in_bounds in c_rooms:
        color = 'green' if in_bounds else 'red'
        r = 30
        x, y = int(px), int(py)
        draw.ellipse([x-r, y-r, x+r, y+r], outline=color, width=3)
        draw.text((x+r+5, y), nid, fill=color)
    
    img.save('data/debug_C_zone_1F.jpg')
    print('\n已保存标记图到 data/debug_C_zone_1F.jpg')

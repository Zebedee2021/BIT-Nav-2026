#!/usr/bin/env python3
"""检查房间位置数据"""
import json
from PIL import Image, ImageDraw

# 加载 v7 数据
with open('data/wencui_building_v7.json', encoding='utf-8') as f:
    data = json.load(f)

# 查找 B-221
node = data['nodes'].get('B-221')
if node:
    print(f'B-221 found:')
    print(f'  east_m={node.get("east_m")}')
    print(f'  south_m={node.get("south_m")}')
    print(f'  floor={node.get("floor")}')
    print(f'  type={node.get("type")}')
else:
    print('B-221 not found')
    print('\nB区房间示例:')
    count = 0
    for nid, n in data['nodes'].items():
        if nid.startswith('B-') and n.get('type') == 'room':
            print(f'{nid}: east_m={n.get("east_m")}, south_m={n.get("south_m")}')
            count += 1
            if count >= 5:
                break

# 检查 3F 高清图尺寸
img = Image.open('data/floorplans_hires/3F_hires.jpg')
print(f'\n3F hires size: {img.size}')

# 测试坐标转换
HIRES_SCALE = 15
img_w, img_h = img.size
center_x = img_w / 2
center_y = img_h / 2

# 测试：原点应该在图片中心
print(f'\n坐标转换测试 (15px/m):')
print(f'  原点 (0, 0) -> 像素: ({center_x}, {center_y})')

# 测试：B区房间应该在南侧（south_m 正）
if node:
    east_m = node.get('east_m', 0)
    south_m = node.get('south_m', 0)
    px = center_x + east_m * HIRES_SCALE
    py = center_y - south_m * HIRES_SCALE
    print(f'\nB-221 像素位置: ({px}, {py})')
    
    # 在图上标记
    draw = ImageDraw.Draw(img)
    r = 30
    draw.ellipse([px-r, py-r, px+r, py+r], outline='red', width=3)
    draw.text((px+r+5, py), 'B-221', fill='red')
    img.save('data/debug_B221_position.jpg')
    print('已保存到 data/debug_B221_position.jpg')

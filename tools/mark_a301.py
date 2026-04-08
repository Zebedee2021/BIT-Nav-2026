#!/usr/bin/env python3
"""标记 A-301 在 3F 楼层图上"""
import json
from PIL import Image, ImageDraw, ImageFont
import os

# 加载 v6 数据
with open('data/wencui_building_v6.json', encoding='utf-8') as f:
    data = json.load(f)

nodes = data['nodes']

# 获取 A-301 坐标
a301 = nodes['A-301']
ux, uy = a301['ux'], a301['uy']
east_m, south_m = a301['east_m'], a301['south_m']

# 圆楼坐标
circular = nodes['circular_hall_1F']
circular_ux, circular_uy = circular['ux'], circular['uy']

print(f"A-301: ux={ux}, uy={uy}, east_m={east_m}, south_m={south_m}")
print(f"圆楼: ux={circular_ux}, uy={circular_uy}")

# 加载 3F 楼层图
img_path = 'data/floorplans_hires/3F_hires.jpg'
img = Image.open(img_path)
img_w, img_h = img.size
print(f"图片尺寸: {img_w} x {img_h}")

# 计算像素坐标
# 比例尺 5px/m，圆楼原点 (164, 564)
scale = 5
origin_ux, origin_uy = 164, 564

center_x, center_y = img_w / 2, img_h / 2

# A-301 像素坐标（上北下南）
px = center_x + east_m * scale
py = center_y + south_m * scale

# 圆楼像素坐标
origin_px = center_x + circular['east_m'] * scale
origin_py = center_y + circular['south_m'] * scale

print(f"A-301 像素坐标: ({px:.1f}, {py:.1f})")
print(f"圆楼像素坐标: ({origin_px:.1f}, {origin_py:.1f})")

# 创建绘图对象
draw = ImageDraw.Draw(img)

# 绘制圆楼原点（红色十字）
cross_size = 30
line_width = 4
draw.line([(origin_px - cross_size, origin_py), (origin_px + cross_size, origin_py)], 
          fill='red', width=line_width)
draw.line([(origin_px, origin_py - cross_size), (origin_px, origin_py + cross_size)], 
          fill='red', width=line_width)

# 绘制 A-301（绿色圆点）
radius = 25
draw.ellipse([(px - radius, py - radius), (px + radius, py + radius)], 
             fill='green', outline='white', width=4)

# 添加标签
try:
    font = ImageFont.truetype("C:/Windows/Fonts/simhei.ttf", 40)
except:
    font = ImageFont.load_default()

# A-301 标签
draw.text((px + 30, py - 20), "A-301", fill='green', font=font)

# 圆楼标签
draw.text((origin_px + 30, origin_py - 20), "圆楼原点", fill='red', font=font)

# 保存图片
output_path = 'data/visualizations/3F_hires_A301_marked.jpg'
os.makedirs(os.path.dirname(output_path), exist_ok=True)
img.save(output_path, quality=95)
print(f"\n已保存到: {output_path}")

# 显示相对位置
print(f"\n相对位置:")
print(f"  A-301 在圆楼: 东{east_m}m, 南{south_m}m")
print(f"  水平: {px/img_w*100:.1f}% ({'左' if px < center_x else '右'})")
print(f"  垂直: {py/img_h*100:.1f}% ({'上' if py < center_y else '下'})")

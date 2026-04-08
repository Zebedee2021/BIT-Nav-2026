#!/usr/bin/env python3
"""调试 A-301 位置"""
import json

with open('data/wencui_building_v6.json', encoding='utf-8') as f:
    data = json.load(f)

nodes = data['nodes']

# A-301 坐标
a301 = nodes['A-301']
print('A-301:')
print('  ux=', a301['ux'], ', uy=', a301['uy'])
print('  east_m=', a301['east_m'], ', south_m=', a301['south_m'])
print()

# 圆楼坐标
circular = nodes['circular_hall_1F']
print('圆楼:')
print('  ux=', circular['ux'], ', uy=', circular['uy'])
print('  east_m=', circular['east_m'], ', south_m=', circular['south_m'])
print()

# 计算 A-301 相对于圆楼的位置
dx = a301['ux'] - circular['ux']
dy = a301['uy'] - circular['uy']
print('A-301 相对于圆楼:')
print('  dx=', dx, ', dy=', dy)
print('  east_m=', dx/5, ', south_m=', dy/5)
print()

# 图片尺寸
img_w, img_h = 2235, 3614
center_x, center_y = img_w/2, img_h/2
print('图片中心:', center_x, center_y)
print()

# 计算像素坐标（使用 east_m/south_m 直接）
px = center_x + a301['east_m'] * 5
py = center_y - a301['south_m'] * 5  # 上南下北
print('A-301 像素坐标:')
print('  px=', px, '(', px/img_w*100, '%)')
print('  py=', py, '(', py/img_h*100, '%)')
print()

# 圆楼像素坐标
origin_px = center_x + circular['east_m'] * 5
origin_py = center_y - circular['south_m'] * 5
print('圆楼像素坐标:')
print('  px=', origin_px)
print('  py=', origin_py)

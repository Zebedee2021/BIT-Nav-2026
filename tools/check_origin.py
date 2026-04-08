#!/usr/bin/env python3
"""检查各楼层圆楼中心位置"""
from PIL import Image
import json

# 加载 unified_params.json
with open('data/floorplans_unified/unified_params.json', encoding='utf-8') as f:
    params = json.load(f)

print("各楼层圆楼中心位置（unified 坐标系）：")
print("-" * 50)

for floor in range(1, 11):
    floor_str = f"{floor}F"
    img_path = f'data/floorplans_unified/{floor_str}_unified.jpg'
    
    try:
        img = Image.open(img_path)
        print(f"{floor_str}: 图片尺寸 {img.size}")
    except:
        print(f"{floor_str}: 无法加载图片")

print("\n当前原点设置（来自 unified_params.json）：")
print(f"HALL_PX = {params.get('HALL_PX')}")
print(f"HALL_PY = {params.get('HALL_PY')}")

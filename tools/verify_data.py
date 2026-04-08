#!/usr/bin/env python3
"""验证建筑数据与楼层图匹配"""
import json
import os
from PIL import Image

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 加载预测数据
building_file = os.path.join(base_dir, 'data', 'wencui_building_v5_predicted_v2.json')
with open(building_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

nodes = data.get('nodes', {})

# 统计信息
total = len(nodes)
rooms = [n for n in nodes.values() if n.get('type') == 'room']
ocr_rooms = [n for n in rooms if 'ocr_conf' in n]
predicted_rooms = [n for n in rooms if n.get('predicted')]

print("=" * 60)
print("建筑数据验证报告")
print("=" * 60)
print(f"文件: {building_file}")
print(f"总节点数: {total}")
print(f"房间节点: {len(rooms)}")
print(f"  - OCR识别: {len(ocr_rooms)}")
print(f"  - 算法预测: {len(predicted_rooms)}")

# 显示前5个房间示例
print("\n房间坐标示例:")
print("-" * 60)
for i, (node_id, node) in enumerate(list(nodes.items())[:5]):
    if node.get('type') == 'room':
        x = node.get('x', 0)
        y = node.get('y', 0)
        floor = node.get('floor', '')
        source = 'OCR' if 'ocr_conf' in node else ('预测' if node.get('predicted') else '原始')
        print(f"  {node_id}: x={x:.0f}, y={y:.0f}, floor={floor}, source={source}")

# 检查坐标范围
print("\n坐标范围统计:")
print("-" * 60)
for floor in ['1F', '2F', '3F', '4F', '5F']:
    floor_nodes = [n for n in rooms if n.get('floor') == floor]
    if floor_nodes:
        xs = [n.get('x', 0) for n in floor_nodes]
        ys = [n.get('y', 0) for n in floor_nodes]
        print(f"  {floor}: X=[{min(xs):.0f}, {max(xs):.0f}], Y=[{min(ys):.0f}, {max(ys):.0f}], 房间数={len(floor_nodes)}")

# 检查高清楼层图尺寸
print("\n高清楼层图尺寸:")
print("-" * 60)
hires_dir = os.path.join(base_dir, 'data', 'floorplans_hires')
for floor in ['1F', '2F', '3F', '4F', '5F']:
    img_path = os.path.join(hires_dir, f'{floor}_hires.jpg')
    if os.path.exists(img_path):
        img = Image.open(img_path)
        print(f"  {floor}: {img.size}")
        img.close()

# 计算坐标与图片的匹配度
print("\n坐标与图片匹配分析:")
print("-" * 60)
for floor in ['1F']:
    floor_nodes = [n for n in rooms if n.get('floor') == floor]
    if floor_nodes:
        xs = [n.get('x', 0) for n in floor_nodes]
        ys = [n.get('y', 0) for n in floor_nodes]
        x_range = max(xs) - min(xs)
        y_range = max(ys) - min(ys)
        
        img_path = os.path.join(hires_dir, f'{floor}_hires.jpg')
        if os.path.exists(img_path):
            img = Image.open(img_path)
            img_w, img_h = img.size
            img.close()
            
            print(f"  {floor} 坐标范围: {x_range:.0f} x {y_range:.0f}")
            print(f"  {floor} 图片尺寸: {img_w} x {img_h}")
            print(f"  X比例: {x_range/img_w:.2f}, Y比例: {y_range/img_h:.2f}")

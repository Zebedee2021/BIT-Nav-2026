#!/usr/bin/env python3
"""调试坐标映射问题"""
import json
from PIL import Image
import os

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 加载建筑数据
building_file = os.path.join(base_dir, 'data', 'wencui_building_v5_predicted_v2.json')
with open(building_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 查找 A-301 的坐标
nodes = data.get('nodes', {})
if 'A-301' in nodes:
    node = nodes['A-301']
    print(f"A-301 坐标:")
    print(f"  x={node.get('x')}, y={node.get('y')}")
    print(f"  ux={node.get('ux')}, uy={node.get('uy')}")
    print(f"  floor={node.get('floor')}")
    print(f"  zone={node.get('zone')}")

# 查找圆楼/报告厅参考点
for node_id, node in nodes.items():
    if '报告厅' in node.get('name', '') or node_id == 'CIRCULAR':
        print(f"\n{node_id} (报告厅/圆楼):")
        print(f"  x={node.get('x')}, y={node.get('y')}")
        print(f"  ux={node.get('ux')}, uy={node.get('uy')}")
        print(f"  floor={node.get('floor')}")

# 查看 3F 高清楼层图尺寸
img_path = os.path.join(base_dir, 'data', 'floorplans_hires', '3F_hires.jpg')
if os.path.exists(img_path):
    img = Image.open(img_path)
    print(f"\n3F_hires.jpg 尺寸: {img.size}")
    print(f"  宽度: {img.width}, 高度: {img.height}")
    print(f"  中心点: ({img.width/2}, {img.height/2})")
    img.close()

# 查看 A 区其他房间坐标
print("\n3F A区房间坐标:")
for node_id, node in nodes.items():
    if node.get('floor') == '3F' and node.get('zone') == 'A':
        ux = node.get('ux', 0)
        uy = node.get('uy', 0)
        if ux != 0 or uy != 0:
            print(f"  {node_id}: ux={ux:.0f}, uy={uy:.0f}")

# 查看 K 区房间坐标（应该在北侧）
print("\n3F K区房间坐标:")
for node_id, node in nodes.items():
    if node.get('floor') == '3F' and node.get('zone') == 'K':
        ux = node.get('ux', 0)
        uy = node.get('uy', 0)
        if ux != 0 or uy != 0:
            print(f"  {node_id}: ux={ux:.0f}, uy={uy:.0f}")
            break  # 只显示第一个

# 查看关键节点的 east_m 和 south_m
print("\n关键节点的 east_m/south_m:")
for nid in ['A-301', 'K-301', 'CIRCULAR', 'I-101', 'L-301']:
    if nid in nodes:
        n = nodes[nid]
        print(f"  {nid}:")
        print(f"    ux={n.get('ux')}, uy={n.get('uy')}")
        print(f"    east_m={n.get('east_m')}, south_m={n.get('south_m')}")

# 查找 south_m 为正（南）的节点
print("\n3F south_m 为正（南）的节点:")
for nid, n in nodes.items():
    if n.get('floor') == '3F':
        sm = n.get('south_m', 0)
        if sm > 50:  # 明显在南边
            print(f"  {nid}: south_m={sm}, zone={n.get('zone')}")

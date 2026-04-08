#!/usr/bin/env python3
"""分析 wencui_building_v6.json"""
import json
from collections import Counter

with open('data/wencui_building_v6.json', encoding='utf-8') as f:
    data = json.load(f)

print("=" * 60)
print("wencui_building_v6.json 数据分析")
print("=" * 60)

# 1. 基础统计
nodes = data.get('nodes', {})
edges = data.get('edges', [])

print(f"\n【基础统计】")
print(f"  总节点数: {len(nodes)}")
print(f"  总边数: {len(edges)}")

# 2. 节点类型分布
node_types = Counter(n.get('type', 'unknown') for n in nodes.values())
print(f"\n【节点类型分布】")
for t, c in node_types.most_common():
    print(f"  {t}: {c}")

# 3. 楼层分布
floors = Counter(n.get('floor', 'unknown') for n in nodes.values())
print(f"\n【楼层分布】")
for f, c in sorted(floors.items(), key=lambda x: x[0]):
    print(f"  {f}: {c} 个节点")

# 4. 区域分布
zones = Counter(n.get('zone', 'unknown') for n in nodes.values())
print(f"\n【区域分布】")
for z, c in zones.most_common():
    print(f"  {z}: {c}")

# 5. 坐标系统计
print(f"\n【坐标系统计】")
has_ux_uy = sum(1 for n in nodes.values() if n.get('ux', 0) != 0 or n.get('uy', 0) != 0)
has_east_south = sum(1 for n in nodes.values() if n.get('east_m') is not None)
has_xy = sum(1 for n in nodes.values() if n.get('x', 0) != 0 or n.get('y', 0) != 0)
print(f"  有 ux/uy 坐标: {has_ux_uy}")
print(f"  有 east_m/south_m: {has_east_south}")
print(f"  有 x/y 坐标: {has_xy}")

# 6. 圆楼/报告厅原点
print(f"\n【坐标原点】")
for nid in ['circular_hall_1F', 'circular_hall_2F', 'circular_hall_3F']:
    if nid in nodes:
        n = nodes[nid]
        print(f"  {nid}:")
        print(f"    ux={n.get('ux')}, uy={n.get('uy')}")
        print(f"    east_m={n.get('east_m')}, south_m={n.get('south_m')}")

# 7. 样本节点坐标对比
print(f"\n【样本节点坐标 (v6 vs 之前)】")
sample_nodes = ['A-301', 'K-301', 'C-301', 'I-101', 'D-301']
for nid in sample_nodes:
    if nid in nodes:
        n = nodes[nid]
        print(f"  {nid}: ux={n.get('ux')}, uy={n.get('uy')}, "
              f"east_m={n.get('east_m')}, south_m={n.get('south_m')}, "
              f"floor={n.get('floor')}, zone={n.get('zone')}")

# 8. 边类型统计
print(f"\n【边类型分布】")
if edges and isinstance(edges[0], dict):
    edge_types = Counter(e.get('type', 'unknown') for e in edges)
    for t, c in edge_types.most_common():
        print(f"  {t}: {c}")
else:
    print(f"  边数据格式: {type(edges[0]) if edges else 'empty'}")
    print(f"  总边数: {len(edges)}")

# 9. 边数据示例
print(f"\n【边数据示例 (前3条)】")
for i, e in enumerate(edges[:3]):
    print(f"  边 {i}: {e}")

# 10. 坐标范围
print(f"\n【坐标范围】")
ux_vals = [n.get('ux', 0) for n in nodes.values() if n.get('ux', 0) != 0]
uy_vals = [n.get('uy', 0) for n in nodes.values() if n.get('uy', 0) != 0]
print(f"  ux 范围: {min(ux_vals):.0f} ~ {max(ux_vals):.0f}")
print(f"  uy 范围: {min(uy_vals):.0f} ~ {max(uy_vals):.0f}")

# 11. v6 关键变化
print(f"\n【v6 关键变化】")
print(f"  1. 节点数从 ~1126 增加到 1434 (+308)")
print(f"  2. 所有节点都有 ux/uy 坐标 (1434/1434)")
print(f"  3. 几乎所有节点都有 east_m/south_m (1432/1434)")
print(f"  4. A-301 坐标变化: v5(729,157) -> v6(654,716)")
print(f"  5. A-301 south_m: v5(-81.2/北) -> v6(30.4/南)")
print(f"  6. 圆楼原点: ux=164, uy=564 (各层相同)")

print("\n" + "=" * 60)

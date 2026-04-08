#!/usr/bin/env python3
"""检查各区实际楼层"""
import json

with open('data/wencui_building_v6.json', encoding='utf-8') as f:
    data = json.load(f)

nodes = data['nodes']

print("=" * 60)
print("各区楼层验证")
print("=" * 60)

for zone in ['A', 'F', 'I', 'B', 'M', 'G', 'H']:
    floors = set(n.get('floor') for n in nodes.values() if n.get('zone') == zone)
    count = sum(1 for n in nodes.values() if n.get('zone') == zone)
    sorted_floors = sorted(floors, key=lambda x: int(x.replace('F', '')))
    print(f"{zone}区: 楼层={sorted_floors}, 节点数={count}")
#!/usr/bin/env python3
"""检查 A 区房间坐标"""
import json

with open('data/wencui_building_v6.json', encoding='utf-8') as f:
    data = json.load(f)

nodes = data['nodes']

# 获取所有 3F A 区房间
a_rooms = [(nid, n) for nid, n in nodes.items() 
           if n.get('floor') == '3F' and n.get('zone') == 'A' and n.get('type') == 'room']

# 按 south_m 排序（南到北）
a_rooms.sort(key=lambda x: x[1].get('south_m', 0))

print('3F A 区房间 (按 south_m 排序，从南到北):')
print('-' * 60)
for nid, n in a_rooms[:20]:
    sm = n.get('south_m', 0)
    em = n.get('east_m', 0)
    uy = n.get('uy', 0)
    print(f'{nid}: south_m={sm:.1f}, east_m={em:.1f}, uy={uy}')

print()
print('A-301 附近房间:')
for nid, n in a_rooms:
    sm = n.get('south_m', 0)
    if 25 <= sm <= 35:  # A-301 south_m=30.4
        em = n.get('east_m', 0)
        uy = n.get('uy', 0)
        print(f'{nid}: south_m={sm:.1f}, east_m={em:.1f}, uy={uy}')

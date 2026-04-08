#!/usr/bin/env python3
"""检查圆形会议厅坐标"""
import json

with open('data/wencui_building_v7.json', encoding='utf-8') as f:
    data = json.load(f)

for nid in ['circular_hall_1F', 'circular_hall_2F']:
    node = data['nodes'].get(nid)
    if node:
        print(f"{nid}: east_m={node['east_m']}, south_m={node['south_m']}")

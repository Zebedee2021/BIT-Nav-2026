#!/usr/bin/env python3
"""检查 v6 文件"""
import json

with open('data/wencui_building_v6.json', encoding='utf-8') as f:
    data = json.load(f)

print('v6 文件统计:')
print('  节点数:', len(data.get('nodes', {})))
print('  边数:', len(data.get('edges', [])))

# 检查 A-301
node = data.get('nodes', {}).get('A-301', {})
print('\nA-301 坐标:')
print('  ux=', node.get('ux'), ', uy=', node.get('uy'))
print('  east_m=', node.get('east_m'), ', south_m=', node.get('south_m'))

# 检查圆楼
node = data.get('nodes', {}).get('circular_hall_1F', {})
print('\n圆楼原点:')
print('  ux=', node.get('ux'), ', uy=', node.get('uy'))
print('  east_m=', node.get('east_m'), ', south_m=', node.get('south_m'))

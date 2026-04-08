#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统计文萃楼各楼层房间数量"""

import json

def main():
    with open('data/wencui_building.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    nodes = data['nodes']

    # 按楼层统计
    floor_stats = {}
    for node in nodes.values():
        floor = node.get('floor', 'Unknown')
        node_type = node.get('type', 'unknown')
        
        if floor not in floor_stats:
            floor_stats[floor] = {'room': 0, 'corridor': 0, 'stairs': 0, 'elevator': 0, 'entrance': 0, 'total': 0}
        
        if node_type in floor_stats[floor]:
            floor_stats[floor][node_type] += 1
        floor_stats[floor]['total'] += 1

    # 按楼层顺序输出
    floor_order = ['1F', '2F', '3F', '4F', '5F', '6F', '7F', '8F', '9F', '10F']
    print('楼层 | 房间 | 走廊 | 楼梯 | 电梯 | 入口 | 总计')
    print('-----|------|------|------|------|------|------')
    for floor in floor_order:
        if floor in floor_stats:
            s = floor_stats[floor]
            print(f"{floor}  | {s['room']:4d} | {s['corridor']:4d} | {s['stairs']:4d} | {s['elevator']:4d} | {s['entrance']:4d} | {s['total']:4d}")

    # 总计
    total_rooms = sum(s['room'] for s in floor_stats.values())
    total_corridors = sum(s['corridor'] for s in floor_stats.values())
    total_stairs = sum(s['stairs'] for s in floor_stats.values())
    total_elevators = sum(s['elevator'] for s in floor_stats.values())
    total_entrances = sum(s['entrance'] for s in floor_stats.values())
    total_all = sum(s['total'] for s in floor_stats.values())

    print('-----|------|------|------|------|------|------')
    print(f"总计 | {total_rooms:4d} | {total_corridors:4d} | {total_stairs:4d} | {total_elevators:4d} | {total_entrances:4d} | {total_all:4d}")

if __name__ == '__main__':
    main()

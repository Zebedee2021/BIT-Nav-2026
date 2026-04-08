#!/usr/bin/env python3
"""测试保存功能"""
import json
import time

# 读取当前数据
with open('data/wencui_building_v7.json', encoding='utf-8') as f:
    data = json.load(f)

# 修改 circular_hall_2F 的坐标
data['nodes']['circular_hall_2F']['east_m'] = 0.0
data['nodes']['circular_hall_2F']['south_m'] = 0.0
data['nodes']['circular_hall_2F']['verified_fixed'] = True

# 保存
with open('data/wencui_building_v7.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print('已保存测试数据')
print(f'修改时间: {time.strftime("%H:%M:%S")}')

"""
文萃楼建筑导航图数据生成器
基于官方楼层图分析，生成 wencui_building.json

用法: python tools/generate_building_graph.py
输出: data/wencui_building.json
"""

import json
import math
import os

# === 常量 ===
IMG_W, IMG_H = 3000, 2000

# === 分区包围盒定义 (3000x2000 像素坐标) ===
# 基于 2F 官方楼层图的分析，1-2F 共用此布局
# 格式: (x_min, y_min, x_max, y_max)

# 四座角楼 (1F-10F)
BBOX_L = (60, 220, 380, 580)     # 左上角楼
BBOX_J = (60, 900, 380, 1260)    # 左下角楼
BBOX_C = (2340, 220, 2910, 580)  # 右上角楼
BBOX_E = (2340, 900, 2910, 1260) # 右下角楼

# 顶部连接区 (M 和 B)
BBOX_M_TOP = (150, 65, 960, 135)   # M 区顶部一排
BBOX_M_LOW = (870, 200, 1200, 430) # M 区下方区域
BBOX_B_TOP = (1520, 65, 2800, 155) # B 区顶部一排
BBOX_B_LOW = (1520, 200, 1720, 430)# B 区下方区域

# 内翼 (I 和 F)
BBOX_I = (630, 300, 950, 780)   # I 区左内翼
BBOX_F = (1720, 300, 2050, 780) # F 区右内翼

# 通道/门厅
BBOX_K = (60, 530, 210, 860)    # K 区左侧通道

# 底部区域 (H 和 G, 仅 1-2F)
BBOX_H_UP = (430, 1100, 660, 1370)   # H 区上部房间
BBOX_H_BOT = (100, 1760, 680, 1880)  # H 区底部一排
BBOX_G_UP = (1600, 1100, 1830, 1370) # G 区上部房间
BBOX_G_BOT = (1520, 1760, 2870, 1880)# G 区底部一排

# 圆楼
CIRCULAR_CENTER = (1370, 1440)
CIRCULAR_R = 200

# A 区 (3F-7F, 顶部中央双排) — 替代 M/B 顶部和中央空白区
BBOX_A = (380, 65, 1520, 350)

# D 区 (3F-7F, 右翼中间区域)
BBOX_D = (2060, 350, 2340, 780)

# K 区有房间时 (3F-7F)
BBOX_K_ROOMS = (60, 530, 210, 860)

# 门厅
LOBBY_WEST = (170, 790)
LOBBY_EAST = (2700, 790)


# === 基础设施位置 ===
# 每个角楼有 2 个楼梯和 1 个电梯
# 定义为相对于角楼包围盒的比例位置

def corner_infra_positions(bbox):
    """计算角楼基础设施位置"""
    x1, y1, x2, y2 = bbox
    w, h = x2 - x1, y2 - y1
    return {
        'stairs_1': (x1 + w * 0.08, y1 + h * 0.15),  # 顶部楼梯
        'stairs_2': (x1 + w * 0.08, y1 + h * 0.85),  # 底部楼梯
        'elevator': (x1 + w * 0.40, y1 + h * 0.45),   # 中部电梯
        'restroom': (x1 + w * 0.35, y1 + h * 0.30),   # 卫生间
        'corridor': (x1 + w * 0.45, y1 + h * 0.50),   # 走廊中心
    }


# === 角楼房间布局模板 ===
# 角楼内房间按周边布局: 上、右、下、左四面
# 返回 [(relative_x, relative_y), ...] 位置列表

def distribute_corner_rooms(bbox, room_ids):
    """在角楼包围盒内分配房间位置"""
    x1, y1, x2, y2 = bbox
    w, h = x2 - x1, y2 - y1
    n = len(room_ids)

    if n == 0:
        return {}

    # 将房间分配到四面墙
    # 右侧墙: 约 40% 的房间 (最多的一面)
    # 上方: 约 20%
    # 下方: 约 25%
    # 左侧: 约 15%
    n_right = max(1, int(n * 0.40))
    n_top = max(1, int(n * 0.20))
    n_bottom = max(1, int(n * 0.25))
    n_left = n - n_right - n_top - n_bottom
    if n_left < 0:
        n_left = 0
        n_bottom = n - n_right - n_top

    positions = {}
    idx = 0

    # 上方房间 (沿顶部, 从左到右)
    for i in range(n_top):
        if idx >= n:
            break
        rx = 0.15 + 0.65 * (i / max(1, n_top - 1)) if n_top > 1 else 0.35
        ry = 0.05
        positions[room_ids[idx]] = (x1 + w * rx, y1 + h * ry)
        idx += 1

    # 右侧房间 (沿右墙, 从上到下)
    for i in range(n_right):
        if idx >= n:
            break
        rx = 0.88
        ry = 0.12 + 0.76 * (i / max(1, n_right - 1)) if n_right > 1 else 0.50
        positions[room_ids[idx]] = (x1 + w * rx, y1 + h * ry)
        idx += 1

    # 下方房间 (沿底部, 从右到左)
    for i in range(n_bottom):
        if idx >= n:
            break
        rx = 0.70 - 0.55 * (i / max(1, n_bottom - 1)) if n_bottom > 1 else 0.35
        ry = 0.92
        positions[room_ids[idx]] = (x1 + w * rx, y1 + h * ry)
        idx += 1

    # 左侧房间 (沿左墙, 从下到上)
    for i in range(n_left):
        if idx >= n:
            break
        rx = 0.05
        ry = 0.80 - 0.55 * (i / max(1, n_left - 1)) if n_left > 1 else 0.50
        positions[room_ids[idx]] = (x1 + w * rx, y1 + h * ry)
        idx += 1

    return positions


def distribute_row(bbox, room_ids, vertical=False):
    """在包围盒内将房间排成一行 (水平或垂直)"""
    x1, y1, x2, y2 = bbox
    positions = {}
    n = len(room_ids)
    if n == 0:
        return positions

    for i, rid in enumerate(room_ids):
        t = i / max(1, n - 1) if n > 1 else 0.5
        if vertical:
            x = (x1 + x2) / 2
            y = y1 + (y2 - y1) * (0.08 + 0.84 * t)
        else:
            x = x1 + (x2 - x1) * (0.05 + 0.90 * t)
            y = (y1 + y2) / 2
        positions[rid] = (int(x), int(y))
    return positions


def distribute_wing(bbox, room_ids):
    """在内翼包围盒内分配房间 (沿走廊两侧)"""
    x1, y1, x2, y2 = bbox
    w, h = x2 - x1, y2 - y1
    positions = {}
    n = len(room_ids)
    if n == 0:
        return positions

    for i, rid in enumerate(room_ids):
        t = i / max(1, n - 1) if n > 1 else 0.5
        # 交替放在走廊两侧
        if i % 2 == 0:
            x = x1 + w * 0.25
        else:
            x = x1 + w * 0.75
        y = y1 + h * (0.08 + 0.84 * t)
        positions[rid] = (int(x), int(y))
    return positions


def distribute_a_zone(bbox, room_ids):
    """A 区双排布局 (3F-7F, 上下两排密集房间)"""
    x1, y1, x2, y2 = bbox
    w, h = x2 - x1, y2 - y1
    positions = {}
    n = len(room_ids)
    if n == 0:
        return positions

    half = n // 2
    # 上排
    for i in range(half):
        rid = room_ids[i]
        t = i / max(1, half - 1) if half > 1 else 0.5
        x = x1 + w * (0.05 + 0.90 * t)
        y = y1 + h * 0.25
        positions[rid] = (int(x), int(y))

    # 下排
    for i in range(half, n):
        rid = room_ids[i]
        t = (i - half) / max(1, (n - half) - 1) if (n - half) > 1 else 0.5
        x = x1 + w * (0.05 + 0.90 * t)
        y = y1 + h * 0.75
        positions[rid] = (int(x), int(y))

    return positions


# === 楼层房间数据 ===
# 基于 docs/building/floors.md 和官方楼层图分析

def gen_range(prefix, start, end, skip=None):
    """生成房间编号列表, 如 gen_range('L-2', 1, 19) → ['L-201', ..., 'L-219']"""
    skip = skip or []
    return [f"{prefix}{i:02d}" if i < 100 else f"{prefix}{i}"
            for i in range(start, end + 1) if i not in skip]


def make_room_ids(zone, floor_num, start, end, skip=None, extras=None):
    """生成标准房间 ID 列表"""
    prefix = f"{zone}-{floor_num}"
    ids = []
    skip = skip or []
    for i in range(start, end + 1):
        if i not in skip:
            ids.append(f"{prefix}{i:02d}" if i < 10 else f"{prefix}{i}")
    if extras:
        ids.extend(extras)
    return ids


# --- 2F 房间数据 ---
ROOMS_2F = {
    'L': ['L-201', 'L-2102', 'L-203', 'L-205', 'L-207', 'L-208', 'L-209',
          'L-210', 'L-211', 'L-212', 'L-213', 'L-214', 'L-215', 'L-216',
          'L-218', 'L-219'],
    'J': ['J-201', 'J-202', 'J-203', 'J-205', 'J-207', 'J-208', 'J-209',
          'J-210', 'J-211', 'J-212', 'J-213', 'J-214', 'J-215', 'J-216',
          'J-218', 'J-219'],
    'C': ['C-201', 'C-205', 'C-206', 'C-208'],
    'E': ['E-201', 'E-203', 'E-205', 'E-207', 'E-208', 'E-209', 'E-210',
          'E-211', 'E-212', 'E-213', 'E-214', 'E-215', 'E-216', 'E-218',
          'E-219'],
    'M_top': ['M-221', 'M-222', 'M-223', 'M-224', 'M-225', 'M-227', 'M-228'],
    'M_low': ['M-230', 'M-231', 'M-232', 'M-233'],
    'B_top': ['B-221', 'B-222', 'B-223', 'B-224', 'B-225', 'B-227', 'B-228'],
    'B_low': ['B-230', 'B-231', 'B-232', 'B-233'],
    'I': ['I-201', 'I-202', 'I-203', 'I-204', 'I-205', 'I-207', 'I-208'],
    'F': ['F-201', 'F-202', 'F-203', 'F-204', 'F-205', 'F-207', 'F-208'],
    'H_bot': ['H-221', 'H-222', 'H-225', 'H-227', 'H-228', 'H-229'],
    'H_up': ['H-232', 'H-233'],
    'G_bot': ['G-221', 'G-222', 'G-223', 'G-224', 'G-225', 'G-227', 'G-228', 'G-229'],
    'G_up': ['G-232', 'G-233'],
}

# --- 1F 房间数据 ---
ROOMS_1F = {
    'L': [f'L-{i}' for i in [101,102,103,104,105,106,107,108,109,110,
          111,112,113,114,115,116,117,118,119,120,121,122]],
    'J': [f'J-{i}' for i in [101,102,103,104,105,106,107,108,109,110,
          111,112,113,114,115,116,117,118,119,120,121,122]],
    'C': [f'C-{i}' for i in [101,102,103,104,105,106,107,108,109]],
    'E': [f'E-{i}' for i in [101,102,103,104,105,106,107,108,109,110,
          111,112,113,114,115,116,117,118,119,120,121,122]],
    'M_top': [f'M-{i}' for i in [123,124,125,126,127,128,129,130,131,132,133,134,135]],
    'M_low': [],
    'B_top': [f'B-{i}' for i in [128,129,130,131,132,133,134,135,136,137,138,139,140]],
    'B_low': [],
    'I': [f'I-{i}' for i in [101,102,103,104]],
    'F': [f'F-{i}' for i in [101,102,103,104]],
    'H_bot': [f'H-{i}' for i in [123,124,125,126,127,128,129,130]],
    'H_up': [],
    'G_bot': [f'G-{i}' for i in [123,124,125,126,127,128,129,130]],
    'G_up': [],
}

# --- 3F 房间数据 ---
ROOMS_3F = {
    'L': [f'L-{i}' for i in range(301, 320)],
    'J': [f'J-{i}' for i in range(301, 321)],
    'C': [f'C-{i}' for i in range(301, 307)],
    'E': [f'E-{i}' for i in range(301, 321)],
    'A': [f'A-{i}' for i in range(301, 343)],
    'I': [f'I-{i}' for i in range(301, 309)],
    'F': [f'F-{i}' for i in range(301, 309)],
    'K': [f'K-{i}' for i in range(301, 310)],
    'D': [f'D-{i}' for i in range(301, 310)],
}

# --- 4F 房间数据 ---
ROOMS_4F = {
    'L': [f'L-{i}' for i in range(401, 417)],
    'J': [f'J-{i}' for i in range(401, 418)],
    'C': [f'C-{i}' for i in range(404, 410)],
    'E': [f'E-{i}' for i in range(401, 418)],
    'A': [f'A-{i}' for i in range(401, 443)],
    'I': [f'I-{i}' for i in range(401, 409)],
    'F': [f'F-{i}' for i in range(401, 408)],
    'K': [f'K-{i}' for i in range(401, 412)],
    'D': [f'D-{i}' for i in range(401, 412)],
}

# --- 5F 房间数据 ---
ROOMS_5F = {
    'L': [f'L-{i}' for i in range(501, 519)],
    'J': [f'J-{i}' for i in range(501, 520)],
    'C': [f'C-{i}' for i in range(503, 509)],
    'E': [f'E-{i}' for i in range(501, 520)],
    'A': [f'A-{i}' for i in range(501, 543)],
    'I': [f'I-{i}' for i in range(501, 509)],
    'F': [f'F-{i}' for i in range(501, 509)],
    'K': [f'K-{i}' for i in range(501, 512)],
    'D': [f'D-{i}' for i in range(501, 512)],
}

# --- 6F 房间数据 ---
ROOMS_6F = {
    'L': [f'L-{i}' for i in range(601, 617)],
    'J': [f'J-{i}' for i in range(601, 618)],
    'C': [f'C-{i}' for i in range(601, 616)],
    'E': [f'E-{i}' for i in range(601, 618)],
    'A': [f'A-{i}' for i in range(601, 643)],
    'I': [f'I-{i}' for i in range(601, 609)],
    'F': [f'F-{i}' for i in range(601, 609)],
    'K': [f'K-{i}' for i in range(601, 612)],
    'D': [f'D-{i}' for i in range(601, 612)],
}

# --- 7F 房间数据 ---
ROOMS_7F = {
    'L': [f'L-{i}' for i in range(701, 719)],
    'J': [f'J-{i}' for i in range(701, 720)],
    'C': [f'C-{i}' for i in range(701, 717)],
    'E': [f'E-{i}' for i in range(701, 720)],
    'A': [f'A-{i}' for i in range(701, 743)],
    'I': [f'I-{i}' for i in range(701, 709)],
    'F': [f'F-{i}' for i in range(701, 709)],
    'K': [f'K-{i}' for i in range(701, 712)],
    'D': [f'D-{i}' for i in range(701, 712)],
}

# --- 8F 房间数据 ---
ROOMS_8F = {
    'L': [f'L-{i}' for i in range(801, 815)],
    'J': [f'J-{i}' for i in range(801, 816)],
    'C': [f'C-{i}' for i in range(801, 815)],
    'E': [f'E-{i}' for i in range(801, 816)],
}

# --- 9F 房间数据 ---
ROOMS_9F = {
    'L': [f'L-{i}' for i in range(901, 916)],
    'J': [f'J-{i}' for i in range(901, 917)],
    'C': [f'C-{i}' for i in range(901, 916)],
    'E': [f'E-{i}' for i in range(901, 917)],
}

# --- 10F 房间数据 ---
ROOMS_10F = {
    'L': [f'L-{i}' for i in range(1001, 1014)],
    'J': [f'J-{i}' for i in range(1001, 1014)],
    'C': [f'C-{i}' for i in range(1001, 1017)],
    'E': [f'E-{i}' for i in range(1001, 1015)],
}

ALL_ROOMS = {
    '1F': ROOMS_1F, '2F': ROOMS_2F, '3F': ROOMS_3F, '4F': ROOMS_4F,
    '5F': ROOMS_5F, '6F': ROOMS_6F, '7F': ROOMS_7F,
    '8F': ROOMS_8F, '9F': ROOMS_9F, '10F': ROOMS_10F,
}

# === 楼层类型 ===
FLOOR_TYPE_LOW = ['1F', '2F']           # 全 13 区 + 圆楼
FLOOR_TYPE_MID = ['3F', '4F', '5F', '6F', '7F']  # 11 区 (无 G/H)
FLOOR_TYPE_HIGH = ['8F', '9F', '10F']   # 仅角楼


# === 核心: 分区在各楼层的定义 ===
# 每层可用的分区及其包围盒

def get_zones_for_floor(floor):
    """获取指定楼层的分区定义"""
    zones = {}
    fn = int(floor.replace('F', ''))

    # 四座角楼 (所有楼层)
    zones['L'] = {'bbox': BBOX_L, 'layout': 'corner'}
    zones['J'] = {'bbox': BBOX_J, 'layout': 'corner'}
    zones['C'] = {'bbox': BBOX_C, 'layout': 'corner'}
    zones['E'] = {'bbox': BBOX_E, 'layout': 'corner'}

    if floor in FLOOR_TYPE_LOW:
        # 1-2F: M, B (顶排+下方), I, F, K, H, G, 圆楼
        zones['M_top'] = {'bbox': BBOX_M_TOP, 'layout': 'row'}
        zones['M_low'] = {'bbox': BBOX_M_LOW, 'layout': 'column'}
        zones['B_top'] = {'bbox': BBOX_B_TOP, 'layout': 'row'}
        zones['B_low'] = {'bbox': BBOX_B_LOW, 'layout': 'column'}
        zones['I'] = {'bbox': BBOX_I, 'layout': 'wing'}
        zones['F'] = {'bbox': BBOX_F, 'layout': 'wing'}
        zones['K'] = {'bbox': BBOX_K, 'layout': 'passage'}
        zones['H_bot'] = {'bbox': BBOX_H_BOT, 'layout': 'row'}
        zones['H_up'] = {'bbox': BBOX_H_UP, 'layout': 'column'}
        zones['G_bot'] = {'bbox': BBOX_G_BOT, 'layout': 'row'}
        zones['G_up'] = {'bbox': BBOX_G_UP, 'layout': 'column'}

    elif floor in FLOOR_TYPE_MID:
        # 3-7F: A(双排), I, F, K(有房间), D
        zones['A'] = {'bbox': BBOX_A, 'layout': 'a_zone'}
        zones['I'] = {'bbox': BBOX_I, 'layout': 'wing'}
        zones['F'] = {'bbox': BBOX_F, 'layout': 'wing'}
        zones['K'] = {'bbox': BBOX_K_ROOMS, 'layout': 'column'}
        zones['D'] = {'bbox': BBOX_D, 'layout': 'wing'}

    # 高层 (8-10F): 只有角楼，已在上面定义

    return zones


# === 生成节点 ===

def generate_floor_nodes(floor, rooms_data, zones_def):
    """生成一层楼的所有节点"""
    nodes = {}
    fn = int(floor.replace('F', ''))

    # 1. 生成房间节点
    for zone_key, zone_info in zones_def.items():
        bbox = zone_info['bbox']
        layout = zone_info['layout']

        # 获取房间列表
        room_list = rooms_data.get(zone_key, [])
        if not room_list:
            continue

        # 根据布局类型分配位置
        if layout == 'corner':
            positions = distribute_corner_rooms(bbox, room_list)
        elif layout == 'row':
            positions = distribute_row(bbox, room_list, vertical=False)
        elif layout == 'column':
            positions = distribute_row(bbox, room_list, vertical=True)
        elif layout == 'wing':
            positions = distribute_wing(bbox, room_list)
        elif layout == 'a_zone':
            positions = distribute_a_zone(bbox, room_list)
        elif layout == 'passage':
            positions = distribute_row(bbox, room_list, vertical=True)
        else:
            positions = distribute_row(bbox, room_list)

        # 确定分区名 (去掉 _top, _low, _bot, _up 后缀)
        zone_name = zone_key.split('_')[0].upper()

        for rid, (x, y) in positions.items():
            nodes[rid] = {
                'id': rid,
                'type': 'room',
                'floor': floor,
                'zone': zone_name,
                'name': rid,
                'description': '',
                'x': int(x),
                'y': int(y),
            }

    # 2. 生成走廊节点 (每个分区一个走廊中心)
    active_zones = set()
    for zone_key, zone_info in zones_def.items():
        base_zone = zone_key.split('_')[0].upper()
        if base_zone in active_zones:
            continue
        active_zones.add(base_zone)

        bbox = zone_info['bbox']
        cx = int((bbox[0] + bbox[2]) / 2)
        cy = int((bbox[1] + bbox[3]) / 2)

        cid = f"corridor_{floor}_{base_zone}"
        nodes[cid] = {
            'id': cid,
            'type': 'corridor',
            'floor': floor,
            'zone': base_zone,
            'name': f'{floor}{base_zone}区走廊',
            'description': f'文萃楼{floor} {base_zone}区主走廊',
            'x': cx,
            'y': cy,
        }

    # 3. 生成楼梯/电梯节点 (角楼)
    for zone_letter, bbox in [('L', BBOX_L), ('J', BBOX_J), ('C', BBOX_C), ('E', BBOX_E)]:
        infra = corner_infra_positions(bbox)

        # 楼梯 1
        sid1 = f'stairs_{zone_letter}_1_{floor}'
        sx1, sy1 = infra['stairs_1']
        nodes[sid1] = {
            'id': sid1, 'type': 'stairs', 'floor': floor, 'zone': zone_letter,
            'name': f'{zone_letter}区楼梯1', 'description': f'{zone_letter}区楼梯间1',
            'x': int(sx1), 'y': int(sy1),
        }

        # 楼梯 2
        sid2 = f'stairs_{zone_letter}_2_{floor}'
        sx2, sy2 = infra['stairs_2']
        nodes[sid2] = {
            'id': sid2, 'type': 'stairs', 'floor': floor, 'zone': zone_letter,
            'name': f'{zone_letter}区楼梯2', 'description': f'{zone_letter}区楼梯间2',
            'x': int(sx2), 'y': int(sy2),
        }

        # 电梯
        eid = f'elevator_{zone_letter}_{floor}'
        ex, ey = infra['elevator']
        nodes[eid] = {
            'id': eid, 'type': 'elevator', 'floor': floor, 'zone': zone_letter,
            'name': f'{zone_letter}区电梯', 'description': f'{zone_letter}区电梯厅',
            'x': int(ex), 'y': int(ey),
        }

    # I/F 区楼梯和电梯 (1F-7F)
    if fn <= 7:
        for zone_letter, bbox in [('I', BBOX_I), ('F', BBOX_F)]:
            mid_x = int((bbox[0] + bbox[2]) / 2)
            mid_y = int((bbox[1] + bbox[3]) / 2)

            sid = f'stairs_{zone_letter}_1_{floor}'
            nodes[sid] = {
                'id': sid, 'type': 'stairs', 'floor': floor, 'zone': zone_letter,
                'name': f'{zone_letter}区楼梯', 'description': f'{zone_letter}区楼梯间',
                'x': mid_x + 40, 'y': mid_y,
            }

            eid = f'elevator_{zone_letter}_{floor}'
            nodes[eid] = {
                'id': eid, 'type': 'elevator', 'floor': floor, 'zone': zone_letter,
                'name': f'{zone_letter}区电梯', 'description': f'{zone_letter}区电梯厅',
                'x': mid_x - 40, 'y': mid_y + 50,
            }

    # M/B 区楼梯 (1F-7F)
    if fn <= 7:
        m_stair_x, m_stair_y = int((BBOX_M_TOP[2] + 50)), int((BBOX_M_TOP[1] + BBOX_M_TOP[3]) / 2)
        nodes[f'stairs_M_1_{floor}'] = {
            'id': f'stairs_M_1_{floor}', 'type': 'stairs', 'floor': floor, 'zone': 'M',
            'name': 'M区楼梯', 'description': 'M区楼梯间',
            'x': m_stair_x, 'y': m_stair_y,
        }

        b_stair_x = int(BBOX_B_TOP[0] - 30)
        nodes[f'stairs_B_1_{floor}'] = {
            'id': f'stairs_B_1_{floor}', 'type': 'stairs', 'floor': floor, 'zone': 'B',
            'name': 'B区楼梯', 'description': 'B区楼梯间',
            'x': b_stair_x, 'y': m_stair_y,
        }

    # 4. 入口和门厅 (仅 1F)
    if floor == '1F':
        nodes['entrance_west_1F'] = {
            'id': 'entrance_west_1F', 'type': 'entrance', 'floor': '1F', 'zone': 'K',
            'name': '西门入口', 'description': '文萃楼西侧门厅入口',
            'x': LOBBY_WEST[0], 'y': LOBBY_WEST[1],
        }
        nodes['entrance_east_1F'] = {
            'id': 'entrance_east_1F', 'type': 'entrance', 'floor': '1F', 'zone': 'D',
            'name': '东门入口', 'description': '文萃楼东侧门厅入口',
            'x': LOBBY_EAST[0], 'y': LOBBY_EAST[1],
        }

    # 5. 圆楼 (1-2F)
    if floor in FLOOR_TYPE_LOW:
        nodes[f'circular_hall_{floor}'] = {
            'id': f'circular_hall_{floor}', 'type': 'room', 'floor': floor, 'zone': 'CIRCULAR',
            'name': '圆楼', 'description': '圆形报告厅',
            'x': CIRCULAR_CENTER[0], 'y': CIRCULAR_CENTER[1],
        }

    return nodes


# === 生成边 ===

def generate_floor_edges(floor, nodes):
    """生成一层楼的所有边"""
    edges = []
    fn = int(floor.replace('F', ''))

    # 获取本层节点按类型分组
    corridors = {nid: n for nid, n in nodes.items() if n['type'] == 'corridor' and n['floor'] == floor}
    rooms = {nid: n for nid, n in nodes.items() if n['type'] == 'room' and n['floor'] == floor}
    stairs = {nid: n for nid, n in nodes.items() if n['type'] == 'stairs' and n['floor'] == floor}
    elevators = {nid: n for nid, n in nodes.items() if n['type'] == 'elevator' and n['floor'] == floor}
    entrances = {nid: n for nid, n in nodes.items() if n['type'] == 'entrance' and n['floor'] == floor}

    # 1. 房间 → 所属区走廊
    for rid, room in rooms.items():
        zone = room['zone']
        corridor_id = f"corridor_{floor}_{zone}"
        if corridor_id in corridors:
            edges.append([rid, corridor_id])

    # 2. 楼梯/电梯 → 所属区走廊
    for sid, stair in stairs.items():
        zone = stair['zone']
        corridor_id = f"corridor_{floor}_{zone}"
        if corridor_id in corridors:
            edges.append([sid, corridor_id])

    for eid, elev in elevators.items():
        zone = elev['zone']
        corridor_id = f"corridor_{floor}_{zone}"
        if corridor_id in corridors:
            edges.append([eid, corridor_id])

    # 3. 入口 → 走廊
    for eid, ent in entrances.items():
        zone = ent['zone']
        corridor_id = f"corridor_{floor}_{zone}"
        if corridor_id in corridors:
            edges.append([eid, corridor_id])

    # 4. 走廊 → 走廊 (分区间连接)
    # 定义分区邻接关系
    if floor in FLOOR_TYPE_LOW:
        adjacency = [
            ('L', 'M'), ('L', 'K'), ('M', 'I'), ('M', 'B'),
            ('I', 'K'), ('K', 'J'),
            ('J', 'H'), ('H', 'CIRCULAR'), ('CIRCULAR', 'G'), ('G', 'E'),
            ('B', 'F'), ('B', 'C'),
            ('F', 'E'),
        ]
    elif floor in FLOOR_TYPE_MID:
        adjacency = [
            ('L', 'A'), ('L', 'K'),
            ('A', 'I'), ('A', 'B'), ('A', 'D'),
            ('I', 'K'), ('K', 'J'),
            ('B', 'F'), ('B', 'C'),
            ('F', 'D'), ('F', 'E'),
        ]
    else:  # HIGH
        adjacency = [
            ('L', 'J'), ('L', 'C'),  # 通过空置楼层的走廊
            ('C', 'E'), ('J', 'E'),
        ]

    for z1, z2 in adjacency:
        c1 = f"corridor_{floor}_{z1}"
        c2 = f"corridor_{floor}_{z2}"
        if c1 in corridors and c2 in corridors:
            edges.append([c1, c2])

    return edges


def generate_vertical_edges(all_nodes):
    """生成跨层垂直边 (楼梯/电梯连接)"""
    edges = []
    floors = ['1F', '2F', '3F', '4F', '5F', '6F', '7F', '8F', '9F', '10F']

    # 收集所有楼梯和电梯
    stairs_by_prefix = {}
    elevators_by_prefix = {}

    for nid, node in all_nodes.items():
        if node['type'] == 'stairs':
            # 提取前缀: stairs_L_1_2F → stairs_L_1
            parts = nid.rsplit('_', 1)
            prefix = parts[0]
            floor = parts[1]
            stairs_by_prefix.setdefault(prefix, {})[floor] = nid
        elif node['type'] == 'elevator':
            parts = nid.rsplit('_', 1)
            prefix = parts[0]
            floor = parts[1]
            elevators_by_prefix.setdefault(prefix, {})[floor] = nid

    # 连接相邻楼层
    for prefix, floor_map in {**stairs_by_prefix, **elevators_by_prefix}.items():
        for i in range(len(floors) - 1):
            f1 = floors[i]
            f2 = floors[i + 1]
            if f1 in floor_map and f2 in floor_map:
                edges.append([floor_map[f1], floor_map[f2]])

    return edges


# === 主函数 ===

def generate_building_data():
    """生成完整的建筑导航图数据"""

    building = {
        'name': '文萃楼',
        'description': '北京理工大学良乡校区文萃楼 — 13个分区(A-M)构成的U形教学科研楼宇群',
        'floors': ['1F', '2F', '3F', '4F', '5F', '6F', '7F', '8F', '9F', '10F'],
    }

    all_nodes = {}
    all_edges = []

    floors = building['floors']
    for floor in floors:
        rooms_data = ALL_ROOMS.get(floor, {})
        zones_def = get_zones_for_floor(floor)
        floor_nodes = generate_floor_nodes(floor, rooms_data, zones_def)
        all_nodes.update(floor_nodes)

        floor_edges = generate_floor_edges(floor, all_nodes)
        all_edges.extend(floor_edges)

    # 垂直边
    vert_edges = generate_vertical_edges(all_nodes)
    all_edges.extend(vert_edges)

    # 楼层布局
    floor_layouts = {}
    for floor in floors:
        fn = int(floor.replace('F', ''))
        floor_rooms = [n for n in all_nodes.values() if n['floor'] == floor and n['type'] == 'room']
        floor_layouts[floor] = {
            'width': IMG_W,
            'height': IMG_H,
            'description': f'{floor} 平面图 ({len(floor_rooms)} 间房)',
        }

    # 汇总
    result = {
        'building': building,
        'nodes': all_nodes,
        'edges': all_edges,
        'floor_layouts': floor_layouts,
    }

    return result


def main():
    data = generate_building_data()

    # 统计
    total_nodes = len(data['nodes'])
    total_edges = len(data['edges'])
    room_count = sum(1 for n in data['nodes'].values() if n['type'] == 'room')
    corridor_count = sum(1 for n in data['nodes'].values() if n['type'] == 'corridor')
    stairs_count = sum(1 for n in data['nodes'].values() if n['type'] == 'stairs')
    elevator_count = sum(1 for n in data['nodes'].values() if n['type'] == 'elevator')
    entrance_count = sum(1 for n in data['nodes'].values() if n['type'] == 'entrance')

    print(f"=== 文萃楼导航图数据生成完成 ===")
    print(f"总节点数: {total_nodes}")
    print(f"  房间: {room_count}")
    print(f"  走廊: {corridor_count}")
    print(f"  楼梯: {stairs_count}")
    print(f"  电梯: {elevator_count}")
    print(f"  入口: {entrance_count}")
    print(f"总边数:  {total_edges}")
    print()

    # 按楼层统计
    for floor in data['building']['floors']:
        fn_rooms = [n for n in data['nodes'].values() if n['floor'] == floor and n['type'] == 'room']
        fn_total = [n for n in data['nodes'].values() if n['floor'] == floor]
        fn_edges = [e for e in data['edges']
                    if any(data['nodes'].get(e[0], {}).get('floor') == floor or
                           data['nodes'].get(e[1], {}).get('floor') == floor
                           for _ in [1])]
        print(f"  {floor}: {len(fn_rooms)} 房间, {len(fn_total)} 总节点")

    # 输出
    out_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    out_path = os.path.join(out_dir, 'wencui_building.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n已写入: {out_path}")
    print(f"文件大小: {os.path.getsize(out_path) / 1024:.1f} KB")


if __name__ == '__main__':
    main()

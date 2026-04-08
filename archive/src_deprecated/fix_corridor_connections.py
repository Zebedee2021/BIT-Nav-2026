"""
修复走廊连通性
添加缺失的走廊之间的连接边
"""

import json
import os
from typing import List, Tuple, Set


def get_corridor_nodes(building_data: dict) -> dict:
    """
    获取所有走廊节点，按楼层分组
    
    Returns:
        {floor: [corridor_node_ids]}
    """
    corridors = {}
    nodes = building_data.get("nodes", {})
    
    for node_id, node in nodes.items():
        if node.get("type") == "corridor":
            floor = node.get("floor")
            if floor not in corridors:
                corridors[floor] = []
            corridors[floor].append(node_id)
    
    return corridors


def get_zone_from_corridor(corridor_id: str) -> str:
    """从走廊ID提取区域信息"""
    # corridor_XF_Z -> Z
    parts = corridor_id.split("_")
    if len(parts) >= 3:
        return parts[2]
    return ""


def should_connect(corridor1: str, corridor2: str) -> bool:
    """
    判断两个走廊是否应该连接
    根据区域字母顺序判断相邻性
    """
    zone1 = get_zone_from_corridor(corridor1)
    zone2 = get_zone_from_corridor(corridor2)
    
    if not zone1 or not zone2:
        return False
    
    # 定义区域相邻关系（基于文萃楼U形结构）
    # L-M-A-B-C-D-E-F-G-H-I-J-K 是主序列
    adjacent_zones = {
        "L": ["M", "K"],
        "M": ["L", "A"],
        "A": ["M", "B"],
        "B": ["A", "C"],
        "C": ["B", "D"],
        "D": ["C", "E"],
        "E": ["D", "F"],
        "F": ["E", "G"],
        "G": ["F", "H"],
        "H": ["G", "I"],
        "I": ["H", "J"],
        "J": ["I", "K"],
        "K": ["J", "L"],
    }
    
    return zone2 in adjacent_zones.get(zone1, [])


def fix_corridor_connections(building_data_path: str, output_path: str):
    """
    修复走廊连通性
    
    Args:
        building_data_path: 输入文件路径
        output_path: 输出文件路径
    """
    # 加载数据
    with open(building_data_path, 'r', encoding='utf-8') as f:
        building_data = json.load(f)
    
    edges = building_data.get("edges", [])
    edges_set = set(tuple(edge) for edge in edges)
    
    # 获取所有走廊
    corridors_by_floor = get_corridor_nodes(building_data)
    
    print("=" * 60)
    print("修复走廊连通性")
    print("=" * 60)
    
    new_edges = []
    
    for floor, corridors in corridors_by_floor.items():
        print(f"\n{floor}: {len(corridors)} 个走廊")
        
        # 检查每对走廊是否应该连接
        for i, c1 in enumerate(corridors):
            for c2 in corridors[i+1:]:
                if should_connect(c1, c2):
                    # 检查是否已连接
                    edge1 = (c1, c2)
                    edge2 = (c2, c1)
                    
                    if edge1 not in edges_set and edge2 not in edges_set:
                        # 添加连接
                        new_edges.append([c1, c2])
                        edges_set.add(edge1)
                        print(f"  添加连接: {c1} <-> {c2}")
    
    # 合并边
    all_edges = edges + new_edges
    building_data["edges"] = all_edges
    
    # 添加修复记录
    if "metadata" not in building_data:
        building_data["metadata"] = {}
    
    building_data["metadata"]["corridor_fix"] = {
        "fixed_date": "2025-03-27",
        "new_edges_count": len(new_edges),
        "total_edges": len(all_edges)
    }
    
    # 保存
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(building_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'=' * 60}")
    print(f"修复完成!")
    print(f"新增连接: {len(new_edges)} 条")
    print(f"总边数: {len(all_edges)}")
    print(f"输出文件: {output_path}")
    print("=" * 60)
    
    return building_data


def verify_connections(building_data: dict, floor: str = "3F"):
    """
    验证指定楼层的走廊连通性
    """
    from pathfinding import BuildingGraph
    
    graph = BuildingGraph(building_data)
    corridors = get_corridor_nodes(building_data)
    
    print(f"\n{'=' * 60}")
    print(f"验证 {floor} 走廊连通性")
    print("=" * 60)
    
    floor_corridors = corridors.get(floor, [])
    
    for corridor in floor_corridors:
        neighbors = list(graph.get_neighbors(corridor))
        # 只统计走廊邻居
        corridor_neighbors = [n for n in neighbors if "corridor" in n]
        print(f"{corridor}: {len(corridor_neighbors)} 个走廊邻居")
        if corridor_neighbors:
            print(f"  -> {corridor_neighbors}")


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(__file__))
    
    input_path = os.path.join(base_dir, "data", "wencui_building_aligned.json")
    output_path = os.path.join(base_dir, "data", "wencui_building_aligned_fixed.json")
    
    # 修复连通性
    fixed_data = fix_corridor_connections(input_path, output_path)
    
    # 验证
    verify_connections(fixed_data, "3F")
    verify_connections(fixed_data, "1F")

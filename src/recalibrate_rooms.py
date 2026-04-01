"""
重新标定所有房间坐标
使用对齐后的楼层图坐标系，更新 wencui_building.json 中所有房间的坐标
"""

import json
import os
from typing import Dict, Tuple
from copy import deepcopy


def load_align_params(params_path: str) -> Dict:
    """加载对齐参数"""
    with open(params_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def transform_coordinate(
    x: float, 
    y: float, 
    scale: float, 
    offset_x: float, 
    offset_y: float
) -> Tuple[float, float]:
    """
    将原始坐标转换为对齐后的标准化坐标
    
    Returns:
        (x_std, y_std) 四舍五入到整数
    """
    x_std = x * scale + offset_x
    y_std = y * scale + offset_y
    return (round(x_std), round(y_std))


def recalibrate_building_data(
    building_data_path: str,
    align_params_path: str,
    output_path: str
):
    """
    重新标定建筑数据中所有房间的坐标
    
    Args:
        building_data_path: 原始 wencui_building.json 路径
        align_params_path: align_params.json 路径
        output_path: 输出文件路径
    """
    # 加载数据
    with open(building_data_path, 'r', encoding='utf-8') as f:
        building_data = json.load(f)
    
    align_params = load_align_params(align_params_path)
    
    # 创建新的节点数据
    new_nodes = {}
    
    print("=" * 60)
    print("重新标定房间坐标")
    print("=" * 60)
    
    # 统计信息
    stats = {
        "total": 0,
        "recalibrated": 0,
        "skipped": 0,
        "by_floor": {}
    }
    
    for node_id, node in building_data.get("nodes", {}).items():
        stats["total"] += 1
        
        floor = node.get("floor")
        if not floor:
            # 没有楼层信息的节点，保持原样
            new_nodes[node_id] = node
            stats["skipped"] += 1
            continue
        
        # 检查该楼层是否有对齐参数
        if floor not in align_params:
            # 没有对齐参数的楼层（如 overview），保持原样
            new_nodes[node_id] = node
            stats["skipped"] += 1
            continue
        
        # 获取对齐参数
        params = align_params[floor]
        scale = params["scale"]
        offset_x, offset_y = params["offset"]
        
        # 转换坐标
        original_x = node.get("x", 0)
        original_y = node.get("y", 0)
        
        new_x, new_y = transform_coordinate(original_x, original_y, scale, offset_x, offset_y)
        
        # 创建新的节点数据
        new_node = deepcopy(node)
        new_node["x"] = new_x
        new_node["y"] = new_y
        # 保留原始坐标信息
        new_node["original_x"] = original_x
        new_node["original_y"] = original_y
        
        new_nodes[node_id] = new_node
        stats["recalibrated"] += 1
        
        # 按楼层统计
        if floor not in stats["by_floor"]:
            stats["by_floor"][floor] = 0
        stats["by_floor"][floor] += 1
    
    # 更新建筑数据
    new_building_data = deepcopy(building_data)
    new_building_data["nodes"] = new_nodes
    
    # 添加元数据
    new_building_data["metadata"] = {
        "coordinate_system": "aligned",
        "reference_point": "L-xxx01 rooms aligned to (100, 200)",
        "target_size": [1400, 1000],
        "calibration_date": "2025-03-27"
    }
    
    # 保存新数据
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(new_building_data, f, ensure_ascii=False, indent=2)
    
    # 打印统计
    print(f"\n处理统计:")
    print(f"  总节点数: {stats['total']}")
    print(f"  重新标定: {stats['recalibrated']}")
    print(f"  保持原样: {stats['skipped']}")
    print(f"\n各楼层房间数:")
    for floor in sorted(stats["by_floor"].keys()):
        print(f"  {floor}: {stats['by_floor'][floor]} 个房间")
    
    print(f"\n输出文件: {output_path}")
    
    return new_building_data


def verify_calibration(
    building_data: Dict,
    align_params: Dict,
    sample_rooms: list = None
):
    """
    验证标定结果
    
    Args:
        building_data: 重新标定后的建筑数据
        align_params: 对齐参数
        sample_rooms: 要验证的示例房间列表，如 ["L-101", "L-201", "D-402"]
    """
    print("\n" + "=" * 60)
    print("验证标定结果")
    print("=" * 60)
    
    nodes = building_data.get("nodes", {})
    
    if sample_rooms is None:
        # 默认验证参考房间
        sample_rooms = ["L-101", "L-201", "L-401", "L-501", "L-601", 
                       "L-701", "L-801", "L-901", "L-1001"]
    
    print("\n参考房间对齐验证（应该都在 (100, 200) 附近）：")
    for room_id in sample_rooms:
        if room_id in nodes:
            node = nodes[room_id]
            print(f"  {room_id}: ({node['x']}, {node['y']}) "
                  f"[原始: ({node.get('original_x', '-')}, {node.get('original_y', '-')})]")
    
    # 验证一些特定房间
    print("\n其他房间示例:")
    sample_checks = ["L-110", "L-207", "D-402", "D-403"]
    for room_id in sample_checks:
        if room_id in nodes:
            node = nodes[room_id]
            print(f"  {room_id}: ({node['x']}, {node['y']}) "
                  f"[原始: ({node.get('original_x', '-')}, {node.get('original_y', '-')})]")


def generate_floor_layouts(building_data: Dict) -> Dict:
    """
    生成每个楼层的布局信息（用于可视化）
    
    Returns:
        更新的建筑数据
    """
    nodes = building_data.get("nodes", {})
    
    # 按楼层分组
    floor_nodes = {}
    for node_id, node in nodes.items():
        floor = node.get("floor")
        if not floor:
            continue
        if floor not in floor_nodes:
            floor_nodes[floor] = []
        floor_nodes[floor].append(node)
    
    # 生成 floor_layouts
    floor_layouts = {}
    for floor, nodes_list in floor_nodes.items():
        if not nodes_list:
            continue
        
        # 计算边界
        xs = [n["x"] for n in nodes_list]
        ys = [n["y"] for n in nodes_list]
        
        floor_layouts[floor] = {
            "width": 1400,
            "height": 1000,
            "min_x": min(xs),
            "max_x": max(xs),
            "min_y": min(ys),
            "max_y": max(ys),
            "room_count": len(nodes_list)
        }
    
    building_data["floor_layouts"] = floor_layouts
    return building_data


if __name__ == "__main__":
    import sys
    
    # 默认路径
    base_dir = os.path.dirname(os.path.dirname(__file__))
    building_data_path = os.path.join(base_dir, "data", "wencui_building.json")
    align_params_path = os.path.join(base_dir, "data", "floorplans_aligned", "align_params.json")
    output_path = os.path.join(base_dir, "data", "wencui_building_aligned.json")
    
    # 重新标定
    new_data = recalibrate_building_data(building_data_path, align_params_path, output_path)
    
    # 验证
    align_params = load_align_params(align_params_path)
    verify_calibration(new_data, align_params)
    
    # 生成楼层布局信息
    new_data = generate_floor_layouts(new_data)
    
    # 保存更新后的数据
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 60)
    print("重新标定完成!")
    print(f"输出文件: {output_path}")
    print("=" * 60)

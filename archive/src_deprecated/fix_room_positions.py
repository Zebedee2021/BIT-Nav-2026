"""
调整房间坐标，让它们靠近走廊
A-301 到 A-310 的 y 坐标应该靠近 corridor_3F_A 的 y=187
"""

import json
import os


def fix_a_zone_rooms(building_data_path: str, output_path: str):
    """
    调整 A 区房间坐标并移除不存在的 A-310
    
    根据楼层图：
    - A-301 到 A-309 在北侧走廊旁
    - A-310 不存在
    """
    # 加载数据
    with open(building_data_path, 'r', encoding='utf-8') as f:
        building_data = json.load(f)
    
    nodes = building_data.get("nodes", {})
    edges = building_data.get("edges", [])
    
    # corridor_3F_A 的 y 坐标
    corridor_y = 187
    
    # 需要调整的房间（A-301 到 A-309）
    rooms_to_fix = [f"A-{i}" for i in range(301, 310)]
    
    print("=" * 60)
    print("调整 A 区房间坐标")
    print("=" * 60)
    
    fixed_count = 0
    for room_id in rooms_to_fix:
        if room_id in nodes:
            node = nodes[room_id]
            old_y = node["y"]
            # 将 y 坐标调整到走廊位置
            node["y"] = corridor_y
            node["y_adjusted"] = True
            node["y_original"] = old_y
            fixed_count += 1
            print(f"{room_id}: y {old_y} -> {corridor_y}")
    
    # 移除不存在的 A-310
    if "A-310" in nodes:
        print("\n移除不存在的节点: A-310")
        del nodes["A-310"]
    
    # 移除与 A-310 相关的边
    edges_before = len(edges)
    edges = [edge for edge in edges if "A-310" not in edge]
    edges_after = len(edges)
    if edges_before != edges_after:
        print(f"移除与 A-310 相关的边: {edges_before - edges_after} 条")
    
    building_data["nodes"] = nodes
    building_data["edges"] = edges
    
    # 添加修复记录
    if "metadata" not in building_data:
        building_data["metadata"] = {}
    
    building_data["metadata"]["room_position_fix"] = {
        "fixed_date": "2025-03-27",
        "fixed_rooms": rooms_to_fix,
        "removed_room": "A-310",
        "fixed_count": fixed_count,
        "reason": "A-301 to A-309 y坐标调整到走廊位置，移除不存在的A-310"
    }
    
    # 保存
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(building_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'=' * 60}")
    print(f"修复完成!")
    print(f"调整房间数: {fixed_count}")
    print(f"输出文件: {output_path}")
    print("=" * 60)
    
    return building_data


def verify_fix(building_data: dict):
    """验证修复结果"""
    print("\n" + "=" * 60)
    print("验证修复结果")
    print("=" * 60)
    
    nodes = building_data.get("nodes", {})
    corridor = nodes.get("corridor_3F_A", {})
    
    print(f"corridor_3F_A: ({corridor.get('x')}, {corridor.get('y')})")
    print()
    
    for i in range(301, 310):  # A-301 到 A-309
        room_id = f"A-{i}"
        if room_id in nodes:
            room = nodes[room_id]
            x = room.get("x")
            y = room.get("y")
            old_y = room.get("y_original", y)
            print(f"{room_id}: ({x}, {y}) [原y: {old_y}]")


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(__file__))
    
    input_path = os.path.join(base_dir, "data", "wencui_building_aligned_fixed.json")
    output_path = os.path.join(base_dir, "data", "wencui_building_aligned_fixed.json")
    
    # 修复坐标
    fixed_data = fix_a_zone_rooms(input_path, output_path)
    
    # 验证
    verify_fix(fixed_data)

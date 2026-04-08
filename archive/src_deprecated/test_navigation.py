"""
测试导航算法 - C-101 到 A-301
"""

import json
import os
import sys

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from pathfinding import BuildingGraph, AStarPathfinder


def test_navigation():
    """测试导航"""
    base_dir = os.path.dirname(os.path.dirname(__file__))
    
    # 加载对齐后的建筑数据（使用修复后的文件）
    with open(os.path.join(base_dir, 'data', 'wencui_building_aligned_fixed.json'), 'r', encoding='utf-8') as f:
        building_data = json.load(f)
    
    graph = BuildingGraph(building_data)
    pathfinder = AStarPathfinder(graph)
    
    # 测试 C-101 到 A-301
    start = "C-101"
    end = "A-301"
    
    print("=" * 60)
    print(f"导航测试: {start} -> {end}")
    print("=" * 60)
    
    # 获取节点信息
    nodes = building_data.get("nodes", {})
    
    if start not in nodes:
        print(f"错误: 起点 {start} 不存在")
        return
    if end not in nodes:
        print(f"错误: 终点 {end} 不存在")
        return
    
    start_node = nodes[start]
    end_node = nodes[end]
    
    print(f"\n起点 {start}:")
    print(f"  楼层: {start_node.get('floor')}")
    print(f"  区域: {start_node.get('zone')}")
    print(f"  坐标: ({start_node.get('x')}, {start_node.get('y')})")
    print(f"  原始坐标: ({start_node.get('original_x')}, {start_node.get('original_y')})")
    
    print(f"\n终点 {end}:")
    print(f"  楼层: {end_node.get('floor')}")
    print(f"  区域: {end_node.get('zone')}")
    print(f"  坐标: ({end_node.get('x')}, {end_node.get('y')})")
    print(f"  原始坐标: ({end_node.get('original_x')}, {end_node.get('original_y')})")
    
    # 查找路径
    print(f"\n查找路径...")
    path = pathfinder.find_path(start, end)
    
    if path:
        print(f"✓ 找到路径，共 {len(path)} 个节点")
        print(f"\n路径详情:")
        
        # 获取详细路径信息
        path_details = pathfinder.get_path_details(path)
        total_distance = pathfinder.calculate_path_distance(path)
        
        current_floor = None
        for i, detail in enumerate(path_details):
            node = nodes.get(detail['to'])
            floor = detail['to_floor']
            
            # 检测楼层变化
            if floor != current_floor:
                if current_floor is not None:
                    print(f"  >> 楼层切换: {current_floor} -> {floor}")
                current_floor = floor
            
            action_icon = "🛗" if detail['action'] == 'elevator' else "🚶"
            print(f"  {i+1}. {action_icon} {detail['from']} -> {detail['to']} "
                  f"[{floor}] {detail['distance']:.1f}px")
        
        print(f"\n总距离: {total_distance:.1f} 像素")
        
    # 检查 corridor_1F_C 的邻居
    print(f"\n{'='*60}")
    print("检查 corridor_1F_C 的邻居:")
    print("="*60)
    neighbors = list(graph.get_neighbors("corridor_1F_C"))
    print(f"邻居数量: {len(neighbors)}")
    print(f"邻居列表: {neighbors[:10]}...")  # 只显示前10个
    
    # 检查是否包含电梯
    elevators = [n for n in neighbors if 'elevator' in n]
    print(f"\n电梯邻居: {elevators}")
    
    # 检查 C区电梯到 3F 终点的路径
    print(f"\n{'='*60}")
    print("测试: elevator_C_3F -> A-301")
    print("="*60)
    path_c_elev = pathfinder.find_path("elevator_C_3F", end)
    if path_c_elev:
        print(f"✓ 找到路径: {len(path_c_elev)} 节点")
        print(f"  路径: {path_c_elev}")
        dist = pathfinder.calculate_path_distance(path_c_elev)
        print(f"  距离: {dist:.1f}px")
        
        # 对比总路径
        print(f"\n{'='*60}")
        print("路径对比:")
        print("="*60)
        path_via_c = ["C-101", "corridor_1F_C", "elevator_C_1F", "elevator_C_2F", "elevator_C_3F"] + path_c_elev[1:]
        dist_via_c = pathfinder.calculate_path_distance(path_via_c)
        print(f"经 C区电梯: {len(path_via_c)} 节点, {dist_via_c:.1f}px")
        print(f"经 F区电梯: {len(path)} 节点, {total_distance:.1f}px")
        
        if dist_via_c < total_distance:
            print(f"✓ C区电梯更优 (节省 {total_distance - dist_via_c:.1f}px)")
        else:
            print(f"✗ F区电梯更优")
    else:
        print("✗ 未找到路径")
        print(f"  elevator_C_3F 邻居: {list(graph.get_neighbors('elevator_C_3F'))}")


if __name__ == "__main__":
    test_navigation()

#!/usr/bin/env python3
"""
v6 到 v7 数据迁移脚本
清理规则：
1. 移除 B/M/G 区的 3-7 层节点（实际为 2 层）
2. 移除 A 区的 1-2 层节点（实际为 3-7 层，1-2层为大厅/通道）
"""
import json
import os

def migrate_v6_to_v7():
    # 读取 v6 数据
    with open('data/wencui_building_v6.json', encoding='utf-8') as f:
        data = json.load(f)
    
    nodes = data['nodes']
    edges = data['edges']
    
    print("=" * 60)
    print("v6 到 v7 数据迁移")
    print("=" * 60)
    
    # 统计原始数据
    original_node_count = len(nodes)
    original_edge_count = len(edges)
    print(f"\n原始节点数: {original_node_count}")
    print(f"原始边数: {original_edge_count}")
    
    # 找出需要移除的节点
    nodes_to_remove = set()
    
    for node_id, node in nodes.items():
        zone = node.get('zone', '')
        floor = node.get('floor', '')
        floor_num = int(floor.replace('F', '')) if floor else 0
        
        # 规则1: B/M/G 区只保留 1-2 层
        if zone in ['B', 'M', 'G'] and floor_num >= 3:
            nodes_to_remove.add(node_id)
        
        # 规则2: A 区只保留 3-7 层
        if zone == 'A' and floor_num <= 2:
            nodes_to_remove.add(node_id)
    
    print(f"\n需要移除的节点数: {len(nodes_to_remove)}")
    
    # 按区域统计
    b_removed = sum(1 for nid in nodes_to_remove if nodes[nid].get('zone') == 'B')
    m_removed = sum(1 for nid in nodes_to_remove if nodes[nid].get('zone') == 'M')
    g_removed = sum(1 for nid in nodes_to_remove if nodes[nid].get('zone') == 'G')
    a_removed = sum(1 for nid in nodes_to_remove if nodes[nid].get('zone') == 'A')
    
    print(f"  - B区 3-7层: {b_removed} 个节点")
    print(f"  - M区 3-7层: {m_removed} 个节点")
    print(f"  - G区 3-7层: {g_removed} 个节点")
    print(f"  - A区 1-2层: {a_removed} 个节点")
    
    # 移除节点
    for node_id in nodes_to_remove:
        del nodes[node_id]
    
    # 移除与这些节点相关的边
    edges_to_remove = []
    for i, edge in enumerate(edges):
        if isinstance(edge, dict):
            if edge.get('from') in nodes_to_remove or edge.get('to') in nodes_to_remove:
                edges_to_remove.append(i)
        elif isinstance(edge, list) and len(edge) >= 2:
            if edge[0] in nodes_to_remove or edge[1] in nodes_to_remove:
                edges_to_remove.append(i)
    
    # 从后往前删除，避免索引变化
    for i in reversed(edges_to_remove):
        edges.pop(i)
    
    print(f"\n移除的边数: {len(edges_to_remove)}")
    
    # 统计新数据
    new_node_count = len(nodes)
    new_edge_count = len(edges)
    print(f"\n新节点数: {new_node_count}")
    print(f"新边数: {new_edge_count}")
    print(f"节点减少: {original_node_count - new_node_count}")
    print(f"边减少: {original_edge_count - new_edge_count}")
    
    # 更新版本信息
    data['version'] = 'v7'
    data['description'] = '清理 B/M/G 3-7层和 A 1-2层节点，符合实际建筑结构'
    
    # 保存 v7 数据
    output_path = 'data/wencui_building_v7.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ 已保存到: {output_path}")
    
    # 验证各区域楼层
    print("\n" + "=" * 60)
    print("v7 数据楼层分布验证")
    print("=" * 60)
    
    for zone in ['A', 'B', 'M', 'G', 'H', 'F', 'I']:
        zone_floors = set()
        zone_count = 0
        for node in nodes.values():
            if node.get('zone') == zone:
                zone_floors.add(node.get('floor'))
                zone_count += 1
        sorted_floors = sorted(zone_floors, key=lambda x: int(x.replace('F', '')))
        print(f"{zone}区: 楼层={sorted_floors}, 节点数={zone_count}")

if __name__ == '__main__':
    migrate_v6_to_v7()

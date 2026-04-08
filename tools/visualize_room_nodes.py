"""
房间节点可视化验证工具

将生成的房间节点数据叠加到楼层图上进行可视化验证

使用方法：
  python tools/visualize_room_nodes.py [楼层] [--data 数据文件]
  
示例：
  python tools/visualize_room_nodes.py 1F
  python tools/visualize_room_nodes.py 3F --data data/wencui_rooms_generated.json
"""

import json
import os
import sys
import argparse
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def load_nodes(data_path: str) -> dict:
    """加载节点数据"""
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('nodes', data)


def visualize_floor(floor: str, data_path: str, output_path: str = None):
    """
    可视化指定楼层的节点
    
    Args:
        floor: 楼层标识（如 1F, 2F）
        data_path: 节点数据文件路径
        output_path: 输出图片路径
    """
    # 加载楼层图
    floorplan_path = os.path.join(
        os.path.dirname(__file__), '..', 'wencui', f'{floor[:-1]}.jpg'
    )
    
    if not os.path.exists(floorplan_path):
        print(f"错误: 找不到楼层图 {floorplan_path}")
        return
    
    # 加载节点数据
    nodes = load_nodes(data_path)
    
    # 打开楼层图
    img = Image.open(floorplan_path)
    draw = ImageDraw.Draw(img)
    
    # 筛选当前楼层的节点
    floor_nodes = {k: v for k, v in nodes.items() if v.get('floor') == floor}
    
    print(f"楼层 {floor}: 找到 {len(floor_nodes)} 个节点")
    
    # 颜色配置
    colors = {
        'room': (255, 0, 0),      # 红色
        'stairs': (0, 255, 0),    # 绿色
        'elevator': (0, 0, 255),  # 蓝色
        'corridor': (255, 255, 0), # 黄色
        'entrance': (255, 128, 0), # 橙色
    }
    
    # 绘制节点
    for node_id, node in floor_nodes.items():
        x = node.get('x', 0)
        y = node.get('y', 0)
        node_type = node.get('type', 'room')
        zone = node.get('zone', '?')
        
        color = colors.get(node_type, (128, 128, 128))
        
        # 绘制圆点
        radius = 8 if node_type == 'room' else 12
        draw.ellipse([x-radius, y-radius, x+radius, y+radius], fill=color, outline=(255, 255, 255), width=2)
        
        # 绘制文字标签
        label = node_id
        if node_type != 'room':
            label = f"{node_type[:3]}"
        
        # 使用默认字体
        try:
            draw.text((x+10, y-5), label, fill=color)
        except:
            pass
    
    # 绘制统计信息
    room_count = len([n for n in floor_nodes.values() if n['type'] == 'room'])
    stairs_count = len([n for n in floor_nodes.values() if n['type'] == 'stairs'])
    elevator_count = len([n for n in floor_nodes.values() if n['type'] == 'elevator'])
    
    stats_text = f"Floor: {floor} | Rooms: {room_count} | Stairs: {stairs_count} | Elevators: {elevator_count}"
    
    # 保存或显示
    if output_path is None:
        output_path = os.path.join(
            os.path.dirname(__file__), '..', 'data', 'visualizations', f'{floor}_nodes_visualized.jpg'
        )
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path)
    print(f"可视化结果已保存到: {output_path}")
    
    return output_path


def visualize_all_floors(data_path: str):
    """可视化所有楼层"""
    floors = ['1F', '2F', '3F', '4F', '5F', '6F', '7F', '8F', '9F', '10F']
    
    for floor in floors:
        try:
            visualize_floor(floor, data_path)
        except Exception as e:
            print(f"处理 {floor} 时出错: {e}")


def generate_zone_summary(data_path: str):
    """生成各区域统计摘要"""
    nodes = load_nodes(data_path)
    
    # 按区域统计
    zone_stats = {}
    for node_id, node in nodes.items():
        zone = node.get('zone', 'Unknown')
        node_type = node.get('type', 'room')
        floor = node.get('floor', 'Unknown')
        
        if zone not in zone_stats:
            zone_stats[zone] = {
                'rooms': 0,
                'stairs': 0,
                'elevators': 0,
                'floors': set()
            }
        
        if node_type == 'room':
            zone_stats[zone]['rooms'] += 1
        elif node_type == 'stairs':
            zone_stats[zone]['stairs'] += 1
        elif node_type == 'elevator':
            zone_stats[zone]['elevators'] += 1
        
        zone_stats[zone]['floors'].add(floor)
    
    print("\n" + "="*60)
    print("文萃楼各区域房间统计")
    print("="*60)
    print(f"{'区域':<6} {'房间数':<8} {'楼梯数':<8} {'电梯数':<8} {'楼层数':<8}")
    print("-"*60)
    
    total_rooms = 0
    total_stairs = 0
    total_elevators = 0
    
    for zone in sorted(zone_stats.keys()):
        stats = zone_stats[zone]
        total_rooms += stats['rooms']
        total_stairs += stats['stairs']
        total_elevators += stats['elevators']
        
        print(f"{zone:<6} {stats['rooms']:<8} {stats['stairs']:<8} {stats['elevators']:<8} {len(stats['floors']):<8}")
    
    print("-"*60)
    print(f"{'总计':<6} {total_rooms:<8} {total_stairs:<8} {total_elevators:<8} {'10':<8}")
    print("="*60)


def main():
    parser = argparse.ArgumentParser(description='房间节点可视化验证工具')
    parser.add_argument('floor', nargs='?', help='楼层标识 (如 1F, 2F)，不指定则可视化所有楼层')
    parser.add_argument('--data', default='data/wencui_rooms_generated.json', 
                       help='节点数据文件路径')
    parser.add_argument('--summary', action='store_true', help='显示统计摘要')
    args = parser.parse_args()
    
    # 转换为绝对路径
    base_dir = os.path.dirname(os.path.dirname(__file__))
    data_path = os.path.join(base_dir, args.data)
    
    if not os.path.exists(data_path):
        print(f"错误: 找不到数据文件 {data_path}")
        sys.exit(1)
    
    if args.summary:
        generate_zone_summary(data_path)
        return
    
    if args.floor:
        visualize_floor(args.floor, data_path)
    else:
        visualize_all_floors(data_path)
        generate_zone_summary(data_path)


if __name__ == '__main__':
    main()

"""
将 C_zone_1F_meter.json 数据反向可视化到图纸

使用方法:
  python tools/visualize_c_zone_from_json.py
"""

import cv2
import json
import os
import numpy as np


def load_coordinate_config():
    """加载坐标系配置"""
    config_path = os.path.join(
        os.path.dirname(__file__), '..', 'data', 'coordinate_system_config.json'
    )
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def meter_to_pixel(mx, my, origin_px, scale_factor):
    """米制坐标转像素坐标"""
    px = int(origin_px[0] + mx / scale_factor)
    py = int(origin_px[1] - my / scale_factor)
    return (px, py)


def visualize_c_zone_from_json():
    """从JSON数据生成可视化图"""
    
    # 加载坐标系配置
    config = load_coordinate_config()
    origin_px = tuple(config['origin_px'])
    scale_factor = config['scale_factor']
    
    print(f"坐标系原点: {origin_px}")
    print(f"比例尺: {scale_factor:.4f} 米/像素")
    
    # 加载C区数据
    json_path = os.path.join(
        os.path.dirname(__file__), '..', 'data', 'zones', 'C_zone_1F_meter.json'
    )
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"\n加载数据: {json_path}")
    print(f"房间数: {len(data['rooms'])}")
    print(f"门点数: {len(data['door_nodes'])}")
    print(f"路点数: {len(data['waypoints'])}")
    
    # 加载1F楼层图
    floorplan_path = os.path.join(
        os.path.dirname(__file__), '..', 'data', 'floorplans', '1F_official.jpg'
    )
    img = cv2.imread(floorplan_path)
    
    # 创建可视化图像
    vis_img = img.copy()
    
    # 绘制坐标系原点（圆形教室中心）
    cv2.circle(vis_img, origin_px, 15, (0, 0, 255), -1)
    cv2.circle(vis_img, origin_px, 15, (255, 255, 255), 3)
    cv2.putText(vis_img, "O(0,0)", (origin_px[0] + 20, origin_px[1] - 20),
               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    
    # 绘制坐标轴
    cv2.arrowedLine(vis_img, origin_px, (origin_px[0] + 200, origin_px[1]),
                   (0, 0, 255), 3, tipLength=0.1)
    cv2.putText(vis_img, "X+", (origin_px[0] + 210, origin_px[1]),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    
    cv2.arrowedLine(vis_img, origin_px, (origin_px[0], origin_px[1] - 200),
                   (0, 255, 0), 3, tipLength=0.1)
    cv2.putText(vis_img, "Y+", (origin_px[0] - 30, origin_px[1] - 210),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    
    # 绘制房间中心（蓝色圆点 + 房间号）
    print("\n绘制房间...")
    for room in data['rooms']:
        mx, my, mz = room['center']['x'], room['center']['y'], room['center']['z']
        px, py = meter_to_pixel(mx, my, origin_px, scale_factor)
        
        # 绘制房间中心点
        cv2.circle(vis_img, (px, py), 12, (255, 0, 0), -1)  # 蓝色实心圆
        cv2.circle(vis_img, (px, py), 12, (255, 255, 255), 2)  # 白色边框
        
        # 绘制房间号
        label = room['id']
        cv2.putText(vis_img, label, (px + 15, py - 15),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
        
        # 显示坐标信息
        coord_text = f"({mx:.1f}, {my:.1f})"
        cv2.putText(vis_img, coord_text, (px + 15, py + 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)
    
    # 绘制门点（绿色圆点）
    print("绘制门点...")
    for door in data['door_nodes']:
        mx, my, mz = door['location']['x'], door['location']['y'], door['location']['z']
        px, py = meter_to_pixel(mx, my, origin_px, scale_factor)
        
        cv2.circle(vis_img, (px, py), 8, (0, 255, 0), -1)  # 绿色实心圆
        cv2.circle(vis_img, (px, py), 8, (255, 255, 255), 1)  # 白色边框
    
    # 绘制走廊路点（黄色圆点）
    print("绘制走廊路点...")
    for wp in data['waypoints']:
        mx, my, mz = wp['location']['x'], wp['location']['y'], wp['location']['z']
        px, py = meter_to_pixel(mx, my, origin_px, scale_factor)
        
        cv2.circle(vis_img, (px, py), 10, (0, 255, 255), -1)  # 黄色实心圆
        cv2.circle(vis_img, (px, py), 10, (255, 255, 255), 1)  # 白色边框
        
        # 显示路点ID
        cv2.putText(vis_img, wp['id'], (px + 12, py - 12),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 150, 150), 1)
    
    # 绘制连接线（边）
    print("绘制路径连接...")
    for edge in data['edges']:
        from_id = edge['from']
        to_id = edge['to']
        
        # 查找节点坐标
        from_node = None
        to_node = None
        
        for node in data['door_nodes'] + data['waypoints']:
            if node['id'] == from_id:
                from_node = node
            if node['id'] == to_id:
                to_node = node
        
        if from_node and to_node:
            from_mx = from_node['location']['x']
            from_my = from_node['location']['y']
            to_mx = to_node['location']['x']
            to_my = to_node['location']['y']
            
            from_px, from_py = meter_to_pixel(from_mx, from_my, origin_px, scale_factor)
            to_px, to_py = meter_to_pixel(to_mx, to_my, origin_px, scale_factor)
            
            # 根据边类型选择颜色
            if edge['type'] == 'door_to_corridor':
                color = (0, 200, 0)  # 深绿色：门到走廊
            else:
                color = (255, 200, 0)  # 橙色：走廊连接
            
            cv2.line(vis_img, (from_px, from_py), (to_px, to_py), color, 2)
    
    # 添加图例
    legend_y = 50
    cv2.putText(vis_img, "Legend:", (20, legend_y),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    cv2.circle(vis_img, (40, legend_y + 30), 8, (255, 0, 0), -1)
    cv2.putText(vis_img, "Room Center", (55, legend_y + 35),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
    cv2.circle(vis_img, (40, legend_y + 55), 6, (0, 255, 0), -1)
    cv2.putText(vis_img, "Door", (55, legend_y + 60),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
    cv2.circle(vis_img, (40, legend_y + 80), 7, (0, 255, 255), -1)
    cv2.putText(vis_img, "Waypoint", (55, legend_y + 85),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
    
    # 添加信息框
    info_text = [
        f"Zone: C",
        f"Floor: 1F",
        f"Rooms: {len(data['rooms'])}",
        f"Doors: {len(data['door_nodes'])}",
        f"Waypoints: {len(data['waypoints'])}",
        f"Scale: 1px={scale_factor:.4f}m",
        f"Origin: ({origin_px[0]}, {origin_px[1]})"
    ]
    
    # 绘制信息背景框
    box_x = img.shape[1] - 300
    box_y = 20
    cv2.rectangle(vis_img, (box_x, box_y), (box_x + 280, box_y + 160),
                 (255, 255, 255), -1)
    cv2.rectangle(vis_img, (box_x, box_y), (box_x + 280, box_y + 160),
                 (0, 0, 0), 2)
    
    for i, text in enumerate(info_text):
        cv2.putText(vis_img, text, (box_x + 10, box_y + 25 + i * 22),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
    
    # 保存可视化图
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'visualizations')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'C_zone_1F_reverse_visualization.jpg')
    
    cv2.imwrite(output_path, vis_img)
    print(f"\n可视化图已保存: {output_path}")
    
    return output_path


def print_data_summary():
    """打印数据摘要"""
    json_path = os.path.join(
        os.path.dirname(__file__), '..', 'data', 'zones', 'C_zone_1F_meter.json'
    )
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("\n" + "=" * 60)
    print("C区1F数据摘要")
    print("=" * 60)
    
    print("\n【房间列表】")
    for room in data['rooms']:
        c = room['center']
        px = room['pixel_coords']
        print(f"  {room['id']}: 米制({c['x']:.2f}, {c['y']:.2f}) | 像素({px['x']}, {px['y']})")
    
    print("\n【门点列表】")
    for door in data['door_nodes']:
        l = door['location']
        print(f"  {door['id']}: ({l['x']:.2f}, {l['y']:.2f})")
    
    print("\n【路点列表】")
    for wp in data['waypoints']:
        l = wp['location']
        print(f"  {wp['id']}: ({l['x']:.2f}, {l['y']:.2f})")
    
    print("\n【连接关系】")
    for edge in data['edges']:
        print(f"  {edge['from']} -> {edge['to']} ({edge['type']}, {edge['distance']:.2f}m)")
    
    print("=" * 60)


def main():
    """主函数"""
    print("=" * 60)
    print("C区1F数据反向可视化工具")
    print("=" * 60)
    
    # 打印数据摘要
    print_data_summary()
    
    # 生成可视化图
    print("\n生成可视化图...")
    output_path = visualize_c_zone_from_json()
    
    print("\n" + "=" * 60)
    print("完成!")
    print(f"请查看: {output_path}")
    print("=" * 60)


if __name__ == '__main__':
    main()
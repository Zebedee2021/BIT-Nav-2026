"""
1F C区精确标注工具

基于米制坐标系，对1F C区房间进行精确标注
生成包含房间中心、门点、走廊路点的完整数据

使用方法:
  python tools/annotate_c_zone_1f.py
"""

import cv2
import json
import os
import numpy as np
from PIL import Image


class MeterCoordinateConverter:
    """米制坐标转换器"""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(__file__), '..', 'data', 'coordinate_system_config.json'
            )
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        self.origin_px = tuple(config['origin_px'])
        self.scale_factor = config['scale_factor']
    
    def pixel_to_meter(self, px: int, py: int, floor: int = 1) -> dict:
        """像素坐标转米制坐标"""
        rel_x = px - self.origin_px[0]
        rel_y = self.origin_px[1] - py
        
        return {
            "x": round(rel_x * self.scale_factor, 2),
            "y": round(rel_y * self.scale_factor, 2),
            "z": floor
        }
    
    def meter_to_pixel(self, mx: float, my: float, floor: int = 1) -> tuple:
        """米制坐标转像素坐标"""
        px = int(self.origin_px[0] + mx / self.scale_factor)
        py = int(self.origin_px[1] - my / self.scale_factor)
        return (px, py)


class CZone1FAnnotator:
    """1F C区标注器"""
    
    def __init__(self):
        self.converter = MeterCoordinateConverter()
        
        # 加载1F楼层图
        self.floorplan_path = os.path.join(
            os.path.dirname(__file__), '..', 'data', 'floorplans', '1F_official.jpg'
        )
        self.img = cv2.imread(self.floorplan_path)
        self.img_height, self.img_width = self.img.shape[:2]
        
        # 数据结构
        self.rooms = []  # 房间数据
        self.door_nodes = []  # 门点
        self.waypoints = []  # 走廊路点
        
    def annotate_c_zone(self):
        """
        标注1F C区房间
        
        根据1F楼层图观察，C区位于右上角，包含以下房间：
        - C-101 到 C-109 (右侧纵向排列)
        """
        
        print("=" * 60)
        print("1F C区房间标注")
        print("=" * 60)
        
        # 根据楼层图观察，C区房间像素坐标（修正后）
        # C区在右侧偏上位置，浅绿色区域，房间从上到下排列
        # 修正：房间应该在C区内部，而不是走廊上
        c_zone_rooms_px = [
            # 房间ID, 中心像素x, 中心像素y, 门点位置(相对于房间的方向)
            ("C-101", 2550, 350, "left"),   # 最上方
            ("C-102", 2550, 450, "left"),
            ("C-103", 2550, 550, "left"),
            ("C-104", 2550, 650, "left"),
            ("C-105", 2550, 750, "left"),
            ("C-106", 2550, 850, "left"),
            ("C-107", 2550, 950, "left"),
            ("C-108", 2550, 1050, "left"),
            ("C-109", 2550, 1150, "left"),  # 最下方
        ]
        
        print(f"标注 {len(c_zone_rooms_px)} 个C区房间...")
        
        for room_id, px, py, door_dir in c_zone_rooms_px:
            # 转换为米制坐标
            meter_coords = self.converter.pixel_to_meter(px, py, floor=1)
            
            # 房间数据
            room = {
                "id": room_id,
                "type": "classroom",
                "zone": "C",
                "floor": 1,
                "center": meter_coords,
                "pixel_coords": {"x": px, "y": py}
            }
            self.rooms.append(room)
            
            # 计算门点位置（在房间左侧，靠近走廊）
            door_offset_px = 40  # 门点距离房间中心的偏移
            if door_dir == "left":
                door_px = px - door_offset_px
                door_py = py
            else:
                door_px = px
                door_py = py
            
            door_meter = self.converter.pixel_to_meter(door_px, door_py, floor=1)
            door_node = {
                "id": f"door_{room_id}",
                "type": "door",
                "room_id": room_id,
                "location": door_meter,
                "pixel_coords": {"x": door_px, "y": door_py}
            }
            self.door_nodes.append(door_node)
            
            print(f"  {room_id}: 像素({px}, {py}) -> 米制({meter_coords['x']}, {meter_coords['y']}, {meter_coords['z']})")
        
        # 添加走廊路点（C区走廊中心线）
        print("\n标注走廊路点...")
        corridor_waypoints_px = [
            # 纵向走廊路点（C区走廊在房间左侧）
            ("wp_c_01", 2450, 350),
            ("wp_c_02", 2450, 550),
            ("wp_c_03", 2450, 750),
            ("wp_c_04", 2450, 950),
            ("wp_c_05", 2450, 1150),
            # 横向连接路点
            ("wp_c_hall_01", 2300, 750),  # 连接到主走廊
        ]
        
        for wp_id, px, py in corridor_waypoints_px:
            meter_coords = self.converter.pixel_to_meter(px, py, floor=1)
            waypoint = {
                "id": wp_id,
                "type": "waypoint",
                "location": meter_coords,
                "pixel_coords": {"x": px, "y": py}
            }
            self.waypoints.append(waypoint)
        
        print(f"  添加了 {len(corridor_waypoints_px)} 个走廊路点")
    
    def create_navigation_graph(self):
        """创建导航图（节点连接关系）"""
        edges = []
        
        # 连接每个门点到最近的走廊路点
        for door in self.door_nodes:
            door_px = (door['pixel_coords']['x'], door['pixel_coords']['y'])
            
            # 找到最近的走廊路点
            min_dist = float('inf')
            nearest_wp = None
            
            for wp in self.waypoints:
                if wp['type'] == 'waypoint':
                    wp_px = (wp['pixel_coords']['x'], wp['pixel_coords']['y'])
                    dist = np.sqrt((door_px[0] - wp_px[0])**2 + (door_px[1] - wp_px[1])**2)
                    if dist < min_dist:
                        min_dist = dist
                        nearest_wp = wp
            
            if nearest_wp:
                edges.append({
                    "from": door['id'],
                    "to": nearest_wp['id'],
                    "type": "door_to_corridor",
                    "distance": round(min_dist * self.converter.scale_factor, 2)
                })
        
        # 连接走廊路点（纵向）
        wp_list = [wp for wp in self.waypoints if wp['type'] == 'waypoint']
        for i in range(len(wp_list) - 1):
            wp1 = wp_list[i]
            wp2 = wp_list[i + 1]
            
            wp1_px = (wp1['pixel_coords']['x'], wp1['pixel_coords']['y'])
            wp2_px = (wp2['pixel_coords']['x'], wp2['pixel_coords']['y'])
            dist = np.sqrt((wp1_px[0] - wp2_px[0])**2 + (wp1_px[1] - wp2_px[1])**2)
            
            edges.append({
                "from": wp1['id'],
                "to": wp2['id'],
                "type": "corridor",
                "distance": round(dist * self.converter.scale_factor, 2)
            })
        
        return edges
    
    def visualize(self, output_path: str = None):
        """生成可视化图"""
        vis_img = self.img.copy()
        
        # 绘制房间中心（蓝色）
        for room in self.rooms:
            px = room['pixel_coords']['x']
            py = room['pixel_coords']['y']
            cv2.circle(vis_img, (px, py), 8, (255, 0, 0), -1)
            cv2.putText(vis_img, room['id'], (px + 10, py - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
        
        # 绘制门点（绿色）
        for door in self.door_nodes:
            px = door['pixel_coords']['x']
            py = door['pixel_coords']['y']
            cv2.circle(vis_img, (px, py), 5, (0, 255, 0), -1)
        
        # 绘制走廊路点（黄色）
        for wp in self.waypoints:
            px = wp['pixel_coords']['x']
            py = wp['pixel_coords']['y']
            cv2.circle(vis_img, (px, py), 6, (0, 255, 255), -1)
            cv2.putText(vis_img, wp['id'], (px + 8, py - 8),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
        
        # 绘制连接线
        edges = self.create_navigation_graph()
        for edge in edges:
            # 找到对应的节点
            from_node = None
            to_node = None
            
            for node in self.door_nodes + self.waypoints:
                if node['id'] == edge['from']:
                    from_node = node
                if node['id'] == edge['to']:
                    to_node = node
            
            if from_node and to_node:
                p1 = (from_node['pixel_coords']['x'], from_node['pixel_coords']['y'])
                p2 = (to_node['pixel_coords']['x'], to_node['pixel_coords']['y'])
                cv2.line(vis_img, p1, p2, (0, 200, 0), 2)
        
        # 保存
        if output_path is None:
            output_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'visualizations')
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, '1F_C_zone_annotated.jpg')
        
        cv2.imwrite(output_path, vis_img)
        print(f"\n可视化图已保存: {output_path}")
        return output_path
    
    def save_data(self, output_path: str = None):
        """保存标注数据"""
        data = {
            "zone": "C",
            "floor": 1,
            "coordinate_system": {
                "origin": "圆形教室中心",
                "unit": "meters",
                "scale_factor": self.converter.scale_factor
            },
            "rooms": self.rooms,
            "door_nodes": self.door_nodes,
            "waypoints": self.waypoints,
            "edges": self.create_navigation_graph()
        }
        
        if output_path is None:
            output_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'zones')
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, 'C_zone_1F_meter.json')
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"数据已保存: {output_path}")
        return output_path


def main():
    """主函数"""
    annotator = CZone1FAnnotator()
    
    # 执行标注
    annotator.annotate_c_zone()
    
    # 生成可视化
    annotator.visualize()
    
    # 保存数据
    annotator.save_data()
    
    print("\n" + "=" * 60)
    print("1F C区标注完成!")
    print(f"  房间数: {len(annotator.rooms)}")
    print(f"  门点数: {len(annotator.door_nodes)}")
    print(f"  路点数: {len(annotator.waypoints)}")
    print("=" * 60)


if __name__ == '__main__':
    main()
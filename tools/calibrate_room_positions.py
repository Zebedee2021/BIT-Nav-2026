"""
房间坐标精确校准工具

基于楼层图实际像素测量，精确校准房间坐标位置

使用方法：
  python tools/calibrate_room_positions.py [区域] [楼层]
  
示例：
  python tools/calibrate_room_positions.py C 1F
  python tools/calibrate_room_positions.py all 1F
"""

import json
import os
import sys
import cv2
import numpy as np
from PIL import Image


class RoomPositionCalibrator:
    """房间坐标校准器"""
    
    def __init__(self, zone: str, floor: str):
        self.zone = zone
        self.floor = floor
        self.floor_num = floor.replace('F', '')
        
        # 加载楼层图
        self.floorplan_path = os.path.join(
            os.path.dirname(__file__), '..', 'wencui', f'{self.floor_num}.jpg'
        )
        
        if not os.path.exists(self.floorplan_path):
            raise FileNotFoundError(f"找不到楼层图: {self.floorplan_path}")
        
        self.img = cv2.imread(self.floorplan_path)
        self.img_height, self.img_width = self.img.shape[:2]
        
        # 加载现有节点数据
        self.data_path = os.path.join(
            os.path.dirname(__file__), '..', 'data', 'wencui_rooms_generated.json'
        )
        
        with open(self.data_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        
        self.nodes = self.data['nodes']
        
        # 筛选当前区域和楼层的房间
        self.zone_rooms = self._get_zone_rooms()
        
        print(f"楼层图尺寸: {self.img_width} x {self.img_height}")
        print(f"{zone}区 {floor} 房间数: {len(self.zone_rooms)}")
    
    def _get_zone_rooms(self) -> dict:
        """获取当前区域和楼层的房间"""
        rooms = {}
        for node_id, node in self.nodes.items():
            if (node.get('zone') == self.zone and 
                node.get('floor') == self.floor and
                node.get('type') == 'room'):
                rooms[node_id] = node
        return rooms
    
    def interactive_calibration(self):
        """
        交互式坐标校准
        点击楼层图上的位置来更新房间坐标
        """
        print(f"\n=== {self.zone}区 {self.floor} 坐标校准 ===")
        print("操作说明:")
        print("  左键点击: 将当前房间移动到点击位置")
        print("  右键点击: 跳过当前房间")
        print("  按 S: 保存当前校准结果")
        print("  按 Q: 退出校准")
        print("  按 N: 下一个房间")
        print("  按 P: 上一个房间")
        print()
        
        # 准备房间列表
        room_list = sorted(self.zone_rooms.keys())
        current_idx = 0
        
        # 当前待校准的房间
        current_room = None
        
        def draw_overlay():
            """绘制叠加层"""
            overlay = self.img.copy()
            
            # 绘制所有已校准的房间（绿色）
            for i, room_id in enumerate(room_list):
                if i < current_idx:
                    room = self.zone_rooms[room_id]
                    x, y = room['x'], room['y']
                    cv2.circle(overlay, (x, y), 8, (0, 255, 0), -1)
                    cv2.circle(overlay, (x, y), 8, (255, 255, 255), 2)
                    cv2.putText(overlay, room_id, (x+10, y), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            
            # 绘制当前房间（红色高亮）
            if current_room and current_idx < len(room_list):
                room_id = room_list[current_idx]
                room = self.zone_rooms[room_id]
                x, y = room['x'], room['y']
                cv2.circle(overlay, (x, y), 12, (0, 0, 255), -1)
                cv2.circle(overlay, (x, y), 12, (255, 255, 255), 3)
                cv2.putText(overlay, f"CURRENT: {room_id}", (x+15, y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # 绘制状态信息
            status = f"Room {current_idx+1}/{len(room_list)}: {room_list[current_idx] if current_idx < len(room_list) else 'Done'}"
            cv2.putText(overlay, status, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            
            return overlay
        
        def mouse_callback(event, x, y, flags, param):
            nonlocal current_idx, current_room
            
            if event == cv2.EVENT_LBUTTONDOWN:
                # 左键点击 - 更新当前房间坐标
                if current_idx < len(room_list):
                    room_id = room_list[current_idx]
                    self.zone_rooms[room_id]['x'] = x
                    self.zone_rooms[room_id]['y'] = y
                    print(f"  更新 {room_id}: ({x}, {y})")
                    current_idx += 1
                    
            elif event == cv2.EVENT_RBUTTONDOWN:
                # 右键点击 - 跳过当前房间
                if current_idx < len(room_list):
                    room_id = room_list[current_idx]
                    print(f"  跳过 {room_id}")
                    current_idx += 1
        
        # 创建窗口
        window_name = f"Room Calibration - {self.zone} {self.floor}"
        cv2.namedWindow(window_name)
        cv2.setMouseCallback(window_name, mouse_callback)
        
        while True:
            overlay = draw_overlay()
            cv2.imshow(window_name, overlay)
            
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q'):
                # 退出
                break
            elif key == ord('s'):
                # 保存
                self.save_calibration()
                print("  已保存校准结果")
            elif key == ord('n'):
                # 下一个
                if current_idx < len(room_list) - 1:
                    current_idx += 1
                    print(f"  移动到: {room_list[current_idx]}")
            elif key == ord('p'):
                # 上一个
                if current_idx > 0:
                    current_idx -= 1
                    print(f"  移动到: {room_list[current_idx]}")
        
        cv2.destroyAllWindows()
        
        # 询问是否保存
        save = input("\n是否保存校准结果? (y/n): ").strip().lower()
        if save == 'y':
            self.save_calibration()
    
    def save_calibration(self):
        """保存校准结果"""
        # 更新主数据
        for room_id, room in self.zone_rooms.items():
            self.nodes[room_id] = room
        
        # 保存到文件
        self.data['nodes'] = self.nodes
        with open(self.data_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        
        print(f"校准结果已保存到: {self.data_path}")
    
    def auto_detect_from_template(self):
        """
        基于模板匹配自动检测房间位置
        使用房间编号的文字特征进行匹配
        """
        print(f"\n正在对 {self.zone}区 {self.floor} 进行自动检测...")
        
        # 转换为灰度图
        gray = cv2.cvtColor(self.img, cv2.COLOR_BGR2GRAY)
        
        # 使用阈值处理提取文字区域
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # 查找轮廓
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        detected_positions = []
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            # 过滤大小（房间编号文字的大小范围）
            if 15 < w < 80 and 10 < h < 50:
                center_x = x + w // 2
                center_y = y + h // 2
                detected_positions.append((center_x, center_y, w, h))
        
        print(f"  检测到 {len(detected_positions)} 个可能的文字区域")
        
        # 可视化检测结果
        vis_img = self.img.copy()
        for x, y, w, h in detected_positions:
            cv2.rectangle(vis_img, (x-w//2, y-h//2), (x+w//2, y+h//2), (0, 255, 0), 2)
            cv2.circle(vis_img, (x, y), 3, (0, 0, 255), -1)
        
        # 保存可视化结果
        output_path = os.path.join(
            os.path.dirname(__file__), '..', 'data', 'visualizations', 
            f'{self.zone}_{self.floor}_auto_detect.jpg'
        )
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        cv2.imwrite(output_path, vis_img)
        print(f"  检测结果已保存到: {output_path}")
        
        return detected_positions


def export_zone_data(zone: str, output_dir: str = None):
    """
    导出指定区域的数据为独立文件
    
    Args:
        zone: 区域标识（如 C, D, E）
        output_dir: 输出目录
    """
    data_path = os.path.join(
        os.path.dirname(__file__), '..', 'data', 'wencui_rooms_generated.json'
    )
    
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 筛选指定区域的节点
    zone_nodes = {}
    for node_id, node in data['nodes'].items():
        if node.get('zone') == zone:
            zone_nodes[node_id] = node
    
    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(__file__), '..', 'data', 'zones'
        )
    
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, f'zone_{zone}_rooms.json')
    
    zone_data = {
        "zone": zone,
        "building": data['building'],
        "node_count": len(zone_nodes),
        "nodes": zone_nodes
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(zone_data, f, ensure_ascii=False, indent=2)
    
    print(f"{zone}区数据已导出到: {output_path}")
    print(f"  共 {len(zone_nodes)} 个节点")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='房间坐标校准工具')
    parser.add_argument('zone', help='区域标识 (如 C, D, E, all)')
    parser.add_argument('floor', nargs='?', default='1F', help='楼层 (如 1F, 2F)')
    parser.add_argument('--auto', action='store_true', help='自动检测模式')
    parser.add_argument('--export', action='store_true', help='导出区域数据')
    args = parser.parse_args()
    
    if args.export:
        # 导出模式
        if args.zone == 'all':
            for zone in ['C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M']:
                export_zone_data(zone)
        else:
            export_zone_data(args.zone)
        return
    
    if args.zone == 'all':
        # 处理所有区域
        zones = ['C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M']
        for zone in zones:
            try:
                calibrator = RoomPositionCalibrator(zone, args.floor)
                if args.auto:
                    calibrator.auto_detect_from_template()
                else:
                    calibrator.interactive_calibration()
            except Exception as e:
                print(f"处理 {zone}区时出错: {e}")
    else:
        # 处理单个区域
        calibrator = RoomPositionCalibrator(args.zone, args.floor)
        
        if args.auto:
            calibrator.auto_detect_from_template()
        else:
            calibrator.interactive_calibration()


if __name__ == '__main__':
    main()

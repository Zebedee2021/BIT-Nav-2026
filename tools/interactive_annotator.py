"""
交互式楼层图标注工具

使用方法:
  python tools/interactive_annotator.py

操作说明:
  - 左键点击: 标注一个房间中心点
  - 右键点击: 标注一个门点
  - 按 'w': 标注一个走廊路点
  - 按 's': 保存当前标注到JSON
  - 按 'q': 退出
  - 按 'z': 撤销上一个标注
"""

import cv2
import json
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont


class InteractiveAnnotator:
    """交互式标注器 - 支持缩放"""
    
    def __init__(self, floorplan_path: str, zone: str = "C", floor: int = 1):
        self.floorplan_path = floorplan_path
        self.zone = zone
        self.floor = floor
        
        # 加载图片（保持原始分辨率）
        self.img_original = cv2.imread(floorplan_path)
        self.img_height, self.img_width = self.img_original.shape[:2]
        print(f"Image resolution: {self.img_width} x {self.img_height}")
        
        # 缩放参数
        self.scale = 0.5  # 初始缩放比例
        self.min_scale = 0.2
        self.max_scale = 2.0
        self.scale_step = 0.1
        
        # 视口偏移（用于平移）
        self.offset_x = 0
        self.offset_y = 0
        self.is_panning = False
        self.pan_start_x = 0
        self.pan_start_y = 0
        
        # 加载坐标系配置
        config_path = os.path.join(
            os.path.dirname(__file__), '..', 'data', 'coordinate_system_config.json'
        )
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        self.origin_px = tuple(config['origin_px'])
        self.scale_factor = config['scale_factor']
        
        # 标注数据
        self.rooms = []
        self.door_nodes = []
        self.waypoints = []
        self.current_room_num = 1  # 当前房间编号
        
        # 窗口名称
        self.window_name = f"Interactive Annotator - {zone} Zone {floor}F"
        
        # 创建窗口 - 使用正常窗口允许最大化
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        
        # 设置鼠标回调
        cv2.setMouseCallback(self.window_name, self.mouse_callback)
        
        # 信息显示（使用英文避免编码问题）
        self.info_text = [
            "=== Interactive Annotator ===",
            "Left Click: Mark Room Center",
            "Right Click: Mark Door",
            "Mouse Wheel: Zoom",
            "Middle Drag: Pan",
            "Press 'w': Add Waypoint",
            "Press 's': Save Data",
            "Press 'q': Quit",
            "Press 'z': Undo",
            "Press '+/-': Zoom In/Out",
            "Press 'r': Reset View",
            "============================="
        ]
        
        self.update_display()
    
    def pixel_to_meter(self, px: int, py: int) -> dict:
        """像素坐标转米制坐标"""
        rel_x = px - self.origin_px[0]
        rel_y = self.origin_px[1] - py
        return {
            "x": round(rel_x * self.scale_factor, 2),
            "y": round(rel_y * self.scale_factor, 2),
            "z": self.floor
        }
    
    def screen_to_original(self, screen_x, screen_y):
        """将屏幕坐标转换为原始图片坐标"""
        orig_x = int((screen_x - self.offset_x) / self.scale)
        orig_y = int((screen_y - self.offset_y) / self.scale)
        return orig_x, orig_y
    
    def original_to_screen(self, orig_x, orig_y):
        """将原始图片坐标转换为屏幕坐标"""
        screen_x = int(orig_x * self.scale + self.offset_x)
        screen_y = int(orig_y * self.scale + self.offset_y)
        return screen_x, screen_y
    
    def mouse_callback(self, event, x, y, flags, param):
        """鼠标回调函数"""
        if event == cv2.EVENT_LBUTTONDOWN:
            # 左键点击 - 标注房间中心（转换为原始坐标）
            orig_x, orig_y = self.screen_to_original(x, y)
            room_id = f"{self.zone}-{self.floor}{self.current_room_num:02d}"
            meter_coords = self.pixel_to_meter(orig_x, orig_y)
            
            room = {
                "id": room_id,
                "type": "classroom",
                "zone": self.zone,
                "floor": self.floor,
                "center": meter_coords,
                "pixel_coords": {"x": orig_x, "y": orig_y}
            }
            self.rooms.append(room)
            
            print(f"✓ Room marked: {room_id} pixel({orig_x}, {orig_y}) -> meter({meter_coords['x']:.2f}, {meter_coords['y']:.2f})")
            self.current_room_num += 1
            self.update_display()
            
        elif event == cv2.EVENT_RBUTTONDOWN:
            # 右键点击 - 标注门点
            orig_x, orig_y = self.screen_to_original(x, y)
            if self.rooms:
                room_id = self.rooms[-1]['id']
                door_id = f"door_{room_id}"
                meter_coords = self.pixel_to_meter(orig_x, orig_y)
                
                door = {
                    "id": door_id,
                    "type": "door",
                    "room_id": room_id,
                    "location": meter_coords,
                    "pixel_coords": {"x": orig_x, "y": orig_y}
                }
                self.door_nodes.append(door)
                
                print(f"✓ Door marked: {door_id} pixel({orig_x}, {orig_y})")
                self.update_display()
            else:
                print("⚠ Please mark room first, then door")
        
        elif event == cv2.EVENT_MOUSEWHEEL:
            # 滚轮缩放
            if flags > 0:
                self.scale = min(self.scale + self.scale_step, self.max_scale)
            else:
                self.scale = max(self.scale - self.scale_step, self.min_scale)
            print(f"Scale: {self.scale:.1f}x")
            self.update_display()
        
        elif event == cv2.EVENT_MBUTTONDOWN:
            # 中键按下 - 开始平移
            self.is_panning = True
            self.pan_start_x = x
            self.pan_start_y = y
        
        elif event == cv2.EVENT_MBUTTONUP:
            # 中键释放 - 结束平移
            self.is_panning = False
        
        elif event == cv2.EVENT_MOUSEMOVE and self.is_panning:
            # 中键拖动 - 平移
            dx = x - self.pan_start_x
            dy = y - self.pan_start_y
            self.offset_x += dx
            self.offset_y += dy
            self.pan_start_x = x
            self.pan_start_y = y
            self.update_display()
    
    def add_waypoint(self):
        """添加走廊路点（按'w'键）"""
        # 获取鼠标当前位置
        # 由于无法直接获取鼠标位置，我们在中心位置添加并让用户移动
        wp_id = f"wp_{self.zone.lower()}_{len(self.waypoints) + 1:02d}"
        
        # 使用最后一个标注位置或默认位置
        if self.rooms:
            last_px = self.rooms[-1]['pixel_coords']['x']
            last_py = self.rooms[-1]['pixel_coords']['y']
        else:
            last_px = self.img.shape[1] // 2
            last_py = self.img.shape[0] // 2
        
        meter_coords = self.pixel_to_meter(last_px, last_py)
        
        waypoint = {
            "id": wp_id,
            "type": "waypoint",
            "location": meter_coords,
            "pixel_coords": {"x": last_px, "y": last_py}
        }
        self.waypoints.append(waypoint)
        
        print(f"✓ Waypoint added: {wp_id}")
        self.update_display()
    
    def undo(self):
        """撤销上一个标注"""
        if self.door_nodes:
            removed = self.door_nodes.pop()
            print(f"↩ Undo door: {removed['id']}")
        elif self.waypoints:
            removed = self.waypoints.pop()
            print(f"↩ Undo waypoint: {removed['id']}")
        elif self.rooms:
            removed = self.rooms.pop()
            print(f"↩ Undo room: {removed['id']}")
            self.current_room_num -= 1
        self.update_display()
    
    def update_display(self):
        """更新显示 - 支持缩放和平移"""
        # 创建显示画布（黑色背景）
        window_width = 1920
        window_height = 1080
        display = np.zeros((window_height, window_width, 3), dtype=np.uint8)
        
        # 缩放原图
        new_width = int(self.img_width * self.scale)
        new_height = int(self.img_height * self.scale)
        img_scaled = cv2.resize(self.img_original, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
        
        # 计算显示位置
        x1 = self.offset_x
        y1 = self.offset_y
        x2 = x1 + new_width
        y2 = y1 + new_height
        
        # 将缩放后的图片放置到画布上
        if x2 > 0 and y2 > 0 and x1 < window_width and y1 < window_height:
            # 计算有效区域
            src_x1 = max(0, -x1)
            src_y1 = max(0, -y1)
            src_x2 = min(new_width, window_width - x1)
            src_y2 = min(new_height, window_height - y1)
            
            dst_x1 = max(0, x1)
            dst_y1 = max(0, y1)
            dst_x2 = dst_x1 + (src_x2 - src_x1)
            dst_y2 = dst_y1 + (src_y2 - src_y1)
            
            if dst_x2 > dst_x1 and dst_y2 > dst_y1:
                display[dst_y1:dst_y2, dst_x1:dst_x2] = img_scaled[src_y1:src_y2, src_x1:src_x2]
        
        # 绘制坐标系原点（转换到屏幕坐标）
        origin_screen = self.original_to_screen(self.origin_px[0], self.origin_px[1])
        if 0 <= origin_screen[0] < window_width and 0 <= origin_screen[1] < window_height:
            cv2.circle(display, origin_screen, int(15 * self.scale), (0, 0, 255), -1)
            cv2.putText(display, "O(0,0)", (origin_screen[0] + 20, origin_screen[1] - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8 * self.scale, (0, 0, 255), 2)
        
        # 绘制房间中心（蓝色）- 转换到屏幕坐标
        for room in self.rooms:
            px = room['pixel_coords']['x']
            py = room['pixel_coords']['y']
            screen_pos = self.original_to_screen(px, py)
            if 0 <= screen_pos[0] < window_width and 0 <= screen_pos[1] < window_height:
                radius = int(12 * self.scale)
                cv2.circle(display, screen_pos, radius, (255, 0, 0), -1)
                cv2.circle(display, screen_pos, radius, (255, 255, 255), 2)
                cv2.putText(display, room['id'], (screen_pos[0] + radius + 5, screen_pos[1] - radius),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6 * self.scale, (255, 0, 0), 2)
        
        # 绘制门点（绿色）
        for door in self.door_nodes:
            px = door['pixel_coords']['x']
            py = door['pixel_coords']['y']
            screen_pos = self.original_to_screen(px, py)
            if 0 <= screen_pos[0] < window_width and 0 <= screen_pos[1] < window_height:
                radius = int(8 * self.scale)
                cv2.circle(display, screen_pos, radius, (0, 255, 0), -1)
                cv2.circle(display, screen_pos, radius, (255, 255, 255), 1)
        
        # 绘制路点（黄色）
        for wp in self.waypoints:
            px = wp['pixel_coords']['x']
            py = wp['pixel_coords']['y']
            screen_pos = self.original_to_screen(px, py)
            if 0 <= screen_pos[0] < window_width and 0 <= screen_pos[1] < window_height:
                radius = int(10 * self.scale)
                cv2.circle(display, screen_pos, radius, (0, 255, 255), -1)
                cv2.circle(display, screen_pos, radius, (255, 255, 255), 1)
                cv2.putText(display, wp['id'], (screen_pos[0] + radius + 5, screen_pos[1] - radius),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5 * self.scale, (0, 150, 150), 1)
        
        # 绘制连接线
        for door in self.door_nodes:
            for room in self.rooms:
                if room['id'] == door['room_id']:
                    r_screen = self.original_to_screen(room['pixel_coords']['x'], room['pixel_coords']['y'])
                    d_screen = self.original_to_screen(door['pixel_coords']['x'], door['pixel_coords']['y'])
                    if (0 <= r_screen[0] < window_width and 0 <= r_screen[1] < window_height and
                        0 <= d_screen[0] < window_width and 0 <= d_screen[1] < window_height):
                        cv2.line(display, r_screen, d_screen, (0, 200, 0), max(1, int(2 * self.scale)))
        
        # 添加信息面板（固定在左上角，不随图片缩放）
        panel_x = 20
        panel_y = 20
        panel_width = 380
        panel_height = 220 + len(self.rooms) * 20
        cv2.rectangle(display, (panel_x, panel_y), (panel_x + panel_width, panel_y + panel_height),
                     (50, 50, 50), -1)
        cv2.rectangle(display, (panel_x, panel_y), (panel_x + panel_width, panel_y + panel_height),
                     (200, 200, 200), 2)
        
        # 绘制说明文字
        for i, text in enumerate(self.info_text):
            cv2.putText(display, text, (panel_x + 10, panel_y + 25 + i * 18),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # 绘制统计信息
        stats_y = panel_y + 200
        cv2.putText(display, f"Rooms: {len(self.rooms)}", (panel_x + 10, stats_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 200, 255), 2)
        cv2.putText(display, f"Doors: {len(self.door_nodes)}", (panel_x + 10, stats_y + 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 255, 100), 2)
        cv2.putText(display, f"Waypoints: {len(self.waypoints)}", (panel_x + 10, stats_y + 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 100), 2)
        cv2.putText(display, f"Scale: {self.scale:.1f}x", (panel_x + 10, stats_y + 75),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        
        # 显示已标注的房间列表
        room_list_y = stats_y + 100
        cv2.putText(display, "Room List:", (panel_x + 10, room_list_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)
        for i, room in enumerate(self.rooms[-5:]):
            c = room['center']
            text = f"{room['id']}: ({c['x']:.1f}, {c['y']:.1f})"
            cv2.putText(display, text, (panel_x + 10, room_list_y + 18 + i * 18),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)
        
        cv2.imshow(self.window_name, display)
    
    def save_data(self):
        """保存标注数据"""
        data = {
            "zone": self.zone,
            "floor": self.floor,
            "coordinate_system": {
                "origin": "圆形教室中心",
                "unit": "meters",
                "scale_factor": self.scale_factor
            },
            "rooms": self.rooms,
            "door_nodes": self.door_nodes,
            "waypoints": self.waypoints
        }
        
        output_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'zones')
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f'{self.zone}_zone_{self.floor}F_manual.json')
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"\n✓ Data saved: {output_path}")
        print(f"  Rooms: {len(self.rooms)}")
        print(f"  Doors: {len(self.door_nodes)}")
        print(f"  Waypoints: {len(self.waypoints)}")
    
    def run(self):
        """运行交互式标注"""
        print("\n" + "=" * 60)
        print("Interactive Floorplan Annotator")
        print("=" * 60)
        print("Controls:")
        print("  Left Click: Mark room center")
        print("  Right Click: Mark door")
        print("  Mouse Wheel: Zoom in/out")
        print("  Middle Button Drag: Pan image")
        print("  Press 'w': Add waypoint")
        print("  Press 's': Save data")
        print("  Press 'q': Quit")
        print("  Press 'z': Undo")
        print("  Press '+/-': Zoom in/out")
        print("  Press 'r': Reset view")
        print("=" * 60 + "\n")
        
        while True:
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q'):
                # 退出前询问是否保存
                if self.rooms:
                    print("\nSave current annotations? (y/n): ", end="")
                    response = input().strip().lower()
                    if response == 'y':
                        self.save_data()
                break
            
            elif key == ord('s'):
                self.save_data()
            
            elif key == ord('z'):
                self.undo()
            
            elif key == ord('w'):
                self.add_waypoint()
            
            elif key == ord('+'):
                self.scale = min(self.scale + self.scale_step, self.max_scale)
                print(f"缩放比例: {self.scale:.1f}x")
                self.update_display()
            
            elif key == ord('-'):
                self.scale = max(self.scale - self.scale_step, self.min_scale)
                print(f"缩放比例: {self.scale:.1f}x")
                self.update_display()
            
            elif key == ord('r'):
                self.scale = 0.5
                self.offset_x = 0
                self.offset_y = 0
                print("View reset")
                self.update_display()
        
        cv2.destroyAllWindows()
        print("\nAnnotator closed")


def main():
    """主函数"""
    floorplan_path = os.path.join(
        os.path.dirname(__file__), '..', 'data', 'floorplans', '1F_official.jpg'
    )
    
    annotator = InteractiveAnnotator(floorplan_path, zone="C", floor=1)
    annotator.run()


if __name__ == '__main__':
    main()
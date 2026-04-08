"""
坐标系设置工具

基于 Gemini 思路，建立以圆形教室中心为原点的米制坐标系

使用方法：
  python tools/coordinate_system_setup.py
"""

import cv2
import json
import os
import numpy as np
from PIL import Image


class CoordinateSystemSetup:
    """坐标系设置工具"""
    
    def __init__(self, floorplan_path: str):
        self.floorplan_path = floorplan_path
        self.img = cv2.imread(floorplan_path)
        self.img_height, self.img_width = self.img.shape[:2]
        
        # 坐标系参数
        self.origin_px = None  # 原点像素坐标 (圆形教室中心)
        self.scale_factor = None  # 比例尺 (米/像素)
        
    def detect_circular_hall_center(self) -> tuple:
        """
        自动检测圆形教室中心
        基于颜色或形状识别
        """
        # 转换为灰度图
        gray = cv2.cvtColor(self.img, cv2.COLOR_BGR2GRAY)
        
        # 使用霍夫圆检测
        circles = cv2.HoughCircles(
            gray, 
            cv2.HOUGH_GRADIENT, 
            dp=1, 
            minDist=100,
            param1=50,
            param2=30,
            minRadius=100,
            maxRadius=300
        )
        
        if circles is not None:
            # 返回最大的圆（应该是圆形教室）
            circles = np.uint16(np.around(circles))
            largest_circle = max(circles[0], key=lambda c: c[2])
            center_x, center_y, radius = largest_circle
            return (int(center_x), int(center_y), int(radius))
        
        return None
    
    def manual_set_origin(self, x: int, y: int):
        """手动设置原点"""
        self.origin_px = (x, y)
        print(f"原点已设置为: ({x}, {y})")
    
    def calculate_scale_factor(self, pixel_distance: float, real_distance_meters: float):
        """
        计算比例尺
        
        Args:
            pixel_distance: 像素距离
            real_distance_meters: 实际物理距离（米）
        """
        self.scale_factor = real_distance_meters / pixel_distance
        print(f"比例尺计算完成: 1像素 = {self.scale_factor:.4f}米")
        print(f"                   1米 = {1/self.scale_factor:.2f}像素")
    
    def pixel_to_meter(self, px: int, py: int, floor: int = 1) -> dict:
        """
        像素坐标转换为米制坐标
        
        坐标系定义：
        - 原点：圆形教室中心
        - X轴：向右为正（东）
        - Y轴：向上为正（北）- 与像素坐标Y轴相反
        - Z轴：楼层高度
        """
        if self.origin_px is None or self.scale_factor is None:
            raise ValueError("请先设置原点和比例尺")
        
        # 相对像素坐标
        rel_x = px - self.origin_px[0]
        rel_y = self.origin_px[1] - py  # Y轴翻转
        
        # 转换为米
        meter_x = rel_x * self.scale_factor
        meter_y = rel_y * self.scale_factor
        
        return {
            "x": round(meter_x, 2),
            "y": round(meter_y, 2),
            "z": floor
        }
    
    def meter_to_pixel(self, mx: float, my: float, floor: int = 1) -> tuple:
        """米制坐标转换为像素坐标"""
        if self.origin_px is None or self.scale_factor is None:
            raise ValueError("请先设置原点和比例尺")
        
        px = int(self.origin_px[0] + mx / self.scale_factor)
        py = int(self.origin_px[1] - my / self.scale_factor)
        
        return (px, py)
    
    def visualize_coordinate_system(self, output_path: str = None):
        """可视化坐标系"""
        vis_img = self.img.copy()
        
        # 绘制原点
        if self.origin_px:
            cv2.circle(vis_img, self.origin_px, 15, (0, 0, 255), -1)
            cv2.circle(vis_img, self.origin_px, 15, (255, 255, 255), 3)
            cv2.putText(vis_img, "O(0,0)", (self.origin_px[0] + 20, self.origin_px[1] - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
        
        # 绘制坐标轴
        if self.origin_px:
            # X轴（红色，向右）
            cv2.arrowedLine(vis_img, 
                           (self.origin_px[0], self.origin_px[1]),
                           (self.origin_px[0] + 200, self.origin_px[1]),
                           (0, 0, 255), 3, tipLength=0.1)
            cv2.putText(vis_img, "X+", (self.origin_px[0] + 210, self.origin_px[1]),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            
            # Y轴（绿色，向上）
            cv2.arrowedLine(vis_img,
                           (self.origin_px[0], self.origin_px[1]),
                           (self.origin_px[0], self.origin_px[1] - 200),
                           (0, 255, 0), 3, tipLength=0.1)
            cv2.putText(vis_img, "Y+", (self.origin_px[0] - 30, self.origin_px[1] - 210),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        
        # 绘制栅格（每10米）
        if self.origin_px and self.scale_factor:
            grid_spacing_meters = 10  # 10米栅格
            grid_spacing_pixels = int(grid_spacing_meters / self.scale_factor)
            
            # 水平线
            for i in range(-10, 11):
                y = self.origin_px[1] + i * grid_spacing_pixels
                if 0 <= y < self.img_height:
                    cv2.line(vis_img, (0, y), (self.img_width, y), (200, 200, 200), 1)
                    if i != 0:
                        cv2.putText(vis_img, f"{i*10}m", (10, y - 5),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)
            
            # 垂直线
            for i in range(-10, 11):
                x = self.origin_px[0] + i * grid_spacing_pixels
                if 0 <= x < self.img_width:
                    cv2.line(vis_img, (x, 0), (x, self.img_height), (200, 200, 200), 1)
                    if i != 0:
                        cv2.putText(vis_img, f"{i*10}m", (x + 5, 20),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)
        
        # 添加信息文本
        info_text = f"Image: {self.img_width}x{self.img_height}"
        if self.scale_factor:
            info_text += f" | Scale: 1px={self.scale_factor:.4f}m"
        cv2.putText(vis_img, info_text, (10, self.img_height - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        
        # 保存或显示
        if output_path is None:
            output_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'visualizations')
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, 'coordinate_system.jpg')
        
        cv2.imwrite(output_path, vis_img)
        print(f"坐标系可视化图已保存: {output_path}")
        return output_path


def main():
    """主函数 - 示例用法"""
    # 使用1F官方楼层图
    floorplan_path = os.path.join(
        os.path.dirname(__file__), '..', 'data', 'floorplans', '1F_official.jpg'
    )
    
    if not os.path.exists(floorplan_path):
        print(f"楼层图不存在: {floorplan_path}")
        print("请确保 data/floorplans/1F_official.jpg 存在")
        return
    
    # 创建坐标系设置工具
    setup = CoordinateSystemSetup(floorplan_path)
    
    print("=" * 60)
    print("文萃楼坐标系设置工具")
    print("=" * 60)
    print(f"图片尺寸: {setup.img_width} x {setup.img_height}")
    print()
    
    # 根据1F楼层图观察，圆形教室（圆楼）位于底部中央
    # 通过观察图片，圆楼中心大约在 (1500, 1650)
    print("设置圆形教室中心为原点...")
    print("根据楼层图观察，圆楼位于底部中央")
    
    # 手动设置圆楼中心坐标（基于视觉观察）
    circular_hall_center = (1500, 1650)  # 底部中央圆楼中心
    setup.manual_set_origin(circular_hall_center[0], circular_hall_center[1])
    
    # 设置比例尺
    # 假设：文萃楼总宽度约200米，图片宽度约3000像素
    # 这个值需要根据实际情况调整
    print()
    print("设置比例尺...")
    print("参考: 文萃楼总宽度约200米，图片宽度约3000像素")
    print("      比例尺 ≈ 200/3000 = 0.067 米/像素")
    
    # 使用估算的比例尺
    setup.calculate_scale_factor(3000, 200)
    
    # 生成坐标系可视化图
    print()
    print("生成坐标系可视化图...")
    output_path = setup.visualize_coordinate_system()
    
    print()
    print("=" * 60)
    print("坐标系设置完成!")
    print(f"原点: {setup.origin_px}")
    print(f"比例尺: {setup.scale_factor:.4f} 米/像素")
    print("=" * 60)
    
    # 保存配置
    config = {
        "origin_px": setup.origin_px,
        "scale_factor": setup.scale_factor,
        "image_size": [setup.img_width, setup.img_height],
        "coordinate_system": {
            "origin": "圆形教室中心",
            "x_axis": "向右为正(东)",
            "y_axis": "向上为正(北)",
            "z_axis": "楼层高度"
        }
    }
    
    config_path = os.path.join(
        os.path.dirname(__file__), '..', 'data', 'coordinate_system_config.json'
    )
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    print(f"配置已保存: {config_path}")


if __name__ == '__main__':
    main()
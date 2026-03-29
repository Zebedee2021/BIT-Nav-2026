"""
楼层平面图可视化模块
支持加载官方楼层图并在其上叠加路径显示
"""

import json
import os
import requests
from io import BytesIO
from typing import Optional, List, Tuple, Dict
from PIL import Image, ImageDraw, ImageFont
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.image as mpimg
import numpy as np

# 查找中文字体并创建 FontProperties
_chinese_font_path = fm.findfont(fm.FontProperties(family='SimHei'))
if 'simhei' not in _chinese_font_path.lower() and 'yahei' not in _chinese_font_path.lower():
    # fallback: 直接用系统路径
    _chinese_font_path = r'C:\Windows\Fonts\simhei.ttf'
CHINESE_FONT = fm.FontProperties(fname=_chinese_font_path)


class FloorplanVisualizer:
    """楼层平面图可视化器"""
    
    def __init__(self, floorplan_urls_path: str):
        """
        初始化可视化器
        
        Args:
            floorplan_urls_path: floorplan_urls.json 文件路径
        """
        with open(floorplan_urls_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.floorplans = data.get("floorplans", {})
        self.coordinate_mapping = data.get("coordinate_mapping", {})
        self.cache = {}  # 图片缓存
    
    def get_floorplan_url(self, floor: str) -> Optional[str]:
        """获取楼层平面图的URL"""
        floor_data = self.floorplans.get(floor)
        if floor_data:
            return floor_data.get("url")
        return None
    
    def get_floorplan_info(self, floor: str) -> Optional[dict]:
        """获取楼层平面图信息"""
        return self.floorplans.get(floor)
    
    def load_floorplan(self, floor: str) -> Optional[Image.Image]:
        """
        加载楼层平面图
        
        Args:
            floor: 楼层标识 (如 "1F", "4F")
        
        Returns:
            PIL Image对象
        """
        # 检查缓存
        if floor in self.cache:
            return self.cache[floor]
        
        # 首先尝试加载本地图片
        local_path = self._get_local_floorplan_path(floor)
        if local_path and os.path.exists(local_path):
            try:
                img = Image.open(local_path)
                self.cache[floor] = img
                return img
            except Exception as e:
                print(f"加载本地楼层图失败: {e}")
        
        # 如果本地没有，尝试从URL加载
        url = self.get_floorplan_url(floor)
        if not url:
            return None
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            img = Image.open(BytesIO(response.content))
            self.cache[floor] = img
            return img
        except Exception as e:
            print(f"加载楼层图失败: {e}")
            return None
    
    def _get_local_floorplan_path(self, floor: str) -> Optional[str]:
        """获取本地楼层图路径"""
        # 假设本地图片存放在 data/floorplans/ 目录下
        base_dir = os.path.dirname(os.path.dirname(__file__))
        
        # 优先使用官方下载的图片
        official_path = os.path.join(base_dir, "data", "floorplans", f"{floor}_official.jpg")
        if os.path.exists(official_path):
            return official_path
        
        # 其次使用生成的示例图
        possible_paths = [
            os.path.join(base_dir, "data", "floorplans", f"{floor}.jpg"),
            os.path.join(base_dir, "data", "floorplans", f"{floor}.png"),
            os.path.join(base_dir, "data", "floorplans", f"floor_{floor}.jpg"),
            os.path.join(base_dir, "data", "floorplans", f"floor_{floor}.png"),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        return None
    
    def draw_path_on_floorplan(
        self,
        floor: str,
        path_nodes: List[Tuple[float, float]],
        node_labels: Optional[List[str]] = None,
        output_size: Tuple[int, int] = (800, 600)
    ) -> Optional[Image.Image]:
        """
        在楼层平面图上绘制路径
        
        Args:
            floor: 楼层标识
            path_nodes: 路径节点坐标列表 [(x1,y1), (x2,y2), ...]
            node_labels: 节点标签列表
            output_size: 输出图片尺寸
        
        Returns:
            带路径的Image对象
        """
        # 加载楼层图
        img = self.load_floorplan(floor)
        if not img:
            return None
        
        # 调整大小
        img = img.resize(output_size, Image.Resampling.LANCZOS)
        
        # 创建绘图对象
        draw = ImageDraw.Draw(img)
        
        # 如果没有路径节点，直接返回原图
        if not path_nodes or len(path_nodes) < 2:
            return img
        
        # 将逻辑坐标映射到图片坐标
        # 注意：这里使用简化的线性映射，实际应该使用坐标映射表
        img_width, img_height = output_size
        mapped_points = []
        
        for point in path_nodes:
            # 简化的映射：假设逻辑坐标范围是 0-200
            x = (point[0] / 200) * img_width
            y = (point[1] / 200) * img_height
            mapped_points.append((x, y))
        
        # 绘制路径线
        line_color = (255, 0, 0, 200)  # 红色半透明
        line_width = 4
        
        for i in range(len(mapped_points) - 1):
            draw.line(
                [mapped_points[i], mapped_points[i + 1]],
                fill=line_color,
                width=line_width
            )
        
        # 绘制节点
        node_radius = 8
        for i, point in enumerate(mapped_points):
            # 起点用绿色，终点用蓝色，中间点用红色
            if i == 0:
                color = (0, 255, 0, 255)  # 绿色
                label = "起点"
            elif i == len(mapped_points) - 1:
                color = (0, 0, 255, 255)  # 蓝色
                label = "终点"
            else:
                color = (255, 0, 0, 255)  # 红色
                label = str(i)
            
            # 绘制圆点
            x, y = point
            draw.ellipse(
                [(x - node_radius, y - node_radius),
                 (x + node_radius, y + node_radius)],
                fill=color,
                outline=(255, 255, 255),
                width=2
            )
            
            # 绘制标签
            if node_labels and i < len(node_labels):
                label_text = node_labels[i]
            else:
                label_text = label
            
            # 使用默认字体
            try:
                font = ImageFont.truetype("arial.ttf", 14)
            except:
                font = ImageFont.load_default()
            
            # 绘制文字背景
            text_bbox = draw.textbbox((0, 0), label_text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            draw.rectangle(
                [(x + 10, y - 10),
                 (x + 10 + text_width, y - 10 + text_height)],
                fill=(255, 255, 255, 200)
            )
            
            draw.text((x + 10, y - 10), label_text, fill=(0, 0, 0), font=font)
        
        return img
    
    def create_matplotlib_visualization(
        self,
        floor: str,
        path_nodes: Optional[List[Tuple[float, float]]] = None,
        title: Optional[str] = None
    ) -> plt.Figure:
        """
        使用matplotlib创建可视化（适合Streamlit）
        
        Args:
            floor: 楼层标识
            path_nodes: 路径节点坐标
            title: 图表标题
        
        Returns:
            matplotlib Figure对象
        """
        # 加载楼层图
        img = self.load_floorplan(floor)
        
        fig, ax = plt.subplots(1, 1, figsize=(12, 8))
        
        if img:
            # 显示楼层图
            ax.imshow(img)
            ax.set_xlim(0, img.width)
            ax.set_ylim(img.height, 0)  # Y轴翻转
        else:
            # 如果没有楼层图，显示占位符
            ax.text(0.5, 0.5, f"楼层 {floor} 平面图加载失败\n请检查网络连接",
                   ha='center', va='center', transform=ax.transAxes,
                   fontsize=16, color='red', fontproperties=CHINESE_FONT)
            ax.set_xlim(0, 100)
            ax.set_ylim(100, 0)
        
        # 如果有路径节点，绘制路径
        if path_nodes and img:
            # 坐标映射
            img_width, img_height = img.size
            mapped_x = [(p[0] / 200) * img_width for p in path_nodes]
            mapped_y = [(p[1] / 200) * img_height for p in path_nodes]
            
            # 绘制路径线
            ax.plot(mapped_x, mapped_y, 'r-', linewidth=3, alpha=0.8, label='导航路径')
            
            # 绘制节点
            ax.scatter(mapped_x[0], mapped_y[0], s=200, c='green', 
                      marker='o', edgecolors='white', linewidths=2,
                      label='起点', zorder=5)
            ax.scatter(mapped_x[-1], mapped_y[-1], s=200, c='blue',
                      marker='o', edgecolors='white', linewidths=2,
                      label='终点', zorder=5)
            
            if len(mapped_x) > 2:
                ax.scatter(mapped_x[1:-1], mapped_y[1:-1], s=100, c='red',
                          marker='o', alpha=0.6, zorder=4)
            
            ax.legend(loc='upper right', prop=CHINESE_FONT)
        
        # 设置标题
        if title:
            ax.set_title(title, fontsize=14, fontweight='bold', pad=20,
                        fontproperties=CHINESE_FONT)
        else:
            floor_info = self.get_floorplan_info(floor)
            if floor_info:
                ax.set_title(f"{floor_info['name']}", fontsize=14, fontweight='bold',
                            fontproperties=CHINESE_FONT)
            else:
                ax.set_title(f"文萃楼 {floor} 平面图", fontsize=14, fontweight='bold',
                            fontproperties=CHINESE_FONT)
        
        # 隐藏坐标轴
        ax.axis('off')
        
        plt.tight_layout()
        return fig
    
    def get_all_floors(self) -> List[str]:
        """获取所有可用楼层"""
        return list(self.floorplans.keys())
    
    def get_floor_thumbnail(self, floor: str) -> Optional[str]:
        """获取楼层缩略图URL"""
        floor_data = self.floorplans.get(floor)
        if floor_data:
            return floor_data.get("thumbnail")
        return None


# 便捷函数
def create_visualizer(data_dir: str = "../data") -> FloorplanVisualizer:
    """
    创建可视化器实例
    
    Args:
        data_dir: 数据目录路径
    
    Returns:
        FloorplanVisualizer实例
    """
    import os
    floorplan_path = os.path.join(data_dir, "floorplans", "floorplan_urls.json")
    return FloorplanVisualizer(floorplan_path)


# 测试代码
if __name__ == "__main__":
    import sys
    import os
    
    # 测试
    viz = create_visualizer()
    
    print("可用楼层:")
    for floor in viz.get_all_floors():
        info = viz.get_floorplan_info(floor)
        print(f"  {floor}: {info['name']} - {info['description']}")
    
    # 测试加载4F楼层图
    print("\n加载4F楼层图...")
    img = viz.load_floorplan("4F")
    if img:
        print(f"  成功加载: {img.size}")
        
        # 测试路径绘制
        test_path = [(100, 20), (100, 60), (50, 60), (50, 100), (120, 100), (120, 80)]
        result_img = viz.draw_path_on_floorplan("4F", test_path)
        
        if result_img:
            result_img.save("test_floorplan_with_path.png")
            print("  已保存测试图片: test_floorplan_with_path.png")
    else:
        print("  加载失败")

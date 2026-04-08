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
    """楼层平面图可视化器（支持三种坐标系转换）"""
    
    # 楼层图类型配置
    # hires: 高清楼层图 (2235×3614 px, 上北下南、左西右东, 15px/m)
    # unified: 统一校正图 (745×1205 px, 上北下南、左西右东, 5px/m)
    IMAGE_CONFIG = {
        'hires': {
            'size': (2235, 3614),
            'origin_crop': (76, 100),      # 裁切偏移量 (x, y)
            'scale_m_per_px': (1/15, 1/15),  # 米/像素 (约0.0667)
            'orientation': {'north': 'up', 'east': 'right'},  # 上北下南、左西右东
        },
        'unified': {
            'size': (745, 1205),
            'origin_px': (164, 640),       # 报告厅/圆楼中心像素位置
            'scale_m_per_px': (0.2, 0.2),   # 5px/m
            'orientation': {'north': 'up', 'east': 'right'},  # 上北下南、左西右东
        },
        'aligned': {
            'size': (1400, 1000),
            'orientation': {'north': 'up', 'east': 'right'},  # 上北下南、左西右东
        },
    }
    
    def __init__(self, floorplan_urls_path: str, building_data_path: str = None, 
                 use_aligned: bool = True, align_params_path: str = None):
        """
        初始化可视化器
        
        Args:
            floorplan_urls_path: floorplan_urls.json 或 unified_params.json 文件路径
            building_data_path: wencui_building.json 文件路径 (用于获取坐标参考尺寸)
            use_aligned: 是否使用对齐后的楼层图和坐标
            align_params_path: align_params.json 文件路径（对齐坐标转换参数）
        """
        self.use_aligned = use_aligned
        self.align_params = {}
        self.aligned_size = (1400, 1000)  # 对齐后的统一尺寸
        self.image_scales = {}  # 存储每个楼层图片的缩放比例
        
        # 加载楼层图配置
        if floorplan_urls_path and os.path.exists(floorplan_urls_path):
            with open(floorplan_urls_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 支持两种配置格式
            if "floorplans" in data:
                self.floorplans = data.get("floorplans", {})
                self.coordinate_mapping = data.get("coordinate_mapping", {})
            else:
                # unified_params.json 格式
                self.floorplans = {}
                self.coordinate_mapping = data
        else:
            self.floorplans = {}
            self.coordinate_mapping = {}
        
        self.cache = {}  # 图片缓存
        
        # 加载对齐坐标转换参数
        if use_aligned and align_params_path and os.path.exists(align_params_path):
            with open(align_params_path, 'r', encoding='utf-8') as f:
                self.align_params = json.load(f)
            print(f"已加载对齐坐标转换参数: {len(self.align_params)} 个楼层")
        
        # 加载楼层坐标参考尺寸
        self.floor_ref_sizes = {}
        self.floor_coord_ranges = {}  # 存储每个楼层的实际坐标范围
        
        if building_data_path and os.path.exists(building_data_path):
            with open(building_data_path, 'r', encoding='utf-8') as f:
                bdata = json.load(f)
            
            # 从 floor_layouts 获取参考尺寸
            for floor, layout in bdata.get("floor_layouts", {}).items():
                self.floor_ref_sizes[floor] = (layout.get("width", 1400), layout.get("height", 1000))
            
            # 从 nodes 计算实际坐标范围
            nodes = bdata.get("nodes", {})
            floor_nodes = {}
            for node_id, node in nodes.items():
                floor = node.get("floor", "")
                if floor:
                    if floor not in floor_nodes:
                        floor_nodes[floor] = []
                    floor_nodes[floor].append(node)
            
            for floor, nodes_list in floor_nodes.items():
                xs = [n.get("x", 0) for n in nodes_list]
                ys = [n.get("y", 0) for n in nodes_list]
                if xs and ys:
                    self.floor_coord_ranges[floor] = {
                        'min_x': min(xs), 'max_x': max(xs),
                        'min_y': min(ys), 'max_y': max(ys),
                        'width': max(xs) - min(xs),
                        'height': max(ys) - min(ys)
                    }
        
        # 检测并设置图片缩放比例
        self._detect_image_scales()
        
        # 打印坐标范围信息
        if self.floor_coord_ranges:
            print(f"已加载楼层坐标范围: {len(self.floor_coord_ranges)} 个楼层")
            sample = list(self.floor_coord_ranges.items())[0]
            print(f"  示例 - {sample[0]}: 宽={sample[1]['width']:.0f}, 高={sample[1]['height']:.0f}")
    
    def _detect_image_scales(self):
        """检测各楼层图片的实际尺寸并计算相对于标准尺寸的缩放比例"""
        base_dir = os.path.dirname(os.path.dirname(__file__))
        
        # 标准参考尺寸（所有坐标都基于此）
        standard_size = (1400, 1000)  # 默认标准尺寸
        
        for floor in ['1F', '2F', '3F', '4F', '5F', '6F', '7F', '8F', '9F', '10F']:
            # 检查各种可能的图片路径（按优先级）
            possible_paths = [
                (os.path.join(base_dir, 'data', 'floorplans_hires', f'{floor}_hires.jpg'), 'hires'),
                (os.path.join(base_dir, 'data', 'floorplans_unified', f'{floor}_unified.jpg'), 'unified'),
                (os.path.join(base_dir, 'data', 'floorplans_aligned', f'{floor}_aligned.jpg'), 'aligned'),
            ]
            
            for path, img_type in possible_paths:
                if os.path.exists(path):
                    try:
                        img = Image.open(path)
                        actual_size = img.size
                        img.close()
                        
                        # 计算相对于标准尺寸的缩放比例
                        # 这样标准坐标 (1400, 1000) 可以正确映射到任意尺寸的图片
                        scale_x = actual_size[0] / standard_size[0]
                        scale_y = actual_size[1] / standard_size[1]
                        
                        self.image_scales[floor] = {
                            'type': img_type,
                            'actual_size': actual_size,
                            'ref_size': standard_size,  # 使用标准尺寸作为参考
                            'scale': (scale_x, scale_y)
                        }
                        break
                    except Exception as e:
                        print(f"检测 {floor} 图片尺寸失败: {e}")
                        continue
        
        if self.image_scales:
            sample = list(self.image_scales.items())[0]
            print(f"已检测楼层图片尺寸: {len(self.image_scales)} 个楼层")
            print(f"  示例 - {sample[0]}: {sample[1]['type']} {sample[1]['actual_size']} (相对于标准尺寸 {sample[1]['ref_size']} 的缩放: {sample[1]['scale'][0]:.2f}x, {sample[1]['scale'][1]:.2f}x)")
    
    def _get_ref_size(self, floor: str) -> tuple:
        """获取楼层的坐标参考尺寸"""
        # 优先使用实际坐标范围
        if floor in self.floor_coord_ranges:
            coord_range = self.floor_coord_ranges[floor]
            return (coord_range['width'], coord_range['height'])
        
        if self.use_aligned and floor in self.align_params:
            return self.aligned_size
        
        return self.floor_ref_sizes.get(floor, (1400, 1000))
    
    def _get_coord_offset(self, floor: str) -> tuple:
        """获取楼层坐标的最小偏移量（用于将坐标归一化到正数范围）"""
        if floor in self.floor_coord_ranges:
            coord_range = self.floor_coord_ranges[floor]
            return (coord_range['min_x'], coord_range['min_y'])
        return (0, 0)
    
    def _transform_to_aligned(self, floor: str, x: float, y: float) -> Tuple[float, float]:
        """
        将原始坐标转换为对齐后的坐标
        
        Args:
            floor: 楼层标识
            x, y: 原始坐标
            
        Returns:
            对齐后的坐标 (x', y')
        """
        if not self.use_aligned or floor not in self.align_params:
            return (x, y)
        
        params = self.align_params[floor]
        scale = params["scale"]
        offset_x, offset_y = params["offset"]
        
        # 缩放 -> 平移
        x_aligned = x * scale + offset_x
        y_aligned = y * scale + offset_y
        
        return (x_aligned, y_aligned)
    
    def _transform_from_aligned(self, floor: str, x_aligned: float, y_aligned: float) -> Tuple[float, float]:
        """
        将对齐后的坐标转换回原始坐标
        
        Args:
            floor: 楼层标识
            x_aligned, y_aligned: 对齐后的坐标
            
        Returns:
            原始坐标 (x, y)
        """
        if not self.use_aligned or floor not in self.align_params:
            return (x_aligned, y_aligned)
        
        params = self.align_params[floor]
        scale = params["scale"]
        offset_x, offset_y = params["offset"]
        
        # 逆向转换
        x = (x_aligned - offset_x) / scale
        y = (y_aligned - offset_y) / scale
        
        return (x, y)
    
    def _apply_image_scale(self, floor: str, x: float, y: float) -> Tuple[float, float]:
        """
        应用图片缩放比例到坐标
        将标准坐标转换为实际图片上的坐标
        
        Args:
            floor: 楼层标识
            x, y: 标准坐标
            
        Returns:
            缩放后的坐标 (x', y')
        """
        if floor not in self.image_scales:
            return (x, y)
        
        scale_info = self.image_scales[floor]
        scale_x, scale_y = scale_info['scale']
        
        # 应用缩放
        x_scaled = x * scale_x
        y_scaled = y * scale_y
        
        return (x_scaled, y_scaled)
    
    def _remove_image_scale(self, floor: str, x: float, y: float) -> Tuple[float, float]:
        """
        移除图片缩放比例
        将实际图片上的坐标转换回标准坐标
        
        Args:
            floor: 楼层标识
            x, y: 图片上的坐标
            
        Returns:
            标准坐标 (x', y')
        """
        if floor not in self.image_scales:
            return (x, y)
        
        scale_info = self.image_scales[floor]
        scale_x, scale_y = scale_info['scale']
        
        # 移除缩放
        x_std = x / scale_x
        y_std = y / scale_y
        
        return (x_std, y_std)
    
    def _transform_to_image_coords(self, floor: str, ux: float, uy: float) -> Tuple[float, float]:
        """
        将统一校正图坐标 (ux, uy) 转换为图片像素坐标
        
        统一校正图坐标 (ux, uy):
        - 原点: 报告厅/圆楼中心 (ux=164, uy=563)
        - ux: 向东像素数 (右为正)
        - uy: 向南像素数 (下为正，即 uy 大 = 南)
        
        验证: A-301 (uy=157) 在圆楼 (uy=563) 北边：
          157 < 563，所以 A-301 在北边 ✓
        
        高清楼层图 (hires):
        - 原点: 报告厅/圆楼中心 (图片中心)
        - 朝向: 上南下北、左西右东
        - 比例: 15px/m
        
        Args:
            floor: 楼层标识
            ux, uy: 统一校正图坐标 (像素值)
            
        Returns:
            图片像素坐标 (px, py)
        """
        if floor not in self.image_scales:
            return (ux, uy)
        
        # 获取图片实际尺寸
        img_w, img_h = self.image_scales[floor]['actual_size']
        
        # 比例尺: v6 数据使用 5px/m (从 east_m/ux 关系计算得出)
        scale = 5
        
        # 圆楼/报告厅原点坐标（在统一校正图中的位置）
        origin_ux = 164
        origin_uy = 564
        
        # 计算相对于圆楼的偏移
        dx = ux - origin_ux  # 东为正
        dy = uy - origin_uy  # 南为正（uy 大 = 南）
        
        # 转换为 east_m 和 south_m
        # dx 像素 -> east_m (东为正)
        # dy 像素 -> south_m (南为正，因为 uy 向南增加)
        east_m = dx / scale
        south_m = dy / scale
        
        # 楼层图朝向: 根据实际图片判断
        # 从 3F_hires.jpg 看：上方=K/L区(北)，下方=A/B/C区(南)
        # 所以楼层图是 "上北下南"
        # 图片中心 = 圆楼位置
        center_x = img_w / 2
        center_y = img_h / 2
        
        # - east_m 向东 -> px 向右（增加）
        # - south_m 向南 -> 南是下方，所以 south_m 正 = Y 大（下方）
        #                    北是上方，所以 south_m 负 = Y 小（上方）
        px = center_x + east_m * scale
        py = center_y + south_m * scale  # 修正：上北下南，南=下方=Y增加
        
        return (px, py)
    
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
        """获取本地楼层图路径 - 优先使用高清楼层图"""
        base_dir = os.path.dirname(os.path.dirname(__file__))
        
        # 1. 优先使用高清楼层图 (floorplans_hires)
        hires_path = os.path.join(
            base_dir, "data", "floorplans_hires", f"{floor}_hires.jpg"
        )
        if os.path.exists(hires_path):
            return hires_path
        
        # 2. 如果启用对齐，使用对齐后的图片
        if self.use_aligned:
            aligned_path = os.path.join(
                base_dir, "data", "floorplans_aligned", f"{floor}_aligned.jpg"
            )
            if os.path.exists(aligned_path):
                return aligned_path
        
        # 3. 使用统一坐标系的图片
        unified_path = os.path.join(
            base_dir, "data", "floorplans_unified", f"{floor}_unified.jpg"
        )
        if os.path.exists(unified_path):
            return unified_path
        
        # 4. 使用官方下载的原始图片
        official_path = os.path.join(base_dir, "data", "floorplans", f"{floor}_official.jpg")
        if os.path.exists(official_path):
            return official_path
        
        # 5. 最后使用生成的示例图
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
        output_size: Tuple[int, int] = (800, 600),
        use_aligned_coords: bool = False
    ) -> Optional[Image.Image]:
        """
        在楼层平面图上绘制路径（支持高清楼层图）
        
        Args:
            floor: 楼层标识
            path_nodes: 路径节点坐标列表 [(x1,y1), (x2,y2), ...]
                       如果 use_aligned_coords=True，则传入的是原始坐标，会自动转换
            node_labels: 节点标签列表
            output_size: 输出图片尺寸
            use_aligned_coords: 传入的坐标是否为原始坐标（需要转换）
        
        Returns:
            带路径的Image对象
        """
        # 加载楼层图
        img = self.load_floorplan(floor)
        if not img:
            return None
        
        # 获取原始图片尺寸
        original_size = img.size
        
        # 调整大小
        img = img.resize(output_size, Image.Resampling.LANCZOS)
        
        # 创建绘图对象
        draw = ImageDraw.Draw(img)
        
        # 如果没有路径节点，直接返回原图
        if not path_nodes or len(path_nodes) < 2:
            return img
        
        # 将逻辑坐标映射到图片坐标
        img_width, img_height = output_size
        ref_w, ref_h = self._get_ref_size(floor)
        offset_x, offset_y = self._get_coord_offset(floor)
        mapped_points = []
        
        # 计算 resize 比例
        resize_scale_x = img_width / original_size[0]
        resize_scale_y = img_height / original_size[1]
        
        for point in path_nodes:
            # 获取建筑数据坐标 (x, y)
            x_data, y_data = point[0], point[1]
            
            # 转换为图片像素坐标
            px, py = self._transform_to_image_coords(floor, x_data, y_data)
            
            # 再映射到输出图片坐标（考虑resize）
            x = px * resize_scale_x
            y = py * resize_scale_y
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
        title: Optional[str] = None,
        use_standardized_coords: bool = False,
        highlight_node: Optional[Tuple[float, float]] = None,
        highlight_label: str = "起点"
    ) -> plt.Figure:
        """
        使用matplotlib创建可视化（适合Streamlit）
        
        Args:
            floor: 楼层标识
            path_nodes: 路径节点坐标
            title: 图表标题
            use_standardized_coords: 传入的坐标是否为原始坐标（需要转换）
            highlight_node: 要高亮显示的节点坐标（如起点标记）
            highlight_label: 高亮节点的标签
        
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
            ref_w, ref_h = self._get_ref_size(floor)
            
            mapped_x = []
            mapped_y = []
            
            for point in path_nodes:
                # 如果需要，先转换为对齐坐标
                if use_standardized_coords and self.use_aligned:
                    x_aligned, y_aligned = self._transform_to_aligned(floor, point[0], point[1])
                else:
                    x_aligned, y_aligned = point[0], point[1]
                
                # 再映射到图片坐标
                mapped_x.append((x_aligned / ref_w) * img_width)
                mapped_y.append((y_aligned / ref_h) * img_height)
            
            # 始终绘制圆楼原点 (ux=164, uy=563)
            origin_px, origin_py = self._transform_to_image_coords(floor, 164, 563)
            ax.scatter(origin_px, origin_py, s=300, c='red', 
                      marker='+', linewidths=3, label='圆楼原点', zorder=10)
            ax.annotate('圆楼原点', (origin_px, origin_py), 
                       xytext=(-50, -25), textcoords='offset points',
                       fontsize=10, color='red', fontweight='bold',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.8))
            
            # 如果有高亮节点（单个节点标记）
            if highlight_node and not path_nodes:
                px, py = self._transform_to_image_coords(floor, highlight_node[0], highlight_node[1])
                ax.scatter(px, py, s=300, c='green', 
                          marker='o', edgecolors='white', linewidths=3,
                          label=highlight_label, zorder=5)
                # 添加标签
                ax.annotate(highlight_label, (px, py), 
                           xytext=(10, 10), textcoords='offset points',
                           fontsize=12, fontweight='bold', color='green',
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
                
                ax.legend(loc='upper right', prop=CHINESE_FONT)
            
            # 如果有路径节点，绘制路径
            elif path_nodes:
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
def create_visualizer(
    data_dir: str = "../data",
    use_aligned: bool = True
) -> FloorplanVisualizer:
    """
    创建可视化器实例
    
    Args:
        data_dir: 数据目录路径
        use_aligned: 是否使用对齐楼层图和坐标
    
    Returns:
        FloorplanVisualizer实例
    """
    import os
    floorplan_path = os.path.join(data_dir, "floorplans", "floorplan_urls.json")
    building_path = os.path.join(data_dir, "wencui_building_aligned_fixed.json")
    
    align_params_path = None
    if use_aligned:
        align_params_path = os.path.join(
            data_dir, "floorplans_aligned", "align_params.json"
        )
    
    return FloorplanVisualizer(
        floorplan_path,
        building_path,
        use_aligned=use_aligned,
        align_params_path=align_params_path
    )


# 测试代码
if __name__ == "__main__":
    import sys
    import os
    
    # 测试（使用对齐坐标）
    print("=" * 50)
    print("楼层平面图可视化器测试（对齐坐标版）")
    print("=" * 50)
    
    viz = create_visualizer(use_aligned=True)
    
    print("\n可用楼层:")
    for floor in viz.get_all_floors():
        info = viz.get_floorplan_info(floor)
        print(f"  {floor}: {info['name']} - {info['description']}")
    
    # 测试加载4F楼层图
    print("\n加载4F楼层图（使用对齐图片）...")
    img = viz.load_floorplan("4F")
    if img:
        print(f"  成功加载: {img.size}")
        print(f"  参考尺寸: {viz._get_ref_size('4F')}")
        
        # 测试坐标转换
        print("\n测试坐标转换（4F）:")
        # D402 的原始坐标
        original_coords = (2270, 420)
        aligned_coords = viz._transform_to_aligned("4F", *original_coords)
        print(f"  原始坐标 {original_coords} -> 对齐坐标 {aligned_coords}")
        
        # 反向转换
        back_coords = viz._transform_from_aligned("4F", *aligned_coords)
        print(f"  对齐坐标 {aligned_coords} -> 原始坐标 {back_coords}")
        
        # 测试路径绘制（使用原始坐标，自动转换）
        # D402 附近的一些示例路径点（原始坐标系）
        test_path_original = [
            (2000, 400),   # 某点
            (2100, 400),   # 某点
            (2200, 420),   # 某点
            (2270, 420),   # D402
        ]
        
        print("\n测试路径绘制（原始坐标自动转换）...")
        result_img = viz.draw_path_on_floorplan(
            "4F", 
            test_path_original,
            use_aligned_coords=True
        )
        
        if result_img:
            result_img.save("test_floorplan_with_path.png")
            print("  已保存测试图片: test_floorplan_with_path.png")
        
        # 测试 matplotlib 可视化
        print("\n测试 Matplotlib 可视化...")
        fig = viz.create_matplotlib_visualization(
            "4F",
            test_path_original,
            title="4F 测试路径（对齐坐标）",
            use_standardized_coords=True
        )
        fig.savefig("test_matplotlib_viz.png", dpi=150, bbox_inches='tight')
        print("  已保存: test_matplotlib_viz.png")
        plt.close(fig)
        
    else:
        print("  加载失败")

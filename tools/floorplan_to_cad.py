"""
楼层图矢量化工具
将楼层平面图转换为CAD/矢量格式，提取房间边界和编号
"""

import json
import os
import sys
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from dataclasses import dataclass
from typing import List, Tuple, Dict


@dataclass
class RoomContour:
    """房间轮廓"""
    room_id: str
    contour: np.ndarray  # OpenCV轮廓
    bbox: Tuple[int, int, int, int]  # (x, y, w, h)
    center: Tuple[int, int]  # 中心点
    area: float


@dataclass
class RoomLabel:
    """房间标签"""
    text: str
    bbox: Tuple[int, int, int, int]  # (x, y, w, h)
    center: Tuple[int, int]
    confidence: float


class FloorplanVectorizer:
    """楼层图矢量化器"""
    
    def __init__(self):
        self.image = None
        self.gray = None
        self.contours = []
        self.room_labels = []
        self.scale_factor = 1.0
        
    def load_image(self, image_path: str):
        """加载楼层图"""
        self.image = cv2.imread(image_path)
        if self.image is None:
            raise ValueError(f"无法加载图片: {image_path}")
        
        # 转换为灰度图
        self.gray = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
        print(f"加载图片: {image_path}, 尺寸: {self.image.shape}")
        return self.image.shape[:2]
    
    def detect_room_contours(self, min_area=500, max_area=50000) -> List[RoomContour]:
        """
        检测房间轮廓
        基于颜色/纹理分割房间区域
        """
        if self.gray is None:
            return []
        
        # 使用自适应阈值分离房间边界
        # 假设房间有不同的背景色
        blurred = cv2.GaussianBlur(self.gray, (5, 5), 0)
        
        # 边缘检测
        edges = cv2.Canny(blurred, 50, 150)
        
        # 膨胀连接断开的边缘
        kernel = np.ones((3, 3), np.uint8)
        edges = cv2.dilate(edges, kernel, iterations=2)
        edges = cv2.erode(edges, kernel, iterations=1)
        
        # 查找轮廓
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        rooms = []
        for i, contour in enumerate(contours):
            area = cv2.contourArea(contour)
            if min_area < area < max_area:
                x, y, w, h = cv2.boundingRect(contour)
                center = (x + w//2, y + h//2)
                
                room = RoomContour(
                    room_id=f"room_{i:03d}",
                    contour=contour,
                    bbox=(x, y, w, h),
                    center=center,
                    area=area
                )
                rooms.append(room)
        
        # 按面积排序
        rooms.sort(key=lambda r: r.area, reverse=True)
        self.contours = rooms
        print(f"检测到 {len(rooms)} 个房间轮廓")
        return rooms
    
    def detect_room_labels(self, floor: str) -> List[RoomLabel]:
        """
        检测房间编号标签
        使用OCR或模板匹配识别房间号（如 A-101, L-201）
        """
        labels = []
        
        # 这里使用简单的启发式方法：
        # 房间号通常在房间中心附近，且是文字区域
        
        # 1. 检测文字区域（高对比度小区域）
        # 2. 使用OCR识别文字
        
        # 简化版本：基于已知房间位置生成标签
        # 实际应用中可以使用 pytesseract 进行OCR
        
        return labels
    
    def generate_cad_data(self, floor: str) -> Dict:
        """
        生成CAD格式的数据
        包含房间轮廓、中心点、标签位置
        """
        cad_data = {
            "floor": floor,
            "coordinate_system": {
                "type": "pixel",
                "origin": [0, 0],
                "scale": 1.0,
                "unit": "pixel"
            },
            "rooms": [],
            "corridors": [],
            "stairs": [],
            "elevators": []
        }
        
        for room in self.contours:
            # 将轮廓转换为多边形点序列
            epsilon = 0.02 * cv2.arcLength(room.contour, True)
            approx = cv2.approxPolyDP(room.contour, epsilon, True)
            points = approx.reshape(-1, 2).tolist()
            
            room_data = {
                "id": room.room_id,
                "bbox": room.bbox,
                "center": room.center,
                "area": room.area,
                "polygon": points
            }
            cad_data["rooms"].append(room_data)
        
        return cad_data
    
    def visualize_detection(self, show_contours=True, show_labels=True) -> np.ndarray:
        """可视化检测结果"""
        if self.image is None:
            return None
        
        vis = self.image.copy()
        
        # 绘制房间轮廓
        if show_contours and self.contours:
            for i, room in enumerate(self.contours[:50]):  # 最多显示50个
                color = (0, 255, 0) if i < 20 else (255, 0, 0)
                cv2.drawContours(vis, [room.contour], -1, color, 2)
                
                # 绘制中心点
                cv2.circle(vis, room.center, 5, (0, 0, 255), -1)
                
                # 标注编号
                cv2.putText(vis, str(i), (room.center[0]-10, room.center[1]),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        return vis
    
    def export_to_dxf(self, output_path: str):
        """
        导出为DXF格式（AutoCAD）
        简化版本，生成基本的DXF结构
        """
        dxf_content = []
        dxf_content.append("0")
        dxf_content.append("SECTION")
        dxf_content.append("2")
        dxf_content.append("ENTITIES")
        
        for room in self.contours:
            # 为每个房间创建LWPOLYLINE
            dxf_content.append("0")
            dxf_content.append("LWPOLYLINE")
            dxf_content.append("8")
            dxf_content.append("Rooms")
            dxf_content.append("90")  # 顶点数
            dxf_content.append(str(len(room.contour)))
            dxf_content.append("70")
            dxf_content.append("1")  # 闭合
            
            for point in room.contour.reshape(-1, 2):
                dxf_content.append("10")
                dxf_content.append(str(point[0]))
                dxf_content.append("20")
                dxf_content.append(str(point[1]))
        
        dxf_content.append("0")
        dxf_content.append("ENDSEC")
        dxf_content.append("0")
        dxf_content.append("EOF")
        
        with open(output_path, 'w') as f:
            f.write('\n'.join(dxf_content))
        
        print(f"DXF文件已保存: {output_path}")


class FloorplanCADApp:
    """楼层图CAD转换GUI"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("楼层图矢量化工具 (Floorplan → CAD)")
        self.root.geometry("1400x900")
        
        self.vectorizer = FloorplanVectorizer()
        self.current_image = None
        self.detection_result = None
        
        self.create_ui()
    
    def create_ui(self):
        """创建用户界面"""
        # 左侧控制面板
        left_frame = ttk.Frame(self.root, padding="10", width=350)
        left_frame.pack(side=tk.LEFT, fill=tk.Y)
        left_frame.pack_propagate(False)
        
        # 图片选择
        ttk.Label(left_frame, text="楼层图:", font=('Arial', 12, 'bold')).pack(anchor=tk.W, pady=(0, 5))
        ttk.Button(left_frame, text="选择图片...", command=self.select_image).pack(anchor=tk.W, fill=tk.X)
        self.image_path_var = tk.StringVar()
        ttk.Label(left_frame, textvariable=self.image_path_var, wraplength=330).pack(anchor=tk.W, pady=(5, 10))
        
        # 检测参数
        ttk.Label(left_frame, text="检测参数:", font=('Arial', 11, 'bold')).pack(anchor=tk.W, pady=(10, 5))
        
        ttk.Label(left_frame, text="最小面积:").pack(anchor=tk.W)
        self.min_area_var = tk.IntVar(value=500)
        ttk.Entry(left_frame, textvariable=self.min_area_var, width=10).pack(anchor=tk.W)
        
        ttk.Label(left_frame, text="最大面积:").pack(anchor=tk.W, pady=(5, 0))
        self.max_area_var = tk.IntVar(value=50000)
        ttk.Entry(left_frame, textvariable=self.max_area_var, width=10).pack(anchor=tk.W)
        
        # 操作按钮
        ttk.Button(left_frame, text="检测房间轮廓", command=self.detect_rooms).pack(anchor=tk.W, fill=tk.X, pady=(20, 5))
        ttk.Button(left_frame, text="生成CAD数据", command=self.generate_cad).pack(anchor=tk.W, fill=tk.X, pady=(5, 5))
        ttk.Button(left_frame, text="导出DXF", command=self.export_dxf).pack(anchor=tk.W, fill=tk.X, pady=(5, 5))
        
        # 统计信息
        self.stats_label = ttk.Label(left_frame, text="未加载图片", font=('Arial', 10))
        self.stats_label.pack(anchor=tk.W, pady=(20, 0))
        
        # 右侧图像显示
        right_frame = ttk.Frame(self.root, padding="10")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # 图像标签
        self.image_label = ttk.Label(right_frame)
        self.image_label.pack(fill=tk.BOTH, expand=True)
    
    def select_image(self):
        """选择图片"""
        path = filedialog.askopenfilename(
            title="选择楼层图",
            filetypes=[("图片文件", "*.jpg *.jpeg *.png"), ("所有文件", "*.*")]
        )
        if path:
            try:
                h, w = self.vectorizer.load_image(path)
                self.image_path_var.set(f"{path}\n尺寸: {w}x{h}")
                self.show_image(self.vectorizer.image)
                self.stats_label.config(text=f"已加载: {w}x{h} 像素")
            except Exception as e:
                messagebox.showerror("错误", str(e))
    
    def detect_rooms(self):
        """检测房间"""
        if self.vectorizer.image is None:
            messagebox.showwarning("提示", "请先选择图片")
            return
        
        try:
            min_area = self.min_area_var.get()
            max_area = self.max_area_var.get()
            
            rooms = self.vectorizer.detect_room_contours(min_area, max_area)
            
            # 显示结果
            vis = self.vectorizer.visualize_detection()
            self.show_image(vis)
            
            self.stats_label.config(text=f"检测到 {len(rooms)} 个房间")
            messagebox.showinfo("完成", f"检测到 {len(rooms)} 个房间轮廓")
            
        except Exception as e:
            messagebox.showerror("错误", str(e))
    
    def generate_cad(self):
        """生成CAD数据"""
        if not self.vectorizer.contours:
            messagebox.showwarning("提示", "请先检测房间")
            return
        
        floor = "1F"  # 可以从文件名推断
        cad_data = self.vectorizer.generate_cad_data(floor)
        
        # 保存JSON
        output_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json")]
        )
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(cad_data, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("完成", f"CAD数据已保存:\n{output_path}")
    
    def export_dxf(self):
        """导出DXF"""
        if not self.vectorizer.contours:
            messagebox.showwarning("提示", "请先检测房间")
            return
        
        output_path = filedialog.asksaveasfilename(
            defaultextension=".dxf",
            filetypes=[("DXF文件", "*.dxf")]
        )
        if output_path:
            self.vectorizer.export_to_dxf(output_path)
            messagebox.showinfo("完成", f"DXF文件已保存:\n{output_path}")
    
    def show_image(self, cv_image):
        """显示OpenCV图像到Tkinter"""
        # 转换颜色空间
        cv_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
        
        # 转换为PIL图像
        pil_image = Image.fromarray(cv_image)
        
        # 缩放以适应显示区域
        max_size = (1200, 800)
        pil_image.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # 转换为Tkinter图像
        from PIL import ImageTk
        tk_image = ImageTk.PhotoImage(pil_image)
        
        self.image_label.config(image=tk_image)
        self.image_label.image = tk_image  # 保持引用


def main():
    root = tk.Tk()
    app = FloorplanCADApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

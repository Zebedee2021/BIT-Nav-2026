"""
楼层房间位置测试工具
选择楼层，显示该层所有房间，并在楼层图上用红色框标注房间位置
用于验证JSON数据的准确性
"""

import json
import os
import sys
from PIL import Image, ImageDraw, ImageFont
import tkinter as tk
from tkinter import ttk, messagebox

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class FloorRoomTester:
    def __init__(self, root):
        self.root = root
        self.root.title("楼层房间位置测试工具")
        self.root.geometry("1400x900")
        
        # 加载数据
        self.load_data()
        
        # 创建UI
        self.create_ui()
        
    def load_data(self):
        """加载建筑数据"""
        base_dir = os.path.dirname(os.path.dirname(__file__))
        
        # 加载建筑图数据
        building_path = os.path.join(base_dir, 'data', 'wencui_building_aligned_fixed.json')
        with open(building_path, 'r', encoding='utf-8') as f:
            self.building_data = json.load(f)
        
        # 加载对齐参数
        align_path = os.path.join(base_dir, 'data', 'floorplans_aligned', 'align_params.json')
        with open(align_path, 'r', encoding='utf-8') as f:
            self.align_params = json.load(f)
        
        # 提取所有楼层
        self.floors = sorted(set(
            node['floor'] for node in self.building_data['nodes'].values()
            if 'floor' in node
        ), key=lambda f: int(f.replace('F', '')))
        
        print(f"加载完成：{len(self.building_data['nodes'])} 个节点，{len(self.floors)} 个楼层")
        
    def create_ui(self):
        """创建用户界面"""
        # 左侧控制面板
        left_frame = ttk.Frame(self.root, padding="10")
        left_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        # 楼层选择
        ttk.Label(left_frame, text="选择楼层:", font=('Arial', 12, 'bold')).pack(anchor=tk.W, pady=(0, 5))
        self.floor_var = tk.StringVar()
        self.floor_combo = ttk.Combobox(left_frame, textvariable=self.floor_var, values=self.floors, state='readonly', width=10)
        self.floor_combo.pack(anchor=tk.W, pady=(0, 10))
        self.floor_combo.bind('<<ComboboxSelected>>', self.on_floor_selected)
        
        # 统计信息
        self.stats_label = ttk.Label(left_frame, text="", font=('Arial', 10))
        self.stats_label.pack(anchor=tk.W, pady=(0, 10))
        
        # 筛选选项
        ttk.Label(left_frame, text="筛选:", font=('Arial', 11, 'bold')).pack(anchor=tk.W, pady=(10, 5))
        
        self.filter_var = tk.StringVar(value="all")
        ttk.Radiobutton(left_frame, text="显示所有", variable=self.filter_var, value="all", 
                       command=self.refresh_display).pack(anchor=tk.W)
        ttk.Radiobutton(left_frame, text="仅房间", variable=self.filter_var, value="room", 
                       command=self.refresh_display).pack(anchor=tk.W)
        ttk.Radiobutton(left_frame, text="仅走廊", variable=self.filter_var, value="corridor", 
                       command=self.refresh_display).pack(anchor=tk.W)
        ttk.Radiobutton(left_frame, text="仅楼梯/电梯", variable=self.filter_var, value="transit", 
                       command=self.refresh_display).pack(anchor=tk.W)
        
        # 框大小设置
        ttk.Label(left_frame, text="标注框大小:", font=('Arial', 11, 'bold')).pack(anchor=tk.W, pady=(15, 5))
        self.box_size_var = tk.IntVar(value=30)
        ttk.Scale(left_frame, from_=10, to=100, variable=self.box_size_var, orient=tk.HORIZONTAL,
                 command=lambda _: self.refresh_display()).pack(anchor=tk.W, fill=tk.X)
        ttk.Label(left_frame, textvariable=self.box_size_var).pack(anchor=tk.W)
        
        # 显示选项
        ttk.Label(left_frame, text="显示选项:", font=('Arial', 11, 'bold')).pack(anchor=tk.W, pady=(15, 5))
        self.show_labels_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(left_frame, text="显示标签", variable=self.show_labels_var, 
                       command=self.refresh_display).pack(anchor=tk.W)
        self.show_coords_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(left_frame, text="显示坐标", variable=self.show_coords_var, 
                       command=self.refresh_display).pack(anchor=tk.W)
        
        # 操作按钮
        ttk.Button(left_frame, text="刷新显示", command=self.refresh_display).pack(anchor=tk.W, pady=(20, 5), fill=tk.X)
        ttk.Button(left_frame, text="保存图片", command=self.save_image).pack(anchor=tk.W, pady=(5, 5), fill=tk.X)
        
        # 房间列表
        ttk.Label(left_frame, text="房间列表:", font=('Arial', 11, 'bold')).pack(anchor=tk.W, pady=(15, 5))
        
        # 创建Treeview
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(anchor=tk.W, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.room_list = ttk.Treeview(list_frame, columns=('id', 'name', 'type'), 
                                     show='headings', height=20, yscrollcommand=scrollbar.set)
        self.room_list.heading('id', text='ID')
        self.room_list.heading('name', text='名称')
        self.room_list.heading('type', text='类型')
        self.room_list.column('id', width=100)
        self.room_list.column('name', width=100)
        self.room_list.column('type', width=60)
        self.room_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.room_list.yview)
        
        self.room_list.bind('<<TreeviewSelect>>', self.on_room_selected)
        
        # 右侧图像显示区
        right_frame = ttk.Frame(self.root, padding="10")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # 图像标签
        self.image_label = ttk.Label(right_frame)
        self.image_label.pack(fill=tk.BOTH, expand=True)
        
        # 选中房间信息
        self.info_label = ttk.Label(right_frame, text="请选择楼层", font=('Arial', 11), wraplength=800)
        self.info_label.pack(anchor=tk.W, pady=(10, 0))
        
        # 默认选择第一层
        if self.floors:
            self.floor_combo.set(self.floors[0])
            self.on_floor_selected(None)
    
    def on_floor_selected(self, event):
        """楼层选择事件"""
        floor = self.floor_var.get()
        if not floor:
            return
        
        # 获取该楼层所有节点
        self.current_floor_nodes = []
        for node_id, node in self.building_data['nodes'].items():
            if node.get('floor') == floor:
                self.current_floor_nodes.append((node_id, node))
        
        # 按ID排序
        self.current_floor_nodes.sort(key=lambda x: x[0])
        
        # 更新统计
        room_count = sum(1 for _, n in self.current_floor_nodes if n.get('type') == 'room')
        corridor_count = sum(1 for _, n in self.current_floor_nodes if n.get('type') == 'corridor')
        self.stats_label.config(text=f"房间: {room_count}  走廊: {corridor_count}  总计: {len(self.current_floor_nodes)}")
        
        # 更新房间列表
        self.update_room_list()
        
        # 刷新显示
        self.refresh_display()
    
    def update_room_list(self):
        """更新房间列表"""
        # 清空列表
        for item in self.room_list.get_children():
            self.room_list.delete(item)
        
        # 添加节点
        for node_id, node in self.current_floor_nodes:
            self.room_list.insert('', tk.END, values=(
                node_id,
                node.get('name', ''),
                node.get('type', '')
            ))
    
    def get_filtered_nodes(self):
        """根据筛选条件获取节点"""
        filter_type = self.filter_var.get()
        
        if filter_type == "all":
            return self.current_floor_nodes
        elif filter_type == "room":
            return [(id, n) for id, n in self.current_floor_nodes if n.get('type') == 'room']
        elif filter_type == "corridor":
            return [(id, n) for id, n in self.current_floor_nodes if n.get('type') == 'corridor']
        elif filter_type == "transit":
            return [(id, n) for id, n in self.current_floor_nodes 
                   if n.get('type') in ('stairs', 'elevator')]
        return self.current_floor_nodes
    
    def refresh_display(self):
        """刷新图像显示"""
        floor = self.floor_var.get()
        if not floor or not hasattr(self, 'current_floor_nodes'):
            return
        
        # 加载楼层图
        img = self.load_floorplan(floor)
        if img is None:
            messagebox.showerror("错误", f"无法加载 {floor} 的楼层图")
            return
        
        # 创建绘图对象
        draw = ImageDraw.Draw(img)
        
        # 获取对齐参数
        params = self.align_params.get(floor, {})
        scale = params.get('scale', 1.0)
        offset = params.get('offset', [0, 0])
        offset_x = offset[0] if len(offset) > 0 else 0
        offset_y = offset[1] if len(offset) > 1 else 0
        
        # 获取筛选后的节点
        nodes_to_show = self.get_filtered_nodes()
        
        # 绘制节点
        box_size = self.box_size_var.get()
        show_labels = self.show_labels_var.get()
        show_coords = self.show_coords_var.get()
        
        # 颜色定义
        colors = {
            'room': (255, 0, 0),      # 红色
            'corridor': (0, 255, 0),   # 绿色
            'stairs': (255, 165, 0),   # 橙色
            'elevator': (128, 0, 128), # 紫色
            'entrance': (0, 0, 255),   # 蓝色
            'unknown': (128, 128, 128) # 灰色
        }
        
        # 调试：记录第一个楼梯/电梯的计算
        debug_nodes = []
        
        for node_id, node in nodes_to_show:
            x = node.get('x', 0)
            y = node.get('y', 0)
            
            # 坐标变换（从JSON坐标到图像坐标）
            img_x = x * scale + offset_x
            img_y = y * scale + offset_y
            
            # 收集调试信息
            if node.get('type') in ('stairs', 'elevator') and len(debug_nodes) < 3:
                debug_nodes.append(f"{node_id}: ({x},{y}) -> ({img_x:.1f},{img_y:.1f})")
            
            node_type = node.get('type', 'unknown')
            color = colors.get(node_type, colors['unknown'])
            
            # 绘制红色方框
            draw.rectangle(
                [img_x - box_size//2, img_y - box_size//2,
                 img_x + box_size//2, img_y + box_size//2],
                outline=color, width=3
            )
            
            # 绘制中心点
            draw.ellipse([img_x-3, img_y-3, img_x+3, img_y+3], fill=color)
            
            # 绘制标签
            if show_labels:
                label = node.get('name', node_id)
                if show_coords:
                    label += f" ({int(x)},{int(y)})"
                
                # 尝试使用默认字体
                try:
                    draw.text((img_x + box_size//2 + 2, img_y - 6), label, fill=color)
                except:
                    pass
        
        # 调试：在图上显示对齐参数和节点计算
        debug_text = f"Scale: {scale:.3f}, Offset: ({offset_x:.1f}, {offset_y:.1f}), ImgSize: {img.size}"
        draw.text((10, 10), debug_text, fill=(255, 0, 0))
        for i, txt in enumerate(debug_nodes):
            draw.text((10, 30 + i*20), txt, fill=(255, 0, 0))
        
        # 保存当前图像用于保存功能
        self.current_image = img
        
        # 转换为Tkinter图像
        from PIL import ImageTk
        # 缩放以适应显示区域
        display_width = 900
        ratio = display_width / img.width
        display_height = int(img.height * ratio)
        
        display_img = img.resize((display_width, display_height), Image.Resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(display_img)
        
        # 更新显示
        self.image_label.config(image=self.tk_image)
        
        # 更新信息
        self.info_label.config(
            text=f"楼层: {floor} | 显示节点: {len(nodes_to_show)} | "
                 f"缩放: {scale:.3f} | 偏移: ({offset_x}, {offset_y})"
        )
    
    def load_floorplan(self, floor):
        """加载楼层图"""
        base_dir = os.path.dirname(os.path.dirname(__file__))
        
        # 优先使用对齐后的图片
        aligned_path = os.path.join(base_dir, 'data', 'floorplans_aligned', f'{floor}_aligned.jpg')
        if os.path.exists(aligned_path):
            return Image.open(aligned_path)
        
        # 其次使用官方图片
        official_path = os.path.join(base_dir, 'data', 'floorplans', f'{floor}_official.jpg')
        if os.path.exists(official_path):
            return Image.open(official_path)
        
        # 最后使用标准图片
        standard_path = os.path.join(base_dir, 'data', 'floorplans_standardized', f'{floor}_standardized.jpg')
        if os.path.exists(standard_path):
            return Image.open(standard_path)
        
        return None
    
    def on_room_selected(self, event):
        """房间选择事件"""
        selection = self.room_list.selection()
        if not selection:
            return
        
        item = self.room_list.item(selection[0])
        node_id = item['values'][0]
        
        # 查找节点信息
        node = self.building_data['nodes'].get(node_id, {})
        
        info = f"选中: {node_id}\n"
        info += f"名称: {node.get('name', 'N/A')}\n"
        info += f"类型: {node.get('type', 'N/A')}\n"
        info += f"楼层: {node.get('floor', 'N/A')}\n"
        info += f"分区: {node.get('zone', 'N/A')}\n"
        info += f"坐标: ({node.get('x', 'N/A')}, {node.get('y', 'N/A')})\n"
        info += f"描述: {node.get('description', 'N/A')[:50]}"
        
        self.info_label.config(text=info)
    
    def save_image(self):
        """保存当前图像"""
        if not hasattr(self, 'current_image'):
            messagebox.showwarning("警告", "没有可保存的图像")
            return
        
        floor = self.floor_var.get()
        filename = f"floor_test_{floor}.png"
        
        save_path = os.path.join(os.path.dirname(__file__), filename)
        self.current_image.save(save_path)
        
        messagebox.showinfo("保存成功", f"图像已保存到:\n{save_path}")


def main():
    root = tk.Tk()
    app = FloorRoomTester(root)
    root.mainloop()


if __name__ == "__main__":
    main()

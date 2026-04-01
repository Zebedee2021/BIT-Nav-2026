"""
房间位置手动校准工具
通过交互式点击或拖框来校准房间位置
"""

import json
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from PIL import Image, ImageDraw, ImageTk

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class RoomPositionCalibrator:
    def __init__(self, root):
        self.root = root
        self.root.title("房间位置手动校准工具")
        self.root.geometry("1600x1000")
        
        # 加载数据
        self.load_data()
        
        # 当前状态
        self.current_floor = None
        self.current_node_id = None
        self.canvas_image = None
        self.canvas_image_id = None
        self.selection_rect = None
        self.temp_rect = None
        self.start_x = 0
        self.start_y = 0
        
        # 待保存的修改（不持久化，每次启动清空）
        self.pending_changes = {}  # {node_id: {x, y}}
        
        # 创建UI
        self.create_ui()
        
        print("校准工具已启动，pending_changes 已清空")
        
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
        left_frame = ttk.Frame(self.root, padding="10", width=350)
        left_frame.pack(side=tk.LEFT, fill=tk.Y)
        left_frame.pack_propagate(False)
        
        # 楼层选择
        ttk.Label(left_frame, text="选择楼层:", font=('Arial', 12, 'bold')).pack(anchor=tk.W, pady=(0, 5))
        self.floor_var = tk.StringVar()
        self.floor_combo = ttk.Combobox(left_frame, textvariable=self.floor_var, 
                                        values=self.floors, state='readonly', width=10)
        self.floor_combo.pack(anchor=tk.W, pady=(0, 10))
        self.floor_combo.bind('<<ComboboxSelected>>', self.on_floor_selected)
        
        # 节点筛选
        ttk.Label(left_frame, text="筛选类型:", font=('Arial', 11, 'bold')).pack(anchor=tk.W, pady=(10, 5))
        self.filter_var = tk.StringVar(value="stairs")
        filter_frame = ttk.Frame(left_frame)
        filter_frame.pack(anchor=tk.W, fill=tk.X)
        ttk.Radiobutton(filter_frame, text="楼梯", variable=self.filter_var, 
                       value="stairs", command=self.refresh_node_list).pack(side=tk.LEFT)
        ttk.Radiobutton(filter_frame, text="电梯", variable=self.filter_var, 
                       value="elevator", command=self.refresh_node_list).pack(side=tk.LEFT)
        ttk.Radiobutton(filter_frame, text="房间", variable=self.filter_var, 
                       value="room", command=self.refresh_node_list).pack(side=tk.LEFT)
        ttk.Radiobutton(filter_frame, text="全部", variable=self.filter_var, 
                       value="all", command=self.refresh_node_list).pack(side=tk.LEFT)
        
        # 节点列表
        ttk.Label(left_frame, text="节点列表:", font=('Arial', 11, 'bold')).pack(anchor=tk.W, pady=(15, 5))
        
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(anchor=tk.W, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.node_list = ttk.Treeview(list_frame, columns=('id', 'name', 'current_pos'), 
                                     show='headings', height=15, yscrollcommand=scrollbar.set)
        self.node_list.heading('id', text='ID')
        self.node_list.heading('name', text='名称')
        self.node_list.heading('current_pos', text='当前坐标')
        self.node_list.column('id', width=120)
        self.node_list.column('name', width=100)
        self.node_list.column('current_pos', width=80)
        self.node_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.node_list.yview)
        
        self.node_list.bind('<<TreeviewSelect>>', self.on_node_selected)
        
        # 当前选中节点信息
        ttk.Label(left_frame, text="选中节点:", font=('Arial', 11, 'bold')).pack(anchor=tk.W, pady=(15, 5))
        self.node_info_text = tk.Text(left_frame, height=6, width=40, font=('Consolas', 9))
        self.node_info_text.pack(anchor=tk.W, fill=tk.X)
        
        # 新位置显示
        ttk.Label(left_frame, text="新位置:", font=('Arial', 11, 'bold')).pack(anchor=tk.W, pady=(10, 5))
        self.new_pos_var = tk.StringVar(value="未设置")
        ttk.Label(left_frame, textvariable=self.new_pos_var, font=('Consolas', 10)).pack(anchor=tk.W)
        
        # 操作按钮
        btn_frame = ttk.Frame(left_frame)
        btn_frame.pack(anchor=tk.W, fill=tk.X, pady=(20, 5))
        
        ttk.Button(btn_frame, text="确认位置", command=self.confirm_position).pack(fill=tk.X, pady=(0, 5))
        ttk.Button(btn_frame, text="跳过此节点", command=self.skip_node).pack(fill=tk.X, pady=(0, 5))
        ttk.Button(btn_frame, text="保存所有修改", command=self.save_changes).pack(fill=tk.X, pady=(0, 5))
        ttk.Button(btn_frame, text="清除当前节点修改", command=self.clear_current_change).pack(fill=tk.X, pady=(0, 5))
        ttk.Button(btn_frame, text="清除所有待保存", command=self.clear_all_changes).pack(fill=tk.X, pady=(0, 5))
        
        # 修改统计
        self.changes_label = ttk.Label(left_frame, text="待保存修改: 0", font=('Arial', 10))
        self.changes_label.pack(anchor=tk.W, pady=(10, 0))
        
        # 右侧图像区
        right_frame = ttk.Frame(self.root, padding="10")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # 操作说明
        ttk.Label(right_frame, text="操作说明: 1.选择节点 2.在图上拖动绘制方框 3.点击确认位置", 
                 font=('Arial', 10), foreground='blue').pack(anchor=tk.W, pady=(0, 5))
        
        # 缩放控制
        zoom_frame = ttk.Frame(right_frame)
        zoom_frame.pack(anchor=tk.W, pady=(0, 5))
        ttk.Label(zoom_frame, text="缩放:").pack(side=tk.LEFT)
        self.zoom_var = tk.DoubleVar(value=1.0)
        self.zoom_scale = ttk.Scale(zoom_frame, from_=0.5, to=3.0, variable=self.zoom_var, 
                                    orient=tk.HORIZONTAL, length=200, command=self.on_zoom_change)
        self.zoom_scale.pack(side=tk.LEFT, padx=(5, 0))
        self.zoom_label = ttk.Label(zoom_frame, text="100%")
        self.zoom_label.pack(side=tk.LEFT, padx=(5, 0))
        ttk.Button(zoom_frame, text="重置", command=self.reset_zoom).pack(side=tk.LEFT, padx=(10, 0))
        ttk.Button(zoom_frame, text="显示/隐藏网格", command=self.toggle_grid).pack(side=tk.LEFT, padx=(10, 0))
        ttk.Button(zoom_frame, text="滚动到原点", command=self.scroll_to_origin).pack(side=tk.LEFT, padx=(10, 0))
        
        # Canvas框架（带滚动条）
        canvas_frame = ttk.Frame(right_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        # 滚动条
        h_scroll = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        v_scroll = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Canvas用于显示图片和绘制
        self.canvas = tk.Canvas(canvas_frame, bg='gray', cursor='crosshair',
                               xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        h_scroll.config(command=self.canvas.xview)
        v_scroll.config(command=self.canvas.yview)
        
        # Canvas事件绑定
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)  # 鼠标滚轮缩放
        
        # 默认选择第一层（延迟加载图片，等待Canvas初始化）
        if self.floors:
            self.floor_combo.set(self.floors[0])
            self.root.after(100, lambda: self.on_floor_selected(None))
    
    def on_floor_selected(self, event):
        """楼层选择事件"""
        floor = self.floor_var.get()
        if not floor:
            return
        
        self.current_floor = floor
        
        # 加载楼层图
        self.load_floor_image(floor)
        
        # 刷新节点列表
        self.refresh_node_list()
        
    def load_floor_image(self, floor):
        """加载楼层图到Canvas - 使用高分辨率原图"""
        base_dir = os.path.dirname(os.path.dirname(__file__))
        
        # 楼层号转换（如 "1F" -> "1"）
        floor_num = floor.replace('F', '')
        
        # 优先使用高分辨率原图
        img_path = os.path.join(base_dir, 'wencui', f'{floor_num}.jpg')
        if not os.path.exists(img_path):
            # 回退到对齐后的图片
            img_path = os.path.join(base_dir, 'data', 'floorplans_aligned', f'{floor}_aligned.jpg')
        if not os.path.exists(img_path):
            img_path = os.path.join(base_dir, 'data', 'floorplans', f'{floor}_official.jpg')
        
        if not os.path.exists(img_path):
            messagebox.showerror("错误", f"无法加载 {floor} 的楼层图")
            return
        
        # 加载高分辨率原图
        self.original_image = Image.open(img_path)
        print(f"加载图片: {img_path}, 尺寸: {self.original_image.size}")
        
        # 计算缩放比例以适应窗口（初始显示）
        canvas_width = max(self.canvas.winfo_width(), 1200)
        canvas_height = max(self.canvas.winfo_height(), 800)
        
        img_width, img_height = self.original_image.size
        scale_w = canvas_width / img_width
        scale_h = canvas_height / img_height
        self.display_scale = min(scale_w, scale_h, 0.5)  # 初始显示不超过50%
        
        new_width = max(int(img_width * self.display_scale), 1)
        new_height = max(int(img_height * self.display_scale), 1)
        
        self.display_image = self.original_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(self.display_image)
        
        # 更新Canvas
        self.canvas.config(width=new_width, height=new_height)
        self.canvas_image_id = self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)
        
        # 保存图像尺寸信息
        self.img_width = img_width
        self.img_height = img_height
        
        # 设置Canvas滚动区域
        self.canvas.config(scrollregion=(0, 0, new_width, new_height))
        
        # 延迟绘制坐标系（确保图片已显示）
        self.root.after(50, self.draw_coordinate_grid)
        
    def draw_coordinate_grid(self):
        """绘制标准数学坐标系 - 类似示例图风格"""
        if not hasattr(self, 'show_grid'):
            self.show_grid = True
        
        if not self.show_grid:
            return
        
        print(f"绘制坐标系: {self.current_floor}")
        
        # 清除旧网格
        if hasattr(self, 'grid_items'):
            for item in self.grid_items:
                self.canvas.delete(item)
        self.grid_items = []
        
        # 获取对齐参数
        params = self.align_params.get(self.current_floor, {})
        scale = params.get('scale', 1.0)
        offset = params.get('offset', [0, 0])
        offset_x = offset[0] if len(offset) > 0 else 0
        offset_y = offset[1] if len(offset) > 1 else 0
        
        zoom = self.zoom_var.get()
        canvas_width = int(self.img_width * self.display_scale * zoom)
        canvas_height = int(self.img_height * self.display_scale * zoom)
        
        # 原点在原图上的位置
        origin_img_x = offset_x
        origin_img_y = offset_y
        origin_disp_x = origin_img_x * self.display_scale * zoom
        origin_disp_y = origin_img_y * self.display_scale * zoom
        
        # ===== 1. 绘制浅蓝色背景栅格（基于1400x1000目标坐标系） =====
        # 目标坐标系范围：X=0~1400, Y=0~1000
        grid_spacing_json = 200  # JSON坐标每200一个栅格
        
        # 垂直栅格线（对应JSON X坐标）
        for i in range(0, 1600, grid_spacing_json):
            img_x = i * scale + offset_x
            disp_x = img_x * self.display_scale * zoom
            if 0 <= disp_x <= canvas_width:
                line = self.canvas.create_line(disp_x, 0, disp_x, canvas_height,
                                              fill='#E6F3FF', width=1)
                self.grid_items.append(line)
        
        # 水平栅格线（对应JSON Y坐标）
        for i in range(0, 1200, grid_spacing_json):
            img_y = i * scale + offset_y
            disp_y = img_y * self.display_scale * zoom
            if 0 <= disp_y <= canvas_height:
                line = self.canvas.create_line(0, disp_y, canvas_width, disp_y,
                                              fill='#E6F3FF', width=1)
                self.grid_items.append(line)
        
        # ===== 2. 绘制坐标轴（带箭头）- 使用粗线条确保可见 =====
        arrow_size = 12
        axis_color_x = '#FF0000'  # 纯红
        axis_color_y = '#0000FF'  # 纯蓝
        
        # X轴（红色）- 始终绘制，即使部分在视野外
        x_axis_y = int(origin_disp_y)
        # 轴线（加粗）
        x_axis = self.canvas.create_line(0, x_axis_y, canvas_width, x_axis_y,
                                         fill=axis_color_x, width=3)
        # 箭头（在右侧）
        x_arrow = self.canvas.create_polygon(
            canvas_width - 25, x_axis_y - arrow_size//2,
            canvas_width - 25, x_axis_y + arrow_size//2,
            canvas_width, x_axis_y,
            fill=axis_color_x, outline='black', width=1
        )
        # X标签
        x_label = self.canvas.create_text(canvas_width - 40, x_axis_y + 25,
                                          text="X", fill=axis_color_x,
                                          font=('Arial', 16, 'bold'))
        self.grid_items.extend([x_axis, x_arrow, x_label])
        
        # Y轴（蓝色）- 箭头向下（屏幕坐标系）
        y_axis_x = int(origin_disp_x)
        # 轴线（加粗）- 从原点向下延伸
        y_axis = self.canvas.create_line(y_axis_x, origin_disp_y, y_axis_x, canvas_height,
                                         fill=axis_color_y, width=3)
        # 箭头（在底部，指向下方）
        y_arrow = self.canvas.create_polygon(
            y_axis_x - arrow_size//2, canvas_height - 25,
            y_axis_x + arrow_size//2, canvas_height - 25,
            y_axis_x, canvas_height,
            fill=axis_color_y, outline='black', width=1
        )
        # Y标签（在箭头附近）
        y_label = self.canvas.create_text(y_axis_x - 25, canvas_height - 40,
                                          text="Y", fill=axis_color_y,
                                          font=('Arial', 16, 'bold'))
        self.grid_items.extend([y_axis, y_arrow, y_label])
        
        # ===== 3. 绘制刻度和数字（基于1400x1000坐标系） =====
        tick_length = 10
        
        # X轴刻度（沿X轴绘制，每200一个刻度，每400标数字）
        for i in range(0, 1600, 200):
            img_x = i * scale + offset_x
            disp_x = img_x * self.display_scale * zoom
            if 0 <= disp_x <= canvas_width:
                # 刻度线（垂直于X轴）
                tick = self.canvas.create_line(disp_x, origin_disp_y,
                                               disp_x, origin_disp_y + tick_length,
                                               fill='red', width=2)
                self.grid_items.append(tick)
                
                # 数字标签（每400）
                if i % 400 == 0:
                    label = self.canvas.create_text(disp_x, origin_disp_y + 25,
                                                   text=str(i), fill='red',
                                                   font=('Arial', 10, 'bold'))
                    self.grid_items.append(label)
        
        # Y轴刻度（沿Y轴绘制，每200一个刻度，每400标数字）
        for i in range(0, 1200, 200):
            img_y = i * scale + offset_y
            disp_y = img_y * self.display_scale * zoom
            if 0 <= disp_y <= canvas_height:
                # 刻度线（垂直于Y轴，向左延伸）
                tick = self.canvas.create_line(origin_disp_x - tick_length, disp_y,
                                               origin_disp_x, disp_y,
                                               fill='blue', width=2)
                self.grid_items.append(tick)
                
                # 数字标签（每400）
                if i % 400 == 0:
                    label = self.canvas.create_text(origin_disp_x - 30, disp_y,
                                                   text=str(i), fill='blue',
                                                   font=('Arial', 10, 'bold'))
                    self.grid_items.append(label)
        
        # ===== 4. 绘制原点O =====
        origin_o = self.canvas.create_text(origin_disp_x - 15, origin_disp_y + 15,
                                          text="O", fill='red',
                                          font=('Arial', 12, 'bold'))
        self.grid_items.append(origin_o)
        
        # ===== 5. 绘制坐标系信息 =====
        info_text = f"坐标系: JSON(0~1400, 0~1000) → 原图({offset_x:.0f}~{offset_x+1400*scale:.0f}, {offset_y:.0f}~{offset_y+1000*scale:.0f})"
        info_bg = self.canvas.create_rectangle(5, canvas_height - 35, 550, canvas_height - 5,
                                               fill='white', outline='gray', width=1)
        info_label = self.canvas.create_text(10, canvas_height - 20, text=info_text,
                                             anchor=tk.W, font=('Consolas', 9), fill='#333333')
        self.grid_items.extend([info_bg, info_label])
        
        # 调整图层顺序：背景栅格在最底层，坐标轴在上层
        foreground_items = {info_bg, info_label, x_axis, x_arrow, x_label, 
                           y_axis, y_arrow, y_label, origin_o}
        for item in self.grid_items:
            if item not in foreground_items:
                self.canvas.tag_lower(item)  # 背景栅格移到最底层
    
    def on_zoom_change(self, event=None):
        """缩放变化处理"""
        zoom = self.zoom_var.get()
        self.zoom_label.config(text=f"{int(zoom*100)}%")
        self.reload_image_with_zoom()
    
    def on_mousewheel(self, event):
        """鼠标滚轮缩放"""
        current_zoom = self.zoom_var.get()
        if event.delta > 0:
            new_zoom = min(current_zoom + 0.1, 3.0)
        else:
            new_zoom = max(current_zoom - 0.1, 0.5)
        self.zoom_var.set(new_zoom)
        self.on_zoom_change()
    
    def reset_zoom(self):
        """重置缩放"""
        self.zoom_var.set(1.0)
        self.on_zoom_change()
    
    def toggle_grid(self):
        """切换网格显示"""
        self.show_grid = not getattr(self, 'show_grid', True)
        if self.show_grid:
            self.draw_coordinate_grid()
        else:
            if hasattr(self, 'grid_items'):
                for item in self.grid_items:
                    self.canvas.delete(item)
                self.grid_items = []
    
    def scroll_to_origin(self):
        """滚动到原点位置"""
        if not self.current_floor:
            return
        
        # 获取对齐参数
        params = self.align_params.get(self.current_floor, {})
        offset = params.get('offset', [0, 0])
        offset_x = offset[0] if len(offset) > 0 else 0
        offset_y = offset[1] if len(offset) > 1 else 0
        
        zoom = self.zoom_var.get()
        origin_disp_x = offset_x * self.display_scale * zoom
        origin_disp_y = offset_y * self.display_scale * zoom
        
        # 滚动到原点中心
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        x_fraction = max(0, (origin_disp_x - canvas_width//2) / (self.img_width * self.display_scale * zoom))
        y_fraction = max(0, (origin_disp_y - canvas_height//2) / (self.img_height * self.display_scale * zoom))
        
        self.canvas.xview_moveto(x_fraction)
        self.canvas.yview_moveto(y_fraction)
        
        print(f"滚动到原点: ({origin_disp_x:.0f}, {origin_disp_y:.0f})")
    
    def reload_image_with_zoom(self):
        """使用新缩放比例重新加载图片"""
        if not self.current_floor or not hasattr(self, 'original_image'):
            return
        
        zoom = self.zoom_var.get()
        
        # 重新计算尺寸
        new_width = max(int(self.img_width * self.display_scale * zoom), 1)
        new_height = max(int(self.img_height * self.display_scale * zoom), 1)
        
        # 调整图片大小
        self.display_image = self.original_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(self.display_image)
        
        # 更新Canvas
        self.canvas.itemconfig(self.canvas_image_id, image=self.tk_image)
        self.canvas.config(scrollregion=(0, 0, new_width, new_height))
        
        # 重绘网格和高亮
        self.draw_coordinate_grid()
        if self.current_node_id:
            node = self.building_data['nodes'].get(self.current_node_id, {})
            if self.current_node_id in self.pending_changes:
                x = self.pending_changes[self.current_node_id]['x']
                y = self.pending_changes[self.current_node_id]['y']
            else:
                x = node.get('x', 0)
                y = node.get('y', 0)
            self.highlight_current_position(x, y)
    
    def refresh_node_list(self):
        """刷新节点列表"""
        # 清空列表
        for item in self.node_list.get_children():
            self.node_list.delete(item)
        
        if not self.current_floor:
            return
        
        filter_type = self.filter_var.get()
        
        # 收集节点
        nodes = []
        for node_id, node in self.building_data['nodes'].items():
            if node.get('floor') != self.current_floor:
                continue
            
            node_type = node.get('type', '')
            if filter_type != 'all' and node_type != filter_type:
                continue
            
            x = node.get('x', 0)
            y = node.get('y', 0)
            
            # 检查是否有待保存的修改
            if node_id in self.pending_changes:
                x = self.pending_changes[node_id]['x']
                y = self.pending_changes[node_id]['y']
                status = "*"
            else:
                status = ""
            
            nodes.append((node_id, node.get('name', ''), f"({int(x)},{int(y)}){status}"))
        
        # 排序并添加
        nodes.sort(key=lambda x: x[0])
        for node_id, name, pos in nodes:
            self.node_list.insert('', tk.END, values=(node_id, name, pos))
    
    def on_node_selected(self, event):
        """节点选择事件"""
        selection = self.node_list.selection()
        if not selection:
            return
        
        item = self.node_list.item(selection[0])
        node_id = item['values'][0]
        self.current_node_id = node_id
        
        # 获取节点信息
        node = self.building_data['nodes'].get(node_id, {})
        
        # 使用待保存的坐标或原始坐标
        if node_id in self.pending_changes:
            x = self.pending_changes[node_id]['x']
            y = self.pending_changes[node_id]['y']
            coord_source = "(待保存)"
        else:
            x = node.get('x', 0)
            y = node.get('y', 0)
            coord_source = "(原始)"
        
        # 验证坐标合理性
        if x > 3000 or y > 2000:
            print(f"警告: {node_id} 的坐标异常: ({x}, {y})")
            # 尝试使用原始坐标
            x = node.get('x', 0)
            y = node.get('y', 0)
            coord_source = "(原始-修正)"
        
        # 调试输出
        print(f"选择节点: {node_id}, 坐标: ({x}, {y}), 来源: {coord_source}")
        if node_id in self.pending_changes:
            print(f"  pending_changes: {self.pending_changes[node_id]}")
        
        # 显示节点信息
        info = f"ID: {node_id}\n"
        info += f"名称: {node.get('name', 'N/A')}\n"
        info += f"类型: {node.get('type', 'N/A')}\n"
        info += f"当前坐标: ({x:.1f}, {y:.1f}) {coord_source}\n"
        info += f"描述: {node.get('description', 'N/A')[:30]}"
        
        self.node_info_text.delete('1.0', tk.END)
        self.node_info_text.insert('1.0', info)
        
        # 在图上高亮当前位置
        self.highlight_current_position(x, y)
        
        self.new_pos_var.set("未设置 - 请在图上拖框")
        
    def highlight_current_position(self, x, y):
        """在图上高亮当前节点位置 - 基于原图坐标系"""
        # 清除之前的高亮
        if self.selection_rect:
            self.canvas.delete(self.selection_rect)
        if hasattr(self, 'highlight_items'):
            for item in self.highlight_items:
                self.canvas.delete(item)
        self.highlight_items = []
        
        # 获取对齐参数，将JSON坐标转换为原图坐标
        params = self.align_params.get(self.current_floor, {})
        scale = params.get('scale', 1.0)
        offset = params.get('offset', [0, 0])
        offset_x = offset[0] if len(offset) > 0 else 0
        offset_y = offset[1] if len(offset) > 1 else 0
        
        # JSON坐标 -> 原图坐标
        img_x = x * scale + offset_x
        img_y = y * scale + offset_y
        
        # 缩放到显示尺寸（包含用户缩放）
        zoom = self.zoom_var.get()
        disp_x = img_x * self.display_scale * zoom
        disp_y = img_y * self.display_scale * zoom
        
        # 绘制高亮框（根据原图分辨率调整大小）
        size = 30 * self.display_scale * zoom  # 原图较大，框也相应增大
        self.selection_rect = self.canvas.create_rectangle(
            disp_x - size, disp_y - size,
            disp_x + size, disp_y + size,
            outline='red', width=3, dash=(5, 5)
        )
        self.highlight_items.append(self.selection_rect)
        
        # 绘制中心点
        center = self.canvas.create_oval(disp_x-5, disp_y-5, disp_x+5, disp_y+5, fill='red')
        self.highlight_items.append(center)
        
        # 绘制坐标标签
        label = self.canvas.create_text(disp_x, disp_y - size - 15, 
                                       text=f"({int(x)}, {int(y)})",
                                       fill='red', font=('Arial', 10, 'bold'))
        self.highlight_items.append(label)
        
        # 滚动到该位置
        self.canvas.xview_moveto(max(0, disp_x - 600) / (self.img_width * self.display_scale * zoom))
        self.canvas.yview_moveto(max(0, disp_y - 400) / (self.img_height * self.display_scale * zoom))
        
    def on_canvas_click(self, event):
        """Canvas点击事件 - 开始绘制"""
        # 获取Canvas坐标（考虑滚动偏移）
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        
        # 清除临时矩形
        if self.temp_rect:
            self.canvas.delete(self.temp_rect)
    
    def on_canvas_drag(self, event):
        """Canvas拖动事件 - 绘制临时矩形"""
        if self.temp_rect:
            self.canvas.delete(self.temp_rect)
        
        # 获取Canvas坐标（考虑滚动偏移）
        cur_x = self.canvas.canvasx(event.x)
        cur_y = self.canvas.canvasy(event.y)
        
        self.temp_rect = self.canvas.create_rectangle(
            self.start_x, self.start_y, cur_x, cur_y,
            outline='green', width=2, dash=(3, 3)
        )
    
    def on_canvas_release(self, event):
        """Canvas释放事件 - 完成绘制"""
        if not self.current_node_id:
            messagebox.showwarning("提示", "请先选择一个节点")
            return
        
        # 获取Canvas坐标（考虑滚动偏移）
        end_x = self.canvas.canvasx(event.x)
        end_y = self.canvas.canvasy(event.y)
        
        # 计算中心点
        center_x = (self.start_x + end_x) / 2
        center_y = (self.start_y + end_y) / 2
        
        # 将显示坐标转换回JSON坐标
        json_x, json_y = self.display_to_json_coords(center_x, center_y)
        
        # 保存临时位置
        self.temp_new_pos = {'x': json_x, 'y': json_y}
        
        # 更新显示
        self.new_pos_var.set(f"({int(json_x)}, {int(json_y)})")
        
        # 固定矩形
        if self.temp_rect:
            self.canvas.delete(self.temp_rect)
        self.temp_rect = self.canvas.create_rectangle(
            self.start_x, self.start_y, end_x, end_y,
            outline='green', width=3
        )
        
    def display_to_json_coords(self, disp_x, disp_y):
        """将显示坐标转换为JSON坐标 - 基于原图坐标系"""
        # 获取对齐参数
        params = self.align_params.get(self.current_floor, {})
        scale = params.get('scale', 1.0)
        offset = params.get('offset', [0, 0])
        offset_x = offset[0] if len(offset) > 0 else 0
        offset_y = offset[1] if len(offset) > 1 else 0
        
        # 考虑用户缩放
        zoom = self.zoom_var.get()
        
        # 显示坐标 -> 原图坐标
        img_x = disp_x / (self.display_scale * zoom)
        img_y = disp_y / (self.display_scale * zoom)
        
        # 原图坐标 -> JSON坐标
        json_x = (img_x - offset_x) / scale
        json_y = (img_y - offset_y) / scale
        
        # 限制在合理范围内
        json_x = max(0, min(json_x, 2000))
        json_y = max(0, min(json_y, 1500))
        
        return json_x, json_y
    
    def confirm_position(self):
        """确认位置"""
        if not self.current_node_id:
            messagebox.showwarning("提示", "请先选择一个节点")
            return
        
        if not hasattr(self, 'temp_new_pos'):
            messagebox.showwarning("提示", "请先在图上拖动绘制方框")
            return
        
        # 保存到待修改列表
        self.pending_changes[self.current_node_id] = self.temp_new_pos.copy()
        
        # 更新统计
        self.changes_label.config(text=f"待保存修改: {len(self.pending_changes)}")
        
        # 刷新节点列表以显示标记
        self.refresh_node_list()
        
        # 自动选择下一个节点
        self.select_next_node()
        
    def skip_node(self):
        """跳过当前节点"""
        self.select_next_node()
    
    def select_next_node(self):
        """选择列表中的下一个节点"""
        selection = self.node_list.selection()
        if not selection:
            return
        
        current_item = selection[0]
        next_item = self.node_list.next(current_item)
        
        if next_item:
            self.node_list.selection_set(next_item)
            self.node_list.see(next_item)
            self.on_node_selected(None)
    
    def clear_current_change(self):
        """清除当前节点的待保存修改"""
        if not self.current_node_id:
            return
        
        if self.current_node_id in self.pending_changes:
            del self.pending_changes[self.current_node_id]
            self.changes_label.config(text=f"待保存修改: {len(self.pending_changes)}")
            self.refresh_node_list()
            self.on_node_selected(None)  # 刷新显示
            messagebox.showinfo("完成", f"已清除 {self.current_node_id} 的修改")
    
    def clear_all_changes(self):
        """清除所有待保存修改"""
        if not self.pending_changes:
            messagebox.showinfo("提示", "没有待保存的修改")
            return
        
        if messagebox.askyesno("确认", f"确定要清除 {len(self.pending_changes)} 个待保存修改吗？"):
            self.pending_changes.clear()
            self.changes_label.config(text="待保存修改: 0")
            self.refresh_node_list()
            if self.current_node_id:
                self.on_node_selected(None)
            messagebox.showinfo("完成", "已清除所有待保存修改")
    
    def save_changes(self):
        """保存所有修改到JSON文件"""
        if not self.pending_changes:
            messagebox.showinfo("提示", "没有待保存的修改")
            return
        
        # 过滤异常值
        valid_changes = {}
        for node_id, new_pos in self.pending_changes.items():
            x, y = new_pos['x'], new_pos['y']
            if 0 <= x <= 2000 and 0 <= y <= 1500:
                valid_changes[node_id] = new_pos
            else:
                print(f"跳过异常坐标: {node_id} ({x}, {y})")
        
        if not valid_changes:
            messagebox.showwarning("警告", "没有有效的修改可保存（所有坐标都超出范围）")
            return
        
        # 更新数据
        for node_id, new_pos in valid_changes.items():
            if node_id in self.building_data['nodes']:
                # 保存原始坐标
                if 'original_x' not in self.building_data['nodes'][node_id]:
                    self.building_data['nodes'][node_id]['original_x'] = \
                        self.building_data['nodes'][node_id].get('x', 0)
                    self.building_data['nodes'][node_id]['original_y'] = \
                        self.building_data['nodes'][node_id].get('y', 0)
                
                # 更新坐标
                self.building_data['nodes'][node_id]['x'] = new_pos['x']
                self.building_data['nodes'][node_id]['y'] = new_pos['y']
                self.building_data['nodes'][node_id]['calibrated'] = True
                self.building_data['nodes'][node_id]['calibrated_date'] = "2025-03-30"
        
        # 保存文件
        base_dir = os.path.dirname(os.path.dirname(__file__))
        output_path = os.path.join(base_dir, 'data', 'wencui_building_aligned_fixed.json')
        
        # 备份原文件
        import shutil
        backup_path = output_path + '.backup'
        if os.path.exists(output_path):
            shutil.copy2(output_path, backup_path)
        
        # 保存新文件
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.building_data, f, ensure_ascii=False, indent=2)
        
        # 清空待保存列表
        saved_count = len(self.pending_changes)
        self.pending_changes.clear()
        self.changes_label.config(text="待保存修改: 0")
        
        messagebox.showinfo("保存成功", f"已保存 {saved_count} 个节点的位置修改\n原文件已备份到 .backup")
        
        # 刷新列表
        self.refresh_node_list()


def main():
    root = tk.Tk()
    app = RoomPositionCalibrator(root)
    root.mainloop()


if __name__ == "__main__":
    main()

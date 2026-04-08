#!/usr/bin/env python3
"""
原点校准工具 - 交互式调整圆楼中心位置
用法：
  1. 运行脚本
  2. 在图上点击圆楼实际中心位置
  3. 脚本会输出新的 HALL_ORIG_X 和 HALL_ORIG_Y
"""

from PIL import Image, ImageDraw
import tkinter as tk
from tkinter import ttk

# 加载 1F 楼层图
img = Image.open('data/archive/floorplans/1F_official.jpg')
print(f"原始图尺寸: {img.size}")

# 当前原点参数（从 floorplan_align.py）
CURRENT_HALL_X = 1370
CURRENT_HALL_Y = 1440

class OriginCalibrator:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("原点校准工具 - 点击圆楼中心")
        
        # 创建画布
        self.canvas = tk.Canvas(self.root, width=800, height=600)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # 缩放因子（适应窗口）
        self.scale = min(800 / img.size[0], 600 / img.size[1])
        self.scaled_w = int(img.size[0] * self.scale)
        self.scaled_h = int(img.size[1] * self.scale)
        
        # 缩放图片显示
        display_img = img.resize((self.scaled_w, self.scaled_h), Image.Resampling.LANCZOS)
        self.photo = tk.PhotoImage(file='data/temp_display.png')
        display_img.save('data/temp_display.png')
        self.photo = tk.PhotoImage(file='data/temp_display.png')
        
        self.canvas.create_image(0, 0, anchor="nw", image=self.photo)
        
        # 绘制当前原点位置
        cx = int(CURRENT_HALL_X * self.scale)
        cy = int(CURRENT_HALL_Y * self.scale)
        r = 15
        self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r, outline="red", width=3)
        self.canvas.create_line(cx-30, cy, cx+30, cy, fill="red", width=2)
        self.canvas.create_line(cx, cy-30, cx, cy+30, fill="red", width=2)
        self.canvas.create_text(cx, cy-25, text=f"当前原点\n({CURRENT_HALL_X}, {CURRENT_HALL_Y})", 
                                fill="red", font=("微软雅黑", 10))
        
        # 提示文字
        self.canvas.create_text(400, 20, text="请点击圆楼的实际中心位置", 
                                fill="blue", font=("微软雅黑", 14, "bold"))
        
        # 绑定点击事件
        self.canvas.bind("<Button-1>", self.on_click)
        
        # 显示新原点
        self.result_text = self.canvas.create_text(400, 580, text="", 
                                                   fill="green", font=("微软雅黑", 12, "bold"))
        
        self.new_marker = None
        
    def on_click(self, event):
        # 转换回原始坐标
        orig_x = round(event.x / self.scale)
        orig_y = round(event.y / self.scale)
        
        # 删除旧标记
        if self.new_marker:
            for item in self.new_marker:
                self.canvas.delete(item)
        
        # 绘制新标记
        r = 15
        m1 = self.canvas.create_oval(event.x-r, event.y-r, event.x+r, event.y+r, 
                                     outline="green", width=3)
        m2 = self.canvas.create_line(event.x-30, event.y, event.x+30, event.y, 
                                     fill="green", width=2)
        m3 = self.canvas.create_line(event.x, event.y-30, event.x, event.y+30, 
                                     fill="green", width=2)
        m4 = self.canvas.create_text(event.x, event.y-25, 
                                     text=f"新原点\n({orig_x}, {orig_y})", 
                                     fill="green", font=("微软雅黑", 10))
        self.new_marker = [m1, m2, m3, m4]
        
        # 更新结果文字
        self.canvas.itemconfig(self.result_text, 
                               text=f"新原点坐标: HALL_ORIG_X = {orig_x}, HALL_ORIG_Y = {orig_y}")
        
        print(f"\n新原点坐标:")
        print(f"  HALL_ORIG_X = {orig_x}")
        print(f"  HALL_ORIG_Y = {orig_y}")
        
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    calibrator = OriginCalibrator()
    calibrator.run()

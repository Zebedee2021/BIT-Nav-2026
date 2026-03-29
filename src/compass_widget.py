"""
指南针可视化组件
用于Streamlit中显示指南针和方位指示
"""

import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import math
from typing import Dict, Tuple


def create_compass_image(heading: float, size: int = 200) -> Image.Image:
    """
    创建指南针图像
    
    Args:
        heading: 当前朝向角度（0-360，0为北）
        size: 图像大小
    
    Returns:
        PIL Image对象
    """
    # 创建透明背景
    img = Image.new('RGBA', (size, size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    center = size // 2
    radius = size // 2 - 20
    
    # 绘制外圈
    draw.ellipse(
        [(center - radius, center - radius),
         (center + radius, center + radius)],
        outline=(200, 200, 200, 255),
        width=3
    )
    
    # 绘制内圈
    draw.ellipse(
        [(center - radius + 10, center - radius + 10),
         (center + radius - 10, center + radius - 10)],
        outline=(230, 230, 230, 255),
        width=1
    )
    
    # 绘制方位标记
    directions = [
        (0, "N", (255, 0, 0)),      # 北 - 红色
        (90, "E", (0, 0, 0)),       # 东
        (180, "S", (0, 0, 0)),      # 南
        (270, "W", (0, 0, 0)),      # 西
    ]
    
    try:
        font = ImageFont.truetype("arial.ttf", 16)
        font_large = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()
        font_large = ImageFont.load_default()
    
    for angle, label, color in directions:
        # 计算位置（注意：图像坐标系中，角度需要调整）
        rad = math.radians(-angle)  # 逆时针为正
        x = center + (radius - 25) * math.sin(rad)
        y = center - (radius - 25) * math.cos(rad)
        
        # 绘制方位文字
        bbox = draw.textbbox((0, 0), label, font=font_large if label == "N" else font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        draw.text(
            (x - text_width // 2, y - text_height // 2),
            label,
            fill=color if label == "N" else (100, 100, 100),
            font=font_large if label == "N" else font
        )
    
    # 绘制刻度线
    for i in range(0, 360, 30):
        rad = math.radians(-i)
        x1 = center + (radius - 5) * math.sin(rad)
        y1 = center - (radius - 5) * math.cos(rad)
        x2 = center + radius * math.sin(rad)
        y2 = center - radius * math.cos(rad)
        draw.line([(x1, y1), (x2, y2)], fill=(150, 150, 150), width=1)
    
    # 绘制指针（指向heading方向）
    # 指针是固定的，但整个指南针会根据heading旋转
    # 这里我们让指针固定指向"上"（北），通过旋转整个图像来模拟
    
    # 绘制指针（三角形）
    pointer_length = radius - 30
    pointer_width = 12
    
    # 指针顶点（指向北/上）
    tip = (center, center - pointer_length)
    # 指针底部左右
    left = (center - pointer_width, center + pointer_width)
    right = (center + pointer_width, center + pointer_width)
    
    # 绘制红色指针（北）
    draw.polygon([tip, left, right], fill=(255, 0, 0, 200), outline=(200, 0, 0))
    
    # 绘制中心点
    draw.ellipse(
        [(center - 5, center - 5), (center + 5, center + 5)],
        fill=(50, 50, 50)
    )
    
    # 旋转图像以匹配heading
    # heading 0 = 北 = 图像不需要旋转
    # heading 90 = 东 = 图像顺时针旋转90度
    rotated = img.rotate(-heading, resample=Image.Resampling.BICUBIC, expand=False)
    
    return rotated


def create_direction_arrow(direction_angle: float, size: int = 100) -> Image.Image:
    """
    创建方向箭头图像
    
    Args:
        direction_angle: 方向角度（0-360）
        size: 图像大小
    
    Returns:
        PIL Image对象
    """
    img = Image.new('RGBA', (size, size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    center = size // 2
    arrow_length = size // 2 - 10
    
    # 计算箭头终点
    rad = math.radians(-direction_angle)  # 转换为弧度，注意方向
    end_x = center + arrow_length * math.sin(rad)
    end_y = center - arrow_length * math.cos(rad)
    
    # 绘制箭头线
    draw.line([(center, center), (end_x, end_y)], 
              fill=(255, 100, 100, 200), width=4)
    
    # 绘制箭头头部
    arrow_head_size = 10
    angle = math.radians(direction_angle)
    
    # 箭头头部的两个点
    head_angle1 = angle + math.radians(150)
    head_angle2 = angle + math.radians(210)
    
    head_x1 = end_x - arrow_head_size * math.cos(head_angle1)
    head_y1 = end_y + arrow_head_size * math.sin(head_angle1)
    head_x2 = end_x - arrow_head_size * math.cos(head_angle2)
    head_y2 = end_y + arrow_head_size * math.sin(head_angle2)
    
    draw.polygon([(end_x, end_y), (head_x1, head_y1), (head_x2, head_y2)],
                fill=(255, 100, 100, 200))
    
    return img


def display_compass(heading: float, key: str = "compass"):
    """
    在Streamlit中显示指南针
    
    Args:
        heading: 当前朝向角度
        key: Streamlit组件key
    """
    compass_img = create_compass_image(heading)
    st.image(compass_img, caption=f"当前朝向: {heading}°", width="content")


def display_direction_indicator(direction_angle: float, label: str = ""):
    """
    显示方向指示器
    
    Args:
        direction_angle: 方向角度
        label: 标签文字
    """
    arrow_img = create_direction_arrow(direction_angle)
    st.image(arrow_img, caption=label if label else f"方向: {direction_angle}°", 
             width="content")


def create_navigation_card(instruction: Dict) -> str:
    """
    创建导航卡片HTML
    
    Args:
        instruction: 导航指令字典
    
    Returns:
        HTML字符串
    """
    direction = instruction.get('direction', {})
    
    html = f"""
    <div style="
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        padding: 15px;
        color: white;
        margin: 10px 0;
    ">
        <div style="font-size: 18px; font-weight: bold; margin-bottom: 10px;">
            🧭 {instruction.get('from', '')} → {instruction.get('to', '')}
        </div>
        <div style="font-size: 24px; margin: 10px 0;">
            {direction.get('cardinal', '')} ({direction.get('relative', '')})
        </div>
        <div style="font-size: 14px; opacity: 0.9;">
            距离: {direction.get('distance', 0):.1f}米 | 
            角度: {direction.get('angle', 0):.1f}°
        </div>
    </div>
    """
    
    return html


# 测试代码
if __name__ == "__main__":
    print("生成指南针测试图像...")
    
    # 测试不同朝向
    test_headings = [0, 45, 90, 180, 270]
    
    for heading in test_headings:
        img = create_compass_image(heading)
        img.save(f"compass_{heading}.png")
        print(f"  ✓ 生成指南针图像: compass_{heading}.png")
    
    # 测试方向箭头
    arrow = create_direction_arrow(45)
    arrow.save("direction_arrow.png")
    print("  ✓ 生成方向箭头: direction_arrow.png")
    
    print("\n完成！")

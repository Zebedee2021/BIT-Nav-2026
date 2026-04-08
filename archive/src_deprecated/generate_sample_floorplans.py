"""
生成示例楼层平面图
用于演示和测试
元素位置基于 wencui_building.json 中的逻辑坐标，
与 floorplan_visualizer.py 的坐标映射保持一致。
"""

from PIL import Image, ImageDraw, ImageFont
import os
import json


# 逻辑坐标空间大小
LOGICAL_W = 200
LOGICAL_H = 200


def _load_fonts():
    """加载中文字体"""
    try:
        title_font = ImageFont.truetype(r"C:\Windows\Fonts\simhei.ttf", 24)
        label_font = ImageFont.truetype(r"C:\Windows\Fonts\simhei.ttf", 14)
        small_font = ImageFont.truetype(r"C:\Windows\Fonts\simhei.ttf", 11)
    except:
        try:
            title_font = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 24)
            label_font = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 14)
            small_font = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 11)
        except:
            title_font = ImageFont.load_default()
            label_font = ImageFont.load_default()
            small_font = ImageFont.load_default()
    return title_font, label_font, small_font


def _to_pixel(lx, ly, img_w, img_h):
    """逻辑坐标 → 像素坐标（与 create_matplotlib_visualization 一致）"""
    return int(lx / LOGICAL_W * img_w), int(ly / LOGICAL_H * img_h)


def generate_floorplan(floor: str, building_data: dict,
                       width: int = 800, height: int = 600) -> Image.Image:
    """基于建筑数据坐标生成楼层平面图"""

    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    title_font, label_font, small_font = _load_fonts()

    floor_names = {
        "1F": "一层 - 入口层", "2F": "二层 - 教学区",
        "3F": "三层 - 实验区", "4F": "四层 - 办公区",
        "5F": "五层 - 研究区", "6F": "六层 - 研讨区",
        "7F": "七层 - 信息技术区", "8F": "八层 - 学生活动区",
        "9F": "九层 - 行政管理区", "10F": "十层 - 综合服务区",
    }

    # 标题
    title = f"文萃楼 {floor_names.get(floor, floor)} 平面图"
    draw.text((width // 2 - 150, 10), title, fill='black', font=title_font)

    # 建筑外框（逻辑 5~195 映射到像素）
    bx1, by1 = _to_pixel(5, 10, width, height)
    bx2, by2 = _to_pixel(195, 190, width, height)
    draw.rectangle([bx1, by1, bx2, by2], outline='black', width=3)

    # 颜色与尺寸
    type_styles = {
        "entrance":  {"fill": "green",      "size": (30, 10), "text_color": "white"},
        "corridor":  {"fill": "lightblue",  "size": (50, 30), "text_color": "black"},
        "stairs":    {"fill": "orange",      "size": (25, 25), "text_color": "black"},
        "elevator":  {"fill": "purple",      "size": (25, 25), "text_color": "white"},
        "room":      {"fill": "lightyellow", "size": (40, 35), "text_color": "black"},
    }

    # 筛选该楼层节点
    nodes = building_data.get("nodes", {})
    floor_nodes = {nid: n for nid, n in nodes.items() if n.get("floor") == floor}

    for node_id, node in floor_nodes.items():
        lx, ly = node["x"], node["y"]
        cx, cy = _to_pixel(lx, ly, width, height)

        style = type_styles.get(node["type"], type_styles["room"])
        half_w, half_h = style["size"]

        # 绘制矩形
        rect = [cx - half_w, cy - half_h, cx + half_w, cy + half_h]
        outline_width = 3 if node["type"] == "room" else 1
        draw.rectangle(rect, fill=style["fill"], outline='black', width=outline_width)

        # 节点名称
        name = node.get("name", node_id)
        draw.text((cx - half_w + 4, cy - 8), name, fill=style["text_color"], font=small_font)

        # 房间额外显示描述
        if node["type"] == "room" and node.get("description"):
            draw.text((cx - half_w + 4, cy + 5), node["description"],
                      fill='gray', font=small_font)

    # 绘制边（该楼层内的连线）
    edges = building_data.get("edges", [])
    for n1_id, n2_id in edges:
        n1 = nodes.get(n1_id)
        n2 = nodes.get(n2_id)
        if n1 and n2 and n1.get("floor") == floor and n2.get("floor") == floor:
            p1 = _to_pixel(n1["x"], n1["y"], width, height)
            p2 = _to_pixel(n2["x"], n2["y"], width, height)
            draw.line([p1, p2], fill='#CCCCCC', width=2)

    # 图例
    legend_y = height - 35
    legend_items = [
        ("green", "入口"), ("lightyellow", "教室"),
        ("orange", "楼梯"), ("purple", "电梯"), ("lightblue", "走廊"),
    ]
    lx_pos = 20
    for color, label in legend_items:
        draw.rectangle([lx_pos, legend_y, lx_pos + 15, legend_y + 15],
                       fill=color, outline='black')
        draw.text((lx_pos + 20, legend_y), label, fill='black', font=small_font)
        lx_pos += 80

    draw.text((width - 200, height - 18), "示例平面图 - 仅供演示",
              fill='gray', font=small_font)

    return img


def generate_overview(width: int = 800, height: int = 600) -> Image.Image:
    """生成文萃楼总览图"""
    
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    
    try:
        title_font = ImageFont.truetype(r"C:\Windows\Fonts\simhei.ttf", 24)
        label_font = ImageFont.truetype(r"C:\Windows\Fonts\simhei.ttf", 14)
        small_font = ImageFont.truetype(r"C:\Windows\Fonts\simhei.ttf", 11)
    except:
        title_font = ImageFont.load_default()
        label_font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    
    # 标题
    draw.text((width//2 - 120, 15), "文萃楼 整体布局概览", fill='black', font=title_font)
    
    # 建筑外框
    bx, by, bw, bh = 150, 60, 500, 480
    draw.rectangle([bx, by, bx+bw, by+bh], outline='black', width=3)
    draw.text((bx + bw//2 - 30, by + 5), "文萃楼", fill='black', font=label_font)
    
    # 楼层示意（从下到上）
    floor_labels = {
        "1F": ("一层 - 入口层", "#A5D6A7"),
        "2F": ("二层 - 教学区", "#90CAF9"),
        "3F": ("三层 - 实验区", "#CE93D8"),
        "4F": ("四层 - 办公区", "#FFAB91"),
        "5F": ("五层 - 研究区", "#FFF59D"),
        "6F": ("六层 - 研讨区", "#B2DFDB"),
        "7F": ("七层 - 信息技术区", "#F0F4C3"),
        "8F": ("八层 - 学生活动区", "#D1C4E9"),
        "9F": ("九层 - 行政管理区", "#FFCCBC"),
        "10F": ("十层 - 综合服务区", "#CFD8DC"),
    }
    
    floors = list(floor_labels.items())
    floor_h = 38
    gap = 4
    start_y = by + bh - 30 - floor_h
    
    for i, (floor_id, (label, color)) in enumerate(floors):
        fy = start_y - i * (floor_h + gap)
        fx = bx + 30
        fw = bw - 60
        draw.rectangle([fx, fy, fx+fw, fy+floor_h], fill=color, outline='black')
        draw.text((fx + 10, fy + 10), f"{floor_id}  {label}", fill='black', font=small_font)
    
    # 入口标注
    # 东门（上方）
    draw.rectangle([bx + bw//2 - 25, by - 5, bx + bw//2 + 25, by + 5], fill='green', outline='black')
    draw.text((bx + bw//2 - 15, by - 22), "东门", fill='black', font=label_font)
    
    # 西门（下方）
    draw.rectangle([bx + bw//2 - 25, by + bh - 5, bx + bw//2 + 25, by + bh + 5], fill='green', outline='black')
    draw.text((bx + bw//2 - 15, by + bh + 10), "西门", fill='black', font=label_font)
    
    # 图例
    ly = height - 45
    draw.rectangle([20, ly, 40, ly+15], fill='#A5D6A7', outline='black')
    draw.text((45, ly), "入口层", fill='black', font=small_font)
    draw.rectangle([110, ly, 130, ly+15], fill='#90CAF9', outline='black')
    draw.text((135, ly), "教学区", fill='black', font=small_font)
    draw.rectangle([200, ly, 220, ly+15], fill='#CE93D8', outline='black')
    draw.text((225, ly), "实验区", fill='black', font=small_font)
    draw.rectangle([290, ly, 310, ly+15], fill='#FFAB91', outline='black')
    draw.text((315, ly), "办公区", fill='black', font=small_font)
    draw.rectangle([380, ly, 400, ly+15], fill='#FFF59D', outline='black')
    draw.text((405, ly), "研究区", fill='black', font=small_font)
    
    draw.text((20, height-20), "示例总览图 - 仅供演示", fill='gray', font=small_font)
    
    return img


def main():
    """生成所有楼层的示例平面图"""
    
    # 获取项目根目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    output_dir = os.path.join(project_root, "data", "floorplans")
    
    # 加载建筑数据
    building_path = os.path.join(project_root, "data", "wencui_building.json")
    with open(building_path, 'r', encoding='utf-8') as f:
        building_data = json.load(f)
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 生成总览图
    overview_img = generate_overview()
    overview_path = os.path.join(output_dir, "overview.png")
    overview_img.save(overview_path, "PNG")
    print(f"  ✓ 生成: {overview_path}")
    
    # 生成所有楼层的平面图
    floors = building_data["building"]["floors"]
    
    print("生成示例楼层平面图...")
    for floor in floors:
        img = generate_floorplan(floor, building_data)
        output_path = os.path.join(output_dir, f"{floor}.png")
        img.save(output_path, "PNG")
        print(f"  ✓ 生成: {output_path}")
    
    print(f"\n完成！共生成 {len(floors) + 1} 个平面图（含总览图）")
    print(f"输出目录: {output_dir}")


if __name__ == "__main__":
    main()

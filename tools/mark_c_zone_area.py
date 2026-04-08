"""
在1F原图上标记C区范围

使用方法:
  python tools/mark_c_zone_area.py
"""

import cv2
import os


def mark_c_zone_area():
    """在1F楼层图上标记C区范围"""
    
    # 加载1F楼层图
    floorplan_path = os.path.join(
        os.path.dirname(__file__), '..', 'data', 'floorplans', '1F_official.jpg'
    )
    img = cv2.imread(floorplan_path)
    
    # 根据观察，C区在右侧偏上位置
    # 让我标记出C区的大致范围（浅绿色区域）
    
    # C区范围（基于视觉观察的像素坐标）
    # 左上角和右下角
    c_zone_top_left = (2450, 250)
    c_zone_bottom_right = (2750, 1300)
    
    # 创建可视化图像
    vis_img = img.copy()
    
    # 绘制C区边界框（红色粗线）
    cv2.rectangle(vis_img, c_zone_top_left, c_zone_bottom_right, (0, 0, 255), 4)
    
    # 添加C区标签
    cv2.putText(vis_img, "C ZONE", (c_zone_top_left[0], c_zone_top_left[1] - 20),
               cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
    
    # 在C区内部标记房间位置（估算）
    # 根据楼层图，C区似乎有多个房间块
    # 让我标记出可能的房间位置
    
    # 从图中观察，C区似乎有纵向排列的房间
    # 但我需要确认具体的房间编号和位置
    
    # 添加提示文字
    info_text = [
        "请确认C区的实际范围",
        "以及C-101到C-109的具体位置",
        "红色框为估算的C区范围"
    ]
    
    y_offset = 100
    for i, text in enumerate(info_text):
        cv2.putText(vis_img, text, (50, y_offset + i * 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    
    # 保存
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'visualizations')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, '1F_C_zone_area_marked.jpg')
    
    cv2.imwrite(output_path, vis_img)
    print(f"C区范围标记图已保存: {output_path}")
    
    return output_path


if __name__ == '__main__':
    mark_c_zone_area()
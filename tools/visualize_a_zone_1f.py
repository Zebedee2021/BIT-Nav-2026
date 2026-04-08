"""
1F A区房间位置可视化

标记1F楼层图上A区的房间位置
"""

import cv2
import json
import os

# 加载1F楼层图
floorplan_path = os.path.join(os.path.dirname(__file__), '..', 'wencui', '1.jpg')
img = cv2.imread(floorplan_path)

# 根据1F图观察，A区位于顶部中央区域
# 从图上看，A区有多个房间横向排列

# A区1F房间坐标（基于图像观察估算）
# A区位于图的顶部中央，绿色区域（从图例看A区是浅绿色）
# 根据1F图，A区在中央顶部，横向排列
a_zone_rooms_1f = [
    # 上层房间（从右到左）- 位于图中央顶部绿色区域
    ('A-101', 1520, 130), ('A-102', 1470, 130), ('A-103', 1420, 130),
    ('A-104', 1370, 130), ('A-105', 1320, 130), ('A-106', 1270, 130),
    ('A-107', 1220, 130), ('A-108', 1170, 130), ('A-109', 1120, 130),
    # 下层房间
    ('A-110', 1520, 180), ('A-111', 1470, 180), ('A-112', 1420, 180),
    ('A-113', 1370, 180), ('A-114', 1320, 180), ('A-115', 1270, 180),
    ('A-116', 1220, 180), ('A-117', 1170, 180), ('A-118', 1120, 180),
]

# 绘制A区房间位置
for room_id, x, y in a_zone_rooms_1f:
    # 绘制圆点
    cv2.circle(img, (x, y), 8, (0, 0, 255), -1)  # 红色填充
    cv2.circle(img, (x, y), 8, (255, 255, 255), 2)  # 白色边框
    
    # 绘制房间编号
    cv2.putText(img, room_id, (x + 10, y), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

# 添加标题
cv2.putText(img, "1F A Zone Rooms", (50, 50), 
            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)

# 保存可视化结果
output_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'visualizations', '1F_A_zone_marked.jpg')
os.makedirs(os.path.dirname(output_path), exist_ok=True)
cv2.imwrite(output_path, img)

print(f"1F A区房间位置已标记")
print(f"保存路径: {output_path}")
print(f"\n标记的房间:")
for room_id, x, y in a_zone_rooms_1f:
    print(f"  {room_id}: ({x}, {y})")

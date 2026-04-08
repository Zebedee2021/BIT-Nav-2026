"""
楼层图对齐标准化处理
以 L-201/L-401/L-501/L-601/L-701/L-801/L-901/L-1001 为参考点进行垂直对齐
"""

import cv2
import numpy as np
import json
import os
from typing import Dict, Tuple, Optional
from PIL import Image


# 参考房间坐标（从 wencui_building.json 提取）
# 所有 L-xxx01 房间的原始坐标都是 (108, 238)
REFERENCE_ROOMS = {
    "2F": {"room": "L-201", "x": 108, "y": 238},
    "3F": {"room": "L-301", "x": 108, "y": 238},  # 假设与2F一致
    "4F": {"room": "L-401", "x": 108, "y": 238},
    "5F": {"room": "L-501", "x": 108, "y": 238},
    "6F": {"room": "L-601", "x": 108, "y": 238},
    "7F": {"room": "L-701", "x": 108, "y": 238},
    "8F": {"room": "L-801", "x": 108, "y": 238},
    "9F": {"room": "L-901", "x": 108, "y": 238},
    "10F": {"room": "L-1001", "x": 108, "y": 238},
}

# 1F 的 L-101 坐标不同，单独处理
REFERENCE_ROOMS["1F"] = {"room": "L-101", "x": 108, "y": 238}


def detect_content_bounds(image: np.ndarray, threshold: int = 240) -> Tuple[int, int, int, int]:
    """
    检测图片内容边界（去除白色边框）
    
    Returns:
        (left, top, right, bottom)
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    
    h, w = gray.shape
    
    # 计算每行的内容密度
    row_content = []
    for y in range(h):
        row = gray[y, :]
        density = np.sum(row < threshold) / w
        row_content.append(density)
    
    # 计算每列的内容密度
    col_content = []
    for x in range(w):
        col = gray[:, x]
        density = np.sum(col < threshold) / h
        col_content.append(density)
    
    # 找到边界（从中间向两边搜索）
    center_y = h // 2
    top = 0
    for y in range(center_y, -1, -1):
        if row_content[y] < 0.02:
            top = y
            break
    
    bottom = h
    for y in range(center_y, h):
        if row_content[y] < 0.02:
            bottom = y
            break
    
    center_x = w // 2
    left = 0
    for x in range(center_x, -1, -1):
        if col_content[x] < 0.02:
            left = x
            break
    
    right = w
    for x in range(center_x, w):
        if col_content[x] < 0.02:
            right = x
            break
    
    return (left, top, right, bottom)


def align_floorplan(
    input_path: str,
    output_path: str,
    floor: str,
    target_ref_point: Tuple[int, int] = (100, 200),
    target_size: Tuple[int, int] = (1400, 1000)
) -> Optional[Dict]:
    """
    对齐单个楼层图
    
    Args:
        input_path: 输入图片路径
        output_path: 输出图片路径
        floor: 楼层标识
        target_ref_point: 参考点在目标图中的位置 (x, y)
        target_size: 目标尺寸
        
    Returns:
        转换参数字典
    """
    # 读取图片
    img = cv2.imread(input_path)
    if img is None:
        print(f"无法读取图片: {input_path}")
        return None
    
    original_h, original_w = img.shape[:2]
    print(f"原始尺寸: {original_w}x{original_h}")
    
    # 检测内容边界
    left, top, right, bottom = detect_content_bounds(img)
    print(f"内容边界: 左={left}, 上={top}, 右={right}, 下={bottom}")
    
    # 获取该楼层的参考点
    ref = REFERENCE_ROOMS.get(floor)
    if not ref:
        print(f"警告: 未找到 {floor} 的参考点")
        return None
    
    ref_x, ref_y = ref["x"], ref["y"]
    print(f"参考房间: {ref['room']} 原始坐标=({ref_x}, {ref_y})")
    
    # 计算缩放比例（基于内容区域宽度）
    content_width = right - left
    content_height = bottom - top
    
    # 目标：让参考点在标准化图中的位置一致
    # 计算需要的缩放比例
    # 假设参考点距离左边界 ref_x - left，距离上边界 ref_y - top
    
    # 为了对齐，我们需要：
    # 1. 所有楼层参考点映射到相同的 target_ref_point
    # 2. 使用统一的缩放比例
    
    # 计算基于参考点的缩放比例
    # 让内容区域在目标图中居中且对齐
    scale_x = (target_size[0] - 200) / content_width  # 留边距
    scale_y = (target_size[1] - 200) / content_height
    scale = min(scale_x, scale_y)
    
    print(f"缩放比例: {scale:.4f}")
    
    # 计算偏移量，使参考点对齐
    # ref_x * scale + offset_x = target_ref_point[0]
    offset_x = target_ref_point[0] - ref_x * scale
    offset_y = target_ref_point[1] - ref_y * scale
    
    print(f"偏移量: ({offset_x:.1f}, {offset_y:.1f})")
    
    # 创建变换矩阵
    # 缩放 + 平移
    M = np.float32([
        [scale, 0, offset_x],
        [0, scale, offset_y]
    ])
    
    # 应用变换
    aligned = cv2.warpAffine(img, M, target_size, 
                             borderValue=(255, 255, 255),
                             flags=cv2.INTER_LANCZOS4)
    
    # 保存结果
    cv2.imwrite(output_path, aligned, [cv2.IMWRITE_JPEG_QUALITY, 95])
    print(f"已保存: {output_path} ({target_size[0]}x{target_size[1]})")
    
    # 验证参考点位置
    ref_aligned_x = ref_x * scale + offset_x
    ref_aligned_y = ref_y * scale + offset_y
    print(f"参考点对齐后位置: ({ref_aligned_x:.1f}, {ref_aligned_y:.1f})")
    
    return {
        "original_size": (original_w, original_h),
        "content_bounds": (left, top, right, bottom),
        "reference": ref,
        "scale": scale,
        "offset": (offset_x, offset_y),
        "target_size": target_size,
        "target_ref_point": target_ref_point
    }


def batch_align(
    input_dir: str,
    output_dir: str,
    target_size: Tuple[int, int] = (1400, 1000),
    target_ref_point: Tuple[int, int] = (100, 200)
):
    """
    批量对齐楼层图
    """
    os.makedirs(output_dir, exist_ok=True)
    
    transform_params = {}
    
    floors = ["1F", "2F", "3F", "4F", "5F", "6F", "7F", "8F", "9F", "10F"]
    
    print("=" * 60)
    print("楼层图对齐标准化处理")
    print(f"目标尺寸: {target_size}")
    print(f"参考点对齐位置: {target_ref_point}")
    print("=" * 60)
    
    for floor in floors:
        input_file = os.path.join(input_dir, f"{floor}_official.jpg")
        
        if not os.path.exists(input_file):
            print(f"\n跳过 {floor}: 文件不存在")
            continue
        
        print(f"\n处理 {floor}...")
        output_file = os.path.join(output_dir, f"{floor}_aligned.jpg")
        
        params = align_floorplan(input_file, output_file, floor, target_ref_point, target_size)
        
        if params:
            transform_params[floor] = params
    
    # 保存参数
    params_file = os.path.join(output_dir, "align_params.json")
    with open(params_file, 'w', encoding='utf-8') as f:
        json.dump(transform_params, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'=' * 60}")
    print(f"对齐参数已保存: {params_file}")
    print("=" * 60)
    
    # 验证对齐结果
    print("\n验证对齐结果（参考点位置）：")
    for floor, params in transform_params.items():
        ref = params["reference"]
        scale = params["scale"]
        offset_x, offset_y = params["offset"]
        aligned_x = ref["x"] * scale + offset_x
        aligned_y = ref["y"] * scale + offset_y
        print(f"  {floor} {ref['room']}: ({aligned_x:.1f}, {aligned_y:.1f})")
    
    return transform_params


if __name__ == "__main__":
    import sys
    
    input_dir = "../data/floorplans"
    output_dir = "../data/floorplans_aligned"
    
    if len(sys.argv) > 1:
        input_dir = sys.argv[1]
    if len(sys.argv) > 2:
        output_dir = sys.argv[2]
    
    # 批量对齐
    params = batch_align(input_dir, output_dir)
    
    print("\n处理完成!")
    print(f"对齐后的图片保存在: {output_dir}")

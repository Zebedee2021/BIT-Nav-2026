"""
楼层图标准化处理工具
- 裁剪空白边
- 统一尺寸
- 保持坐标比例
"""

import cv2
import numpy as np
from PIL import Image
import os
from typing import Tuple, Optional


def crop_to_content_area(
    image: np.ndarray,
    min_content_density: float = 0.05,
    padding: int = 10
) -> Tuple[np.ndarray, Tuple[int, int, int, int]]:
    """
    裁剪图片到内容区域（去除白色/浅色边框）
    
    通过分析每行每列的内容密度，找到实际的色区边界
    
    Args:
        image: 输入图片 (BGR格式)
        min_content_density: 内容密度阈值（低于此值视为空白）
        padding: 保留的边距
        
    Returns:
        (裁剪后的图片, (x, y, w, h) 裁剪区域)
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    
    h, w = gray.shape
    
    # 计算每行的内容密度
    row_density = []
    for y in range(h):
        row = gray[y, :]
        # 非白色像素比例（白色阈值 240）
        density = np.sum(row < 240) / w
        row_density.append(density)
    
    # 计算每列的内容密度
    col_density = []
    for x in range(w):
        col = gray[:, x]
        density = np.sum(col < 240) / h
        col_density.append(density)
    
    # 找到上下边界（从中间向两边搜索，避免顶部/底部的小噪声）
    center_y = h // 2
    top = 0
    for y in range(center_y, -1, -1):
        if row_density[y] < min_content_density:
            top = min(h, y + padding)
            break
    
    bottom = h
    for y in range(center_y, h):
        if row_density[y] < min_content_density:
            bottom = max(0, y - padding)
            break
    
    # 找到左右边界
    center_x = w // 2
    left = 0
    for x in range(center_x, -1, -1):
        if col_density[x] < min_content_density:
            left = min(w, x + padding)
            break
    
    right = w
    for x in range(center_x, w):
        if col_density[x] < min_content_density:
            right = max(0, x - padding)
            break
    
    # 确保有效区域
    if right <= left or bottom <= top:
        print(f"警告: 未找到有效内容区域，使用原图")
        return image, (0, 0, w, h)
    
    # 裁剪
    cropped = image[top:bottom, left:right]
    
    return cropped, (left, top, right - left, bottom - top)


def standardize_floorplan_v2(
    input_path: str,
    output_path: str,
    target_size: Tuple[int, int] = (1400, 1000),
    maintain_aspect: bool = True
) -> Optional[Dict]:
    """
    标准化楼层图 V2 - 裁剪到色区边界，统一尺寸
    
    Args:
        input_path: 输入图片路径
        output_path: 输出图片路径
        target_size: 目标尺寸 (width, height)
        maintain_aspect: 是否保持宽高比
        
    Returns:
        坐标转换参数字典
    """
    # 读取图片
    img = cv2.imread(input_path)
    if img is None:
        print(f"无法读取图片: {input_path}")
        return None
    
    original_h, original_w = img.shape[:2]
    print(f"原始尺寸: {original_w}x{original_h}")
    
    # 裁剪到内容区域（去除白色边框）
    content_img, crop_box = crop_to_content_area(img)
    crop_x, crop_y, crop_w, crop_h = crop_box
    
    print(f"裁剪区域: ({crop_x}, {crop_y}, {crop_w}, {crop_h})")
    print(f"内容尺寸: {crop_w}x{crop_h}")
    
    # 目标尺寸
    target_w, target_h = target_size
    
    if maintain_aspect:
        # 保持宽高比，缩放以适应目标尺寸
        scale = min(target_w / crop_w, target_h / crop_h)
        new_w = int(crop_w * scale)
        new_h = int(crop_h * scale)
        
        # 缩放
        resized = cv2.resize(content_img, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
        
        # 创建目标尺寸画布（白色背景）
        result = np.ones((target_h, target_w, 3), dtype=np.uint8) * 255
        
        # 居中放置
        offset_x = (target_w - new_w) // 2
        offset_y = (target_h - new_h) // 2
        result[offset_y:offset_y+new_h, offset_x:offset_x+new_w] = resized
        
        print(f"缩放比例: {scale:.3f}, 放置位置: ({offset_x}, {offset_y})")
        
        # 坐标转换参数
        params = {
            "original_size": (original_w, original_h),
            "crop_box": crop_box,
            "scale": scale,
            "offset": (offset_x, offset_y),
            "target_size": target_size
        }
        
    else:
        # 直接拉伸到目标尺寸
        result = cv2.resize(content_img, target_size, interpolation=cv2.INTER_LANCZOS4)
        
        params = {
            "original_size": (original_w, original_h),
            "crop_box": crop_box,
            "scale_x": target_w / crop_w,
            "scale_y": target_h / crop_h,
            "target_size": target_size
        }
    
    # 保存结果
    cv2.imwrite(output_path, result, [cv2.IMWRITE_JPEG_QUALITY, 95])
    print(f"已保存: {output_path} ({result.shape[1]}x{result.shape[0]})")
    
    return params


def transform_coordinates_v2(
    x: float,
    y: float,
    params: Dict
) -> Tuple[float, float]:
    """
    将原始坐标转换为标准化后的坐标
    
    Args:
        x, y: 原始坐标
        params: 转换参数
        
    Returns:
        转换后的坐标 (x', y')
    """
    # 裁剪偏移
    crop_x, crop_y = params["crop_box"][0], params["crop_box"][1]
    
    # 相对坐标（相对于裁剪后的内容区域）
    x_rel = x - crop_x
    y_rel = y - crop_y
    
    # 缩放
    if "scale" in params:
        # 等比例缩放
        scale = params["scale"]
        offset_x, offset_y = params["offset"]
        x_new = x_rel * scale + offset_x
        y_new = y_rel * scale + offset_y
    else:
        # 非等比例
        x_new = x_rel * params["scale_x"]
        y_new = y_rel * params["scale_y"]
    
    return (x_new, y_new)


def standardize_floorplan(
    input_path: str,
    output_path: str,
    target_size: Tuple[int, int] = (1920, 1080),
    maintain_aspect: bool = True
) -> Optional[Tuple[float, float, float, float]]:
    """
    标准化楼层图
    
    Args:
        input_path: 输入图片路径
        output_path: 输出图片路径
        target_size: 目标尺寸 (width, height)
        maintain_aspect: 是否保持宽高比
        
    Returns:
        缩放和偏移信息 (scale_x, scale_y, offset_x, offset_y) 用于坐标转换
    """
    # 读取图片
    img = cv2.imread(input_path)
    if img is None:
        print(f"无法读取图片: {input_path}")
        return None
    
    original_h, original_w = img.shape[:2]
    print(f"原始尺寸: {original_w}x{original_h}")
    
    # 检测内容区域
    x, y, w, h = detect_content_region(img)
    print(f"内容区域: ({x}, {y}, {w}, {h})")
    
    # 裁剪内容区域
    content = img[y:y+h, x:x+w]
    
    # 计算缩放比例
    target_w, target_h = target_size
    
    if maintain_aspect:
        # 保持宽高比，填充黑边
        scale = min(target_w / w, target_h / h)
        new_w = int(w * scale)
        new_h = int(h * scale)
        
        # 缩放内容
        resized = cv2.resize(content, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
        
        # 创建目标尺寸画布（白色背景）
        result = np.ones((target_h, target_w, 3), dtype=np.uint8) * 255
        
        # 居中放置
        offset_x = (target_w - new_w) // 2
        offset_y = (target_h - new_h) // 2
        result[offset_y:offset_y+new_h, offset_x:offset_x+new_w] = resized
        
        # 计算坐标转换参数
        # 原始坐标 -> 标准化坐标
        scale_x = scale
        scale_y = scale
        # 裁剪偏移 + 居中偏移
        offset_x_total = offset_x - x * scale
        offset_y_total = offset_y - y * scale
        
    else:
        # 不保持宽高比，直接拉伸
        result = cv2.resize(content, target_size, interpolation=cv2.INTER_LANCZOS4)
        scale_x = target_w / w
        scale_y = target_h / h
        offset_x_total = -x * scale_x
        offset_y_total = -y * scale_y
    
    # 保存结果
    cv2.imwrite(output_path, result, [cv2.IMWRITE_JPEG_QUALITY, 95])
    print(f"已保存: {output_path} ({target_w}x{target_h})")
    
    return (scale_x, scale_y, offset_x_total, offset_y_total)


def batch_standardize(
    input_dir: str,
    output_dir: str,
    target_size: Tuple[int, int] = (1400, 1000),
    suffix: str = "_standardized"
):
    """
    批量标准化楼层图（裁剪到色区边界版）
    
    Args:
        input_dir: 输入目录
        output_dir: 输出目录
        target_size: 目标尺寸 (width, height)
        suffix: 输出文件名后缀
    """
    import json
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 存储坐标转换参数
    transform_params = {}
    
    # 处理所有楼层图
    floors = ["1F", "2F", "3F", "4F", "5F", "6F", "7F", "8F", "9F", "10F", "overview"]
    
    for floor in floors:
        input_file = os.path.join(input_dir, f"{floor}_official.jpg")
        
        if not os.path.exists(input_file):
            print(f"跳过 {floor}: 文件不存在")
            continue
        
        print(f"\n处理 {floor}...")
        output_file = os.path.join(output_dir, f"{floor}{suffix}.jpg")
        
        params = standardize_floorplan_v2(input_file, output_file, target_size)
        
        if params:
            transform_params[floor] = params
    
    # 保存坐标转换参数
    params_file = os.path.join(output_dir, "transform_params.json")
    with open(params_file, 'w', encoding='utf-8') as f:
        json.dump(transform_params, f, ensure_ascii=False, indent=2)
    
    print(f"\n坐标转换参数已保存: {params_file}")
    return transform_params


def visualize_standardization(
    original_path: str,
    standardized_path: str,
    output_path: str
):
    """
    可视化标准化前后的对比
    """
    import matplotlib.pyplot as plt
    
    orig = cv2.imread(original_path)
    orig = cv2.cvtColor(orig, cv2.COLOR_BGR2RGB)
    
    std = cv2.imread(standardized_path)
    std = cv2.cvtColor(std, cv2.COLOR_BGR2RGB)
    
    fig, axes = plt.subplots(1, 2, figsize=(16, 8))
    
    axes[0].imshow(orig)
    axes[0].set_title(f"Original\n{orig.shape[1]}x{orig.shape[0]}")
    axes[0].axis('off')
    
    axes[1].imshow(std)
    axes[1].set_title(f"Standardized\n{std.shape[1]}x{std.shape[0]}")
    axes[1].axis('off')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"对比图已保存: {output_path}")


if __name__ == "__main__":
    import sys
    
    # 默认参数
    input_dir = "../data/floorplans"
    output_dir = "../data/floorplans_standardized"
    target_size = (1400, 1000)  # 统一目标尺寸
    
    if len(sys.argv) > 1:
        input_dir = sys.argv[1]
    if len(sys.argv) > 2:
        output_dir = sys.argv[2]
    
    print("楼层图标准化处理（裁剪到色区边界版）")
    print(f"输入目录: {input_dir}")
    print(f"输出目录: {output_dir}")
    print(f"目标尺寸: {target_size}")
    print("-" * 50)
    
    # 批量处理
    params = batch_standardize(input_dir, output_dir, target_size)
    
    # 生成对比图（以4F为例）
    if os.path.exists(os.path.join(input_dir, "4F_official.jpg")):
        print("\n生成对比图...")
        visualize_standardization(
            os.path.join(input_dir, "4F_official.jpg"),
            os.path.join(output_dir, "4F_standardized.jpg"),
            os.path.join(output_dir, "comparison_4F.jpg")
        )
    
    print("\n处理完成!")
    print(f"标准化后的图片保存在: {output_dir}")
    print("注意: 使用标准化图片后，需要更新坐标转换参数!")

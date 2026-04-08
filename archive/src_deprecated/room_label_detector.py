"""
房间编号识别器 - 从楼层图提取房间标签位置
使用 OCR 识别房间编号（如 L-101）并获取其中心坐标
"""

import cv2
import numpy as np
from PIL import Image
from typing import List, Dict, Tuple, Optional
import os


class RoomLabelDetector:
    """房间标签检测器 - 基于图像处理识别房间编号"""
    
    def __init__(self):
        self.debug = False
    
    def detect_labels_from_image(self, image_path: str, zone_prefix: str = None) -> List[Dict]:
        """
        从楼层图图片中检测房间标签位置
        
        Args:
            image_path: 楼层图图片路径
            zone_prefix: 区域前缀（如 "L"、"D"），用于过滤
            
        Returns:
            检测到的标签列表，每项包含：
            - text: 识别的文字（如 "L-101"）
            - center: 中心坐标 (x, y)
            - bbox: 边界框 (x, y, w, h)
            - confidence: 置信度
        """
        # 读取图片
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"无法读取图片: {image_path}")
        
        height, width = img.shape[:2]
        
        # 转换为灰度图
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 使用阈值处理提取文字区域
        # 房间编号通常是深色文字在浅色背景上
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # 形态学操作，连接文字区域
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 5))
        dilated = cv2.dilate(binary, kernel, iterations=2)
        
        # 查找轮廓
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        detected_labels = []
        
        for contour in contours:
            # 获取边界框
            x, y, w, h = cv2.boundingRect(contour)
            
            # 过滤太小或太大的区域（房间编号的大小范围）
            if w < 20 or h < 10 or w > 200 or h > 100:
                continue
            
            # 计算中心点
            center_x = x + w // 2
            center_y = y + h // 2
            
            # 提取该区域进行 OCR
            roi = gray[y:y+h, x:x+w]
            
            # 使用简单的字符识别（基于轮廓分析）
            text = self._recognize_text_simple(roi, zone_prefix)
            
            if text:
                detected_labels.append({
                    "text": text,
                    "center": (center_x, center_y),
                    "bbox": (x, y, w, h),
                    "confidence": 0.8  # 简化版本使用固定置信度
                })
        
        return detected_labels
    
    def _recognize_text_simple(self, roi: np.ndarray, zone_prefix: str = None) -> Optional[str]:
        """
        简化版文字识别
        实际项目中应该使用 Tesseract 或 PaddleOCR
        
        Args:
            roi: 文字区域图像
            zone_prefix: 期望的区域前缀
            
        Returns:
            识别的文字或 None
        """
        # 这里使用简化逻辑：根据区域特征匹配
        # 实际应该调用 OCR 引擎
        
        # 暂时返回模拟结果，实际使用时替换为真实 OCR
        # 例如：使用 pytesseract 或 paddleocr
        
        # 示例：如果区域大小符合房间编号特征，返回模拟值
        h, w = roi.shape
        aspect_ratio = w / h if h > 0 else 0
        
        # 房间编号通常是宽高比 2:1 到 4:1
        if 1.5 < aspect_ratio < 5:
            # 这里应该调用 OCR，暂时返回占位符
            return f"{zone_prefix or 'X'}-XXX" if zone_prefix else "UNKNOWN"
        
        return None
    
    def detect_with_easyocr(self, image_path: str, zone_prefix: str = None) -> List[Dict]:
        """
        使用 EasyOCR 进行文字识别（推荐，安装更简单）
        
        需要安装: pip install easyocr
        
        Args:
            image_path: 楼层图图片路径
            zone_prefix: 区域前缀过滤
            
        Returns:
            检测到的标签列表
        """
        try:
            import easyocr
        except ImportError:
            print("请先安装 EasyOCR: pip install easyocr")
            return []
        
        # 初始化 EasyOCR（支持英文和数字）
        reader = easyocr.Reader(['en'], gpu=False, verbose=False)
        
        # 读取图片
        result = reader.readtext(image_path)
        
        detected_labels = []
        
        for detection in result:
            bbox = detection[0]  # 边界框坐标 [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
            text = detection[1]  # 识别的文字
            confidence = detection[2]  # 置信度
            
            # 清理文字（去除空格）
            text = text.replace(" ", "").replace("-", "-").upper()
            
            # 过滤非房间编号
            if zone_prefix and not text.startswith(zone_prefix):
                continue
            
            # 检查是否符合房间编号格式
            if self._is_room_number(text):
                # 计算中心点
                x_coords = [p[0] for p in bbox]
                y_coords = [p[1] for p in bbox]
                center_x = sum(x_coords) / len(x_coords)
                center_y = sum(y_coords) / len(y_coords)
                
                detected_labels.append({
                    "text": text,
                    "center": (int(center_x), int(center_y)),
                    "bbox": bbox,
                    "confidence": confidence
                })
        
        return detected_labels
    
    def _is_room_number(self, text: str) -> bool:
        """
        检查文字是否符合房间编号格式
        如：L-101, D-402, A-201
        """
        import re
        # 匹配格式：字母-数字
        pattern = r'^[A-Z]-\d{3}$'
        return bool(re.match(pattern, text))
    
    def visualize_detection(self, image_path: str, labels: List[Dict], output_path: str = None):
        """
        可视化检测结果
        
        Args:
            image_path: 原始图片路径
            labels: 检测到的标签列表
            output_path: 输出图片路径
        """
        img = cv2.imread(image_path)
        
        for label in labels:
            center = label["center"]
            text = label["text"]
            
            # 绘制中心点
            cv2.circle(img, center, 5, (0, 0, 255), -1)
            
            # 绘制文字
            cv2.putText(img, text, (center[0] + 10, center[1]), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        if output_path:
            cv2.imwrite(output_path, img)
        
        return img
    
    def export_to_json(self, labels: List[Dict], floor: str, ref_size: Tuple[int, int]) -> Dict:
        """
        将检测结果导出为节点坐标格式
        
        Args:
            labels: 检测到的标签列表
            floor: 楼层（如 "4F"）
            ref_size: 参考尺寸 (width, height)
            
        Returns:
            节点数据字典
        """
        nodes = {}
        img_w, img_h = ref_size
        
        for label in labels:
            text = label["text"]
            center_x, center_y = label["center"]
            
            # 将像素坐标转换为逻辑坐标
            logic_x = center_x
            logic_y = center_y
            
            # 从房间编号提取区域
            zone = text.split('-')[0] if '-' in text else 'UNKNOWN'
            
            nodes[text] = {
                "id": text,
                "type": "room",
                "floor": floor,
                "zone": zone,
                "name": text,
                "description": f"{floor} {text} 房间",
                "x": logic_x,
                "y": logic_y
            }
        
        return nodes


def calibrate_room_coordinates(floorplan_dir: str, output_path: str = None):
    """
    校准所有楼层的房间坐标
    
    Args:
        floorplan_dir: 楼层图目录
        output_path: 输出文件路径
    """
    detector = RoomLabelDetector()
    
    all_nodes = {}
    
    # 处理每个楼层
    for floor in ["1F", "2F", "3F", "4F", "5F", "6F", "7F", "8F", "9F", "10F"]:
        image_path = os.path.join(floorplan_dir, f"{floor}_official.jpg")
        
        if not os.path.exists(image_path):
            print(f"跳过 {floor}: 图片不存在")
            continue
        
        print(f"处理 {floor}...")
        
        try:
            # 使用 PaddleOCR 检测
            labels = detector.detect_with_paddleocr(image_path)
            
            # 导出节点
            nodes = detector.export_to_json(labels, floor, (3000, 2000))
            all_nodes.update(nodes)
            
            print(f"  检测到 {len(labels)} 个房间标签")
            
            # 可视化（可选）
            vis_path = os.path.join(floorplan_dir, f"{floor}_detected.jpg")
            detector.visualize_detection(image_path, labels, vis_path)
            
        except Exception as e:
            print(f"  错误: {e}")
    
    # 保存结果
    if output_path:
        import json
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({"nodes": all_nodes}, f, ensure_ascii=False, indent=2)
        print(f"\n结果已保存到: {output_path}")
    
    return all_nodes


if __name__ == "__main__":
    # 示例用法
    import sys
    
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        detector = RoomLabelDetector()
        
        print(f"检测图片: {image_path}")
        
        # 使用 EasyOCR 检测
        labels = detector.detect_with_easyocr(image_path)
        
        if labels:
            print(f"\n检测到 {len(labels)} 个房间标签:")
            for label in labels:
                print(f"  {label['text']}: 中心点 {label['center']}, 置信度 {label['confidence']:.2f}")
            
            # 可视化
            detector.visualize_detection(image_path, labels, "detected_output.jpg")
            print("\n可视化结果已保存到: detected_output.jpg")
        else:
            print("未检测到房间标签")
    else:
        print("用法: python room_label_detector.py <楼层图图片路径>")

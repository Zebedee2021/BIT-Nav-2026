#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
房间坐标预测补全算法 V2.0
基于OCR识别的房间位置，预测未识别房间的位置

优化功能:
1. 置信度加权预测
2. 多楼层协同预测
3. 相邻分区交叉验证
4. 异常值检测和修正
5. 无OCR数据分区的推测

作者: Qoder AI
日期: 2026-04-02
"""

import json
import numpy as np
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
import math
from dataclasses import dataclass
from enum import Enum


class PredictionMethod(Enum):
    """预测方法枚举"""
    LINEAR_INTERPOLATION = "linear_interpolation"
    EXTRAPOLATION = "extrapolation"
    GRID_PATTERN = "grid_pattern"
    FLOOR_ALIGNMENT = "floor_alignment"
    CROSS_ZONE_INFERENCE = "cross_zone_inference"
    SPATIAL_CLUSTERING = "spatial_clustering"
    MANUAL_PATTERN = "manual_pattern"


@dataclass
class RoomPrediction:
    """房间预测结果数据结构"""
    room_id: str
    x: int
    y: int
    method: PredictionMethod
    confidence: float
    source_rooms: List[str]  # 用于预测的源房间
    zone: str
    floor: str


class RoomPositionPredictor:
    """房间位置预测器 V2.0 - 基于已识别房间推断未识别房间位置"""
    
    def __init__(self, building_file: str):
        """初始化预测器"""
        with open(building_file, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        
        self.nodes = self.data.get('nodes', {})
        self.predictions: Dict[str, RoomPrediction] = {}
        
        # 分区相邻关系（基于文萃楼U形结构）
        self.zone_adjacency = {
            'A': ['B', 'C'],
            'B': ['A', 'C', 'L'],
            'C': ['A', 'B', 'D'],
            'D': ['C', 'E'],
            'E': ['D', 'F'],
            'F': ['E', 'G'],
            'G': ['F', 'H'],
            'H': ['G', 'I'],
            'I': ['H', 'J'],
            'J': ['I', 'K'],
            'K': ['J', 'L'],
            'L': ['K', 'B', 'M'],
            'M': ['L']
        }
        
    def analyze_zone_patterns(self) -> Dict:
        """分析每个分区的房间布局模式"""
        zone_stats = defaultdict(lambda: {
            'rooms': [],
            'ocr_rooms': [],
            'floors': set(),
            'x_coords': [],
            'y_coords': []
        })
        
        for node_id, node in self.nodes.items():
            if node.get('type') != 'room':
                continue
                
            zone = node.get('zone', '')
            floor = node.get('floor', '')
            
            zone_stats[zone]['rooms'].append(node)
            zone_stats[zone]['floors'].add(floor)
            
            # 区分OCR识别和未识别的房间
            if 'ocr_conf' in node:
                zone_stats[zone]['ocr_rooms'].append(node)
                zone_stats[zone]['x_coords'].append(node.get('x', 0))
                zone_stats[zone]['y_coords'].append(node.get('y', 0))
        
        return dict(zone_stats)
    
    def detect_layout_pattern(self, ocr_rooms: List[Dict]) -> str:
        """检测房间布局模式"""
        if len(ocr_rooms) < 2:
            return 'unknown'
        
        # 计算坐标方差
        xs = [r.get('x', 0) for r in ocr_rooms]
        ys = [r.get('y', 0) for r in ocr_rooms]
        
        x_var = np.var(xs) if len(xs) > 1 else 0
        y_var = np.var(ys) if len(ys) > 1 else 0
        
        # 判断布局类型
        if x_var < 1000 and y_var > 1000:
            return 'vertical_corridor'  # 垂直走廊（X固定，Y变化）
        elif y_var < 1000 and x_var > 1000:
            return 'horizontal_corridor'  # 水平走廊（Y固定，X变化）
        elif x_var > 1000 and y_var > 1000:
            return 'grid'  # 网格布局
        else:
            return 'linear'  # 线性布局
    
    def get_room_number(self, room: Dict) -> int:
        """获取房间编号数字部分"""
        name = room.get('name', '')
        try:
            return int(name.split('-')[-1])
        except:
            return 0
    
    def calculate_confidence_weighted_position(self, source_rooms: List[Dict]) -> Tuple[float, float, float]:
        """基于置信度加权计算位置
        
        Returns:
            (weighted_x, weighted_y, avg_confidence)
        """
        if not source_rooms:
            return 0, 0, 0
        
        total_weight = 0
        weighted_x = 0
        weighted_y = 0
        confidences = []
        
        for room in source_rooms:
            conf = room.get('ocr_conf', 0.5)
            if 'predicted' in room:
                conf = room.get('prediction_confidence', 0.3)
            
            weight = conf ** 2  # 平方加权，高置信度更有影响力
            weighted_x += room.get('x', 0) * weight
            weighted_y += room.get('y', 0) * weight
            total_weight += weight
            confidences.append(conf)
        
        if total_weight == 0:
            return 0, 0, 0
        
        return weighted_x / total_weight, weighted_y / total_weight, np.mean(confidences)
    
    def detect_outliers_and_correct(self, rooms: List[Dict]) -> List[Dict]:
        """检测并修正异常值"""
        if len(rooms) < 3:
            return rooms
        
        # 计算坐标的中位数和四分位数
        xs = [r.get('x', 0) for r in rooms]
        ys = [r.get('y', 0) for r in rooms]
        
        x_median = np.median(xs)
        y_median = np.median(ys)
        
        # 计算标准差
        x_std = np.std(xs)
        y_std = np.std(ys)
        
        # 标记异常值（超过2个标准差）
        corrected = []
        for room in rooms:
            x = room.get('x', 0)
            y = room.get('y', 0)
            
            is_outlier = abs(x - x_median) > 2 * x_std or abs(y - y_median) > 2 * y_std
            
            if is_outlier and 'ocr_conf' in room and room['ocr_conf'] < 0.5:
                # 低置信度的异常值，标记为需要重新预测
                room_copy = room.copy()
                room_copy['needs_reprediction'] = True
                corrected.append(room_copy)
            else:
                corrected.append(room)
        
        return corrected
    
    def predict_by_linear_interpolation(self, zone: str, floor: str, 
                                        ocr_rooms: List[Dict]) -> Dict[str, RoomPrediction]:
        """使用置信度加权线性插值预测房间位置"""
        predictions = {}
        
        if len(ocr_rooms) < 2:
            return predictions
        
        # 检测并修正异常值
        ocr_rooms = self.detect_outliers_and_correct(ocr_rooms)
        
        # 过滤掉需要重新预测的房间
        valid_ocr = [r for r in ocr_rooms if not r.get('needs_reprediction', False)]
        
        if len(valid_ocr) < 2:
            valid_ocr = ocr_rooms  # 如果过滤后太少，使用原始数据
        
        # 按房间号排序
        sorted_rooms = sorted(valid_ocr, key=self.get_room_number)
        
        # 获取已知点的坐标（带置信度）
        known_points = []
        for room in sorted_rooms:
            num = self.get_room_number(room)
            x = room.get('x', 0)
            y = room.get('y', 0)
            conf = room.get('ocr_conf', 0.5) if 'ocr_conf' in room else room.get('prediction_confidence', 0.3)
            known_points.append((num, x, y, conf, room.get('id', '')))
        
        # 找到该楼层所有房间
        floor_rooms = [r for r in self.nodes.values() 
                      if r.get('zone') == zone and r.get('floor') == floor 
                      and r.get('type') == 'room']
        
        # 对每个未识别的房间进行插值
        for room in floor_rooms:
            if 'ocr_conf' in room:
                continue  # 跳过已识别的
            
            room_num = self.get_room_number(room)
            room_id = room.get('id', '')
            
            # 找到最近的两个已知点进行插值
            lower_candidates = [kp for kp in known_points if kp[0] < room_num]
            upper_candidates = [kp for kp in known_points if kp[0] > room_num]
            
            # 选择置信度最高的作为边界点
            lower = max(lower_candidates, key=lambda x: x[3]) if lower_candidates else None
            upper = max(upper_candidates, key=lambda x: x[3]) if upper_candidates else None
            
            source_rooms = []
            
            if lower and upper:
                # 线性插值（置信度加权）
                t = (room_num - lower[0]) / (upper[0] - lower[0])
                
                # 加权平均
                total_conf = lower[3] + upper[3]
                w1 = lower[3] / total_conf if total_conf > 0 else 0.5
                w2 = upper[3] / total_conf if total_conf > 0 else 0.5
                
                pred_x = int(lower[1] * (1-t) * w1 + upper[1] * t * w2)
                pred_y = int(lower[2] * (1-t) * w1 + upper[2] * t * w2)
                
                # 计算置信度（基于距离和源置信度）
                distance_factor = 1.0 / (1 + abs(upper[0] - lower[0]))
                confidence = (lower[3] + upper[3]) / 2 * distance_factor
                method = PredictionMethod.LINEAR_INTERPOLATION
                source_rooms = [lower[4], upper[4]]
                
            elif lower:
                # 外推 - 使用平均间隔（置信度加权）
                if len(known_points) >= 2:
                    # 计算加权平均间隔
                    total_weight = 0
                    weighted_dx = 0
                    weighted_dy = 0
                    
                    for i in range(len(known_points)-1):
                        dx = known_points[i+1][1] - known_points[i][1]
                        dy = known_points[i+1][2] - known_points[i][2]
                        num_gap = known_points[i+1][0] - known_points[i][0]
                        
                        if num_gap > 0:
                            avg_conf = (known_points[i][3] + known_points[i+1][3]) / 2
                            weighted_dx += (dx / num_gap) * avg_conf
                            weighted_dy += (dy / num_gap) * avg_conf
                            total_weight += avg_conf
                    
                    if total_weight > 0:
                        avg_dx = weighted_dx / total_weight
                        avg_dy = weighted_dy / total_weight
                    else:
                        avg_dx = np.mean([known_points[i+1][1] - known_points[i][1] 
                                         for i in range(len(known_points)-1)])
                        avg_dy = np.mean([known_points[i+1][2] - known_points[i][2] 
                                         for i in range(len(known_points)-1)])
                    
                    steps = room_num - lower[0]
                    pred_x = int(lower[1] + steps * avg_dx)
                    pred_y = int(lower[2] + steps * avg_dy)
                    confidence = lower[3] * 0.7  # 外推降低置信度
                    method = PredictionMethod.EXTRAPOLATION
                    source_rooms = [lower[4]]
                else:
                    continue
            else:
                continue
            
            predictions[room_id] = RoomPrediction(
                room_id=room_id,
                x=pred_x,
                y=pred_y,
                method=method,
                confidence=min(confidence, 0.95),
                source_rooms=source_rooms,
                zone=zone,
                floor=floor
            )
        
        return predictions
    
    def predict_by_grid_pattern(self, zone: str, ocr_rooms: List[Dict]) -> Dict[str, Tuple[int, int]]:
        """基于网格模式预测房间位置"""
        predictions = {}
        
        if len(ocr_rooms) < 2:
            return predictions
        
        # 分析网格规律
        xs = [r.get('x', 0) for r in ocr_rooms]
        ys = [r.get('y', 0) for r in ocr_rooms]
        
        # 找出X和Y的固定值或间隔
        unique_xs = sorted(set(xs))
        unique_ys = sorted(set(ys))
        
        # 计算间隔模式
        if len(unique_xs) > 1:
            x_gaps = [unique_xs[i+1] - unique_xs[i] for i in range(len(unique_xs)-1)]
            common_x_gap = max(set(x_gaps), key=x_gaps.count) if x_gaps else 120
        else:
            common_x_gap = 0
            
        if len(unique_ys) > 1:
            y_gaps = [unique_ys[i+1] - unique_ys[i] for i in range(len(unique_ys)-1)]
            common_y_gap = max(set(y_gaps), key=y_gaps.count) if y_gaps else 120
        else:
            common_y_gap = 0
        
        # 获取该分区所有房间
        zone_rooms = [r for r in self.nodes.values() 
                     if r.get('zone') == zone and r.get('type') == 'room']
        
        # 按楼层和房间号分组
        floor_groups = defaultdict(list)
        for room in zone_rooms:
            floor = room.get('floor', '')
            floor_groups[floor].append(room)
        
        # 对每个楼层进行预测
        for floor, rooms in floor_groups.items():
            ocr_in_floor = [r for r in rooms if 'ocr_conf' in r]
            
            if not ocr_in_floor:
                continue
            
            # 找到基准点
            base_room = min(ocr_in_floor, key=lambda r: int(r.get('name', '0').split('-')[-1] or 0))
            base_x = base_room.get('x', 0)
            base_y = base_room.get('y', 0)
            base_num = int(base_room.get('name', '0').split('-')[-1] or 0)
            
            for room in rooms:
                if 'ocr_conf' in room:
                    continue
                
                room_num = int(room.get('name', '0').split('-')[-1] or 0)
                room_id = room.get('id', '')
                
                # 基于网格间隔预测
                offset = room_num - base_num
                
                if common_x_gap > 0:
                    pred_x = base_x + offset * common_x_gap
                else:
                    pred_x = base_x
                    
                if common_y_gap > 0:
                    pred_y = base_y + offset * common_y_gap
                else:
                    pred_y = base_y
                
                predictions[room_id] = (int(pred_x), int(pred_y), 'grid_pattern')
        
        return predictions
    
    def predict_by_multi_floor_collaboration(self, zone: str) -> Dict[str, RoomPrediction]:
        """多楼层协同预测 - 利用所有楼层的OCR数据提高预测精度"""
        predictions = {}
        
        # 收集所有楼层的数据（包括已预测的房间）
        floor_data = defaultdict(list)
        for node in self.nodes.values():
            if node.get('zone') == zone and node.get('type') == 'room':
                floor = node.get('floor', '')
                if 'ocr_conf' in node or 'predicted' in node:
                    floor_data[floor].append(node)
        
        # 对每个楼层进行预测
        all_floors = ['1F', '2F', '3F', '4F', '5F', '6F', '7F', '8F', '9F', '10F']
        
        for target_floor in all_floors:
            # 获取目标楼层未识别的房间
            target_rooms = [r for r in self.nodes.values()
                           if r.get('zone') == zone 
                           and r.get('floor') == target_floor
                           and r.get('type') == 'room'
                           and 'ocr_conf' not in r
                           and 'predicted' not in r]
            
            for room in target_rooms:
                room_suffix = room.get('name', '').split('-')[-1]
                room_id = room.get('id', '')
                
                # 收集所有楼层同号房间的位置
                same_number_rooms = []
                for floor, rooms in floor_data.items():
                    if floor != target_floor:
                        for r in rooms:
                            if r.get('name', '').split('-')[-1] == room_suffix:
                                same_number_rooms.append(r)
                
                if len(same_number_rooms) >= 1:
                    # 使用置信度加权平均
                    weighted_x, weighted_y, avg_conf = self.calculate_confidence_weighted_position(same_number_rooms)
                    
                    # 楼层越多，置信度越高
                    floor_bonus = min(len(same_number_rooms) * 0.05, 0.15)
                    confidence = min(avg_conf + floor_bonus, 0.9)
                    
                    predictions[room_id] = RoomPrediction(
                        room_id=room_id,
                        x=int(weighted_x),
                        y=int(weighted_y),
                        method=PredictionMethod.FLOOR_ALIGNMENT,
                        confidence=confidence,
                        source_rooms=[r.get('id', '') for r in same_number_rooms],
                        zone=zone,
                        floor=target_floor
                    )
        
        return predictions
    
    def predict_by_cross_zone_inference(self, target_zone: str) -> Dict[str, RoomPrediction]:
        """相邻分区交叉验证预测 - 利用相邻分区的布局规律"""
        predictions = {}
        
        # 获取目标分区的相邻分区
        adjacent_zones = self.zone_adjacency.get(target_zone, [])
        
        if not adjacent_zones:
            return predictions
        
        # 收集相邻分区的OCR数据
        adjacent_patterns = {}
        for adj_zone in adjacent_zones:
            adj_ocr = [r for r in self.nodes.values()
                      if r.get('zone') == adj_zone 
                      and r.get('type') == 'room'
                      and 'ocr_conf' in r]
            
            if len(adj_ocr) >= 3:
                # 分析相邻分区的布局模式
                xs = [r.get('x', 0) for r in adj_ocr]
                ys = [r.get('y', 0) for r in adj_ocr]
                
                adjacent_patterns[adj_zone] = {
                    'x_range': (min(xs), max(xs)),
                    'y_range': (min(ys), max(ys)),
                    'center_x': np.mean(xs),
                    'center_y': np.mean(ys),
                    'rooms': adj_ocr
                }
        
        if not adjacent_patterns:
            return predictions
        
        # 获取目标分区未识别的房间
        target_rooms = [r for r in self.nodes.values()
                       if r.get('zone') == target_zone 
                       and r.get('type') == 'room'
                       and 'ocr_conf' not in r
                       and 'predicted' not in r]
        
        # 基于相邻分区的平均偏移进行预测
        for room in target_rooms:
            room_id = room.get('id', '')
            floor = room.get('floor', '')
            room_num = self.get_room_number(room)
            
            # 在相邻分区找到同楼层、相似编号的房间
            reference_positions = []
            
            for adj_zone, pattern in adjacent_patterns.items():
                adj_room = None
                adj_min_diff = float('inf')
                
                for r in pattern['rooms']:
                    if r.get('floor') == floor:
                        diff = abs(self.get_room_number(r) - room_num)
                        if diff < adj_min_diff:
                            adj_min_diff = diff
                            adj_room = r
                
                if adj_room and adj_min_diff <= 10:  # 编号相差不超过10
                    # 计算相对位置
                    rel_x = adj_room.get('x', 0) - pattern['center_x']
                    rel_y = adj_room.get('y', 0) - pattern['center_y']
                    
                    # 估算目标分区的中心（基于相邻分区中心偏移）
                    # 这里简化处理，使用相邻分区的平均中心
                    target_center_x = np.mean([p['center_x'] for p in adjacent_patterns.values()])
                    target_center_y = np.mean([p['center_y'] for p in adjacent_patterns.values()])
                    
                    # 根据文萃楼U形结构调整偏移方向
                    if target_zone in ['A', 'B', 'C', 'D', 'E']:
                        # 东侧分区，X坐标较大
                        target_center_x += 200
                    elif target_zone in ['F', 'G', 'H', 'I', 'J']:
                        # 南侧分区，Y坐标较大
                        target_center_y += 200
                    elif target_zone in ['K', 'L', 'M']:
                        # 西侧分区，X坐标较小
                        target_center_x -= 200
                    
                    pred_x = int(target_center_x + rel_x)
                    pred_y = int(target_center_y + rel_y)
                    
                    reference_positions.append((pred_x, pred_y, adj_room.get('ocr_conf', 0.5), adj_room.get('id', '')))
            
            if reference_positions:
                # 加权平均
                total_weight = sum(pos[2] for pos in reference_positions)
                pred_x = int(sum(pos[0] * pos[2] for pos in reference_positions) / total_weight)
                pred_y = int(sum(pos[1] * pos[2] for pos in reference_positions) / total_weight)
                avg_conf = np.mean([pos[2] for pos in reference_positions]) * 0.6  # 交叉验证降低置信度
                
                predictions[room_id] = RoomPrediction(
                    room_id=room_id,
                    x=pred_x,
                    y=pred_y,
                    method=PredictionMethod.CROSS_ZONE_INFERENCE,
                    confidence=min(avg_conf, 0.7),
                    source_rooms=[pos[3] for pos in reference_positions],
                    zone=target_zone,
                    floor=floor
                )
        
        return predictions
    
    def predict_for_no_ocr_zone(self, zone: str) -> Dict[str, RoomPrediction]:
        """为完全没有OCR数据的分区进行预测"""
        predictions = {}
        
        # 获取该分区的所有房间
        zone_rooms = [r for r in self.nodes.values()
                     if r.get('zone') == zone and r.get('type') == 'room']
        
        if not zone_rooms:
            return predictions
        
        # 使用相邻分区的布局规律
        adjacent_predictions = self.predict_by_cross_zone_inference(zone)
        predictions.update(adjacent_predictions)
        
        # 如果还有未预测的房间，使用空间聚类方法
        predicted_ids = set(predictions.keys())
        remaining_rooms = [r for r in zone_rooms if r.get('id', '') not in predicted_ids]
        
        if remaining_rooms:
            # 基于房间编号的连续性进行空间分布推测
            floor_groups = defaultdict(list)
            for room in remaining_rooms:
                floor_groups[room.get('floor', '')].append(room)
            
            for floor, rooms in floor_groups.items():
                # 按编号排序
                sorted_rooms = sorted(rooms, key=self.get_room_number)
                
                # 如果有预测的房间作为参考点
                floor_predicted = [predictions[r.get('id', '')] for r in zone_rooms 
                                  if r.get('floor') == floor and r.get('id', '') in predictions]
                
                if floor_predicted:
                    # 使用已有预测点作为基准
                    base_pred = floor_predicted[0]
                    base_room = next((r for r in sorted_rooms 
                                     if r.get('id', '') == base_pred.room_id), None)
                    
                    if base_room:
                        base_num = self.get_room_number(base_room)
                        
                        # 估算间隔
                        estimated_gap = 120  # 默认间隔
                        
                        for room in sorted_rooms:
                            room_id = room.get('id', '')
                            if room_id in predictions:
                                continue
                            
                            room_num = self.get_room_number(room)
                            offset = room_num - base_num
                            
                            pred_x = base_pred.x + offset * estimated_gap
                            pred_y = base_pred.y
                            
                            predictions[room_id] = RoomPrediction(
                                room_id=room_id,
                                x=pred_x,
                                y=pred_y,
                                method=PredictionMethod.SPATIAL_CLUSTERING,
                                confidence=0.3,  # 低置信度
                                source_rooms=[base_pred.room_id],
                                zone=zone,
                                floor=floor
                            )
        
        return predictions
    
    def predict_all(self) -> Dict[str, RoomPrediction]:
        """执行所有预测策略 V2.0"""
        print("=" * 70)
        print("房间坐标预测补全算法 V2.0")
        print("=" * 70)
        print("优化功能: 置信度加权 | 多楼层协同 | 相邻分区交叉验证")
        print("=" * 70)
        
        # 分析各分区模式
        zone_stats = self.analyze_zone_patterns()
        
        all_predictions: Dict[str, RoomPrediction] = {}
        
        for zone, stats in zone_stats.items():
            ocr_count = len(stats['ocr_rooms'])
            total_count = len(stats['rooms'])
            
            print(f"\n【分区 {zone}】")
            print(f"  总房间数: {total_count} | OCR识别: {ocr_count} ({ocr_count/total_count*100:.1f}%)")
            
            zone_predictions: Dict[str, RoomPrediction] = {}
            
            if ocr_count == 0:
                # 无OCR数据的分区，使用交叉分区推断
                print(f"  ⚠️ 无OCR数据，使用相邻分区交叉推断...")
                no_ocr_preds = self.predict_for_no_ocr_zone(zone)
                zone_predictions.update(no_ocr_preds)
            else:
                # 检测布局模式
                layout = self.detect_layout_pattern(stats['ocr_rooms'])
                print(f"  布局模式: {layout} | 楼层: {sorted(stats['floors'])}")
                
                # 1. 按楼层执行置信度加权线性插值
                for floor in sorted(stats['floors']):
                    floor_ocr = [r for r in stats['ocr_rooms'] if r.get('floor') == floor]
                    if len(floor_ocr) >= 2:
                        preds = self.predict_by_linear_interpolation(zone, floor, floor_ocr)
                        zone_predictions.update(preds)
                
                print(f"  📊 线性插值预测: {len(zone_predictions)} 个")
                
                # 2. 多楼层协同预测
                multi_floor_preds = self.predict_by_multi_floor_collaboration(zone)
                merged_count = 0
                for room_id, pred in multi_floor_preds.items():
                    if room_id not in zone_predictions:
                        zone_predictions[room_id] = pred
                        merged_count += 1
                    elif pred.confidence > zone_predictions[room_id].confidence:
                        # 如果新预测置信度更高，替换
                        zone_predictions[room_id] = pred
                        merged_count += 1
                
                if merged_count > 0:
                    print(f"  🏢 多楼层协同增强: {merged_count} 个")
                
                # 3. 相邻分区交叉验证
                cross_zone_preds = self.predict_by_cross_zone_inference(zone)
                cross_merged = 0
                for room_id, pred in cross_zone_preds.items():
                    if room_id not in zone_predictions:
                        zone_predictions[room_id] = pred
                        cross_merged += 1
                
                if cross_merged > 0:
                    print(f"  🔗 相邻分区交叉验证: {cross_merged} 个")
            
            # 统计预测置信度分布
            if zone_predictions:
                high_conf = sum(1 for p in zone_predictions.values() if p.confidence >= 0.7)
                med_conf = sum(1 for p in zone_predictions.values() if 0.4 <= p.confidence < 0.7)
                low_conf = sum(1 for p in zone_predictions.values() if p.confidence < 0.4)
                
                print(f"  ✅ 总预测: {len(zone_predictions)} 个 (高:{high_conf} 中:{med_conf} 低:{low_conf})")
            
            all_predictions.update(zone_predictions)
        
        self.predictions = all_predictions
        return all_predictions
    
    def apply_predictions(self, output_file: str = None):
        """将预测结果应用到建筑数据中 V2.0"""
        if not self.predictions:
            print("\n请先执行 predict_all()")
            return
        
        # 复制原始数据
        updated_data = json.loads(json.dumps(self.data))
        
        updated_count = 0
        high_conf_count = 0
        med_conf_count = 0
        low_conf_count = 0
        
        for room_id, prediction in self.predictions.items():
            if room_id in updated_data['nodes']:
                node = updated_data['nodes'][room_id]
                
                # 只更新没有OCR数据的房间
                if 'ocr_conf' not in node:
                    node['x'] = prediction.x
                    node['y'] = prediction.y
                    node['ux'] = prediction.x  # 统一坐标
                    node['uy'] = prediction.y
                    node['predicted'] = True
                    node['prediction_method'] = prediction.method.value
                    node['prediction_confidence'] = round(prediction.confidence, 3)
                    node['prediction_sources'] = prediction.source_rooms
                    
                    updated_count += 1
                    
                    if prediction.confidence >= 0.7:
                        high_conf_count += 1
                    elif prediction.confidence >= 0.4:
                        med_conf_count += 1
                    else:
                        low_conf_count += 1
        
        print(f"\n{'=' * 70}")
        print(f"预测应用完成")
        print(f"{'=' * 70}")
        print(f"更新房间数: {updated_count}")
        print(f"  - 高置信度 (≥0.7): {high_conf_count}")
        print(f"  - 中置信度 (0.4-0.7): {med_conf_count}")
        print(f"  - 低置信度 (<0.4): {low_conf_count}")
        
        # 统计最终覆盖率
        total_rooms = sum(1 for n in updated_data['nodes'].values() 
                         if n.get('type') == 'room')
        ocr_rooms = sum(1 for n in updated_data['nodes'].values() 
                       if n.get('type') == 'room' and 'ocr_conf' in n)
        predicted_rooms = sum(1 for n in updated_data['nodes'].values() 
                             if n.get('type') == 'room' and n.get('predicted'))
        
        coverage = (ocr_rooms + predicted_rooms) / total_rooms * 100 if total_rooms > 0 else 0
        
        print(f"\n📊 最终统计:")
        print(f"  - 总房间数: {total_rooms}")
        print(f"  - OCR识别: {ocr_rooms} ({ocr_rooms/total_rooms*100:.1f}%)")
        print(f"  - 算法预测: {predicted_rooms} ({predicted_rooms/total_rooms*100:.1f}%)")
        print(f"  - 总覆盖率: {coverage:.1f}%")
        
        # 计算质量分数
        quality_score = (ocr_rooms + high_conf_count * 0.8 + med_conf_count * 0.5 + low_conf_count * 0.2) / total_rooms * 100
        print(f"  - 数据质量分: {quality_score:.1f}/100")
        
        # 保存结果
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(updated_data, f, ensure_ascii=False, indent=2)
            print(f"\n💾 结果已保存到: {output_file}")
        
        return updated_data
    
    def generate_prediction_report(self) -> Dict:
        """生成详细预测报告 V2.0"""
        report = {
            'total_predictions': len(self.predictions),
            'by_method': defaultdict(int),
            'by_zone': defaultdict(lambda: {'count': 0, 'avg_confidence': 0, 'methods': defaultdict(int)}),
            'confidence_distribution': {'high': 0, 'medium': 0, 'low': 0},
            'floor_coverage': defaultdict(int)
        }
        
        conf_sum_by_zone = defaultdict(float)
        
        for room_id, pred in self.predictions.items():
            # 按方法统计
            report['by_method'][pred.method.value] += 1
            
            # 按分区统计
            zone = pred.zone
            report['by_zone'][zone]['count'] += 1
            conf_sum_by_zone[zone] += pred.confidence
            report['by_zone'][zone]['methods'][pred.method.value] += 1
            
            # 置信度分布
            if pred.confidence >= 0.7:
                report['confidence_distribution']['high'] += 1
            elif pred.confidence >= 0.4:
                report['confidence_distribution']['medium'] += 1
            else:
                report['confidence_distribution']['low'] += 1
            
            # 楼层覆盖
            report['floor_coverage'][pred.floor] += 1
        
        # 计算平均置信度
        for zone in report['by_zone']:
            if report['by_zone'][zone]['count'] > 0:
                report['by_zone'][zone]['avg_confidence'] = round(
                    conf_sum_by_zone[zone] / report['by_zone'][zone]['count'], 3
                )
        
        return dict(report)


def main():
    """主函数 V2.0"""
    import os
    
    # 文件路径
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_file = os.path.join(base_dir, 'data', 'wencui_building_v5.json')
    output_file = os.path.join(base_dir, 'data', 'wencui_building_v5_predicted_v2.json')
    
    print(f"📁 输入文件: {input_file}")
    print(f"📁 输出文件: {output_file}")
    
    # 创建预测器
    predictor = RoomPositionPredictor(input_file)
    
    # 执行预测
    predictions = predictor.predict_all()
    
    # 生成报告
    report = predictor.generate_prediction_report()
    
    print(f"\n{'=' * 70}")
    print("📈 预测方法统计")
    print(f"{'=' * 70}")
    for method, count in sorted(report['by_method'].items(), key=lambda x: x[1], reverse=True):
        pct = count / report['total_predictions'] * 100 if report['total_predictions'] > 0 else 0
        print(f"  {method:30s}: {count:4d} ({pct:5.1f}%)")
    
    print(f"\n{'=' * 70}")
    print("🎯 置信度分布")
    print(f"{'=' * 70}")
    total = report['total_predictions']
    print(f"  高置信度 (≥0.7): {report['confidence_distribution']['high']:4d} ({report['confidence_distribution']['high']/total*100:5.1f}%)")
    print(f"  中置信度 (0.4-0.7): {report['confidence_distribution']['medium']:4d} ({report['confidence_distribution']['medium']/total*100:5.1f}%)")
    print(f"  低置信度 (<0.4): {report['confidence_distribution']['low']:4d} ({report['confidence_distribution']['low']/total*100:5.1f}%)")
    
    print(f"\n{'=' * 70}")
    print("🏢 分区预测详情")
    print(f"{'=' * 70}")
    print(f"  {'分区':<6} {'数量':>6} {'平均置信度':>12} {'主要方法':<20}")
    print(f"  {'-'*50}")
    for zone, data in sorted(report['by_zone'].items()):
        main_method = max(data['methods'].items(), key=lambda x: x[1])[0] if data['methods'] else 'N/A'
        print(f"  {zone:<6} {data['count']:>6} {data['avg_confidence']:>12.3f} {main_method:<20}")
    
    # 应用预测并保存
    updated_data = predictor.apply_predictions(output_file)
    
    print(f"\n{'=' * 70}")
    print("✅ 预测补全完成!")
    print(f"{'=' * 70}")


if __name__ == '__main__':
    main()

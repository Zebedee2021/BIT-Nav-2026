"""
方位感知导航模块
支持基于手机指南针的方位导航（东南西北 + 前后左右）
"""

import math
from typing import Optional, Tuple, Dict, List
from dataclasses import dataclass
from enum import Enum


class Direction(Enum):
    """方位枚举"""
    NORTH = ("北", "前", 0)
    NORTHEAST = ("东北", "右前", 45)
    EAST = ("东", "右", 90)
    SOUTHEAST = ("东南", "右后", 135)
    SOUTH = ("南", "后", 180)
    SOUTHWEST = ("西南", "左后", 225)
    WEST = ("西", "左", 270)
    NORTHWEST = ("西北", "左前", 315)
    
    def __init__(self, cardinal: str, relative: str, degrees: int):
        self.cardinal = cardinal  # 东南西北
        self.relative = relative  # 前后左右
        self.degrees = degrees    # 角度


@dataclass
class NavigationDirection:
    """导航方向信息"""
    angle: float                    # 绝对角度（0-360，0为北）
    cardinal_direction: str         # 东南西北表示
    relative_direction: str         # 前后左右表示
    turn_instruction: str           # 转向指令
    distance: float                 # 距离（米，估算）
    
    def to_dict(self) -> Dict:
        return {
            "angle": round(self.angle, 1),
            "cardinal": self.cardinal_direction,
            "relative": self.relative_direction,
            "turn": self.turn_instruction,
            "distance": round(self.distance, 1)
        }


class OrientationNavigator:
    """方位感知导航器"""
    
    # 方向阈值（角度范围）
    DIRECTION_RANGES = [
        (337.5, 22.5, Direction.NORTH),
        (22.5, 67.5, Direction.NORTHEAST),
        (67.5, 112.5, Direction.EAST),
        (112.5, 157.5, Direction.SOUTHEAST),
        (157.5, 202.5, Direction.SOUTH),
        (202.5, 247.5, Direction.SOUTHWEST),
        (247.5, 292.5, Direction.WEST),
        (292.5, 337.5, Direction.NORTHWEST),
    ]
    
    def __init__(self, pixel_to_meter: float = 0.1):
        """
        初始化导航器
        
        Args:
            pixel_to_meter: 像素到米的转换比例（默认0.1米/像素）
        """
        self.pixel_to_meter = pixel_to_meter
        self.user_heading = 0  # 用户当前朝向（0为北）
    
    def set_user_heading(self, heading: float):
        """
        设置用户当前朝向
        
        Args:
            heading: 指南针角度（0-360，0为北，90为东）
        """
        self.user_heading = heading % 360
    
    def calculate_direction(self, from_point: Tuple[float, float], 
                           to_point: Tuple[float, float]) -> NavigationDirection:
        """
        计算从from_point到to_point的方向
        
        Args:
            from_point: 起点坐标 (x, y)
            to_point: 终点坐标 (x, y)
        
        Returns:
            NavigationDirection对象
        """
        dx = to_point[0] - from_point[0]
        dy = to_point[1] - from_point[1]
        
        # 计算角度（0为北，顺时针）
        # 注意：在屏幕坐标系中，y轴向下为正，需要翻转
        angle = math.degrees(math.atan2(dx, -dy)) % 360
        
        # 计算距离
        distance_pixels = math.sqrt(dx * dx + dy * dy)
        distance_meters = distance_pixels * self.pixel_to_meter
        
        # 获取方位名称
        direction = self._angle_to_direction(angle)
        
        # 计算相对方向（基于用户朝向）
        relative_angle = (angle - self.user_heading) % 360
        relative_direction = self._angle_to_relative_direction(relative_angle)
        
        # 生成转向指令
        turn_instruction = self._generate_turn_instruction(relative_angle)
        
        return NavigationDirection(
            angle=angle,
            cardinal_direction=direction.cardinal,
            relative_direction=relative_direction,
            turn_instruction=turn_instruction,
            distance=distance_meters
        )
    
    def _angle_to_direction(self, angle: float) -> Direction:
        """将角度转换为方位"""
        for start, end, direction in self.DIRECTION_RANGES:
            if start <= angle < end or (start > end and (angle >= start or angle < end)):
                return direction
        return Direction.NORTH
    
    def _angle_to_relative_direction(self, relative_angle: float) -> str:
        """将相对角度转换为前后左右描述"""
        direction = self._angle_to_direction(relative_angle)
        return direction.relative
    
    def _generate_turn_instruction(self, relative_angle: float) -> str:
        """生成转向指令"""
        if relative_angle < 15 or relative_angle > 345:
            return "直行"
        elif 15 <= relative_angle < 45:
            return "稍向右转"
        elif 45 <= relative_angle < 90:
            return "向右转"
        elif 90 <= relative_angle < 135:
            return "向右后方转"
        elif 135 <= relative_angle < 225:
            return "向后转"
        elif 225 <= relative_angle < 270:
            return "向左后方转"
        elif 270 <= relative_angle < 315:
            return "向左转"
        elif 315 <= relative_angle <= 345:
            return "稍向左转"
        return "直行"
    
    def generate_path_directions(self, path_points: List[Tuple[float, float]], 
                                 point_names: Optional[List[str]] = None) -> List[Dict]:
        """
        为整个路径生成方位导航指令
        
        Args:
            path_points: 路径点坐标列表
            point_names: 路径点名称列表（可选）
        
        Returns:
            导航指令列表
        """
        if len(path_points) < 2:
            return []
        
        instructions = []
        
        for i in range(len(path_points) - 1):
            from_point = path_points[i]
            to_point = path_points[i + 1]
            
            direction = self.calculate_direction(from_point, to_point)
            
            # 构建导航指令
            instruction = {
                "step": i + 1,
                "from": point_names[i] if point_names and i < len(point_names) else f"点{i}",
                "to": point_names[i + 1] if point_names and i + 1 < len(point_names) else f"点{i+1}",
                "direction": direction.to_dict(),
                "text_cardinal": f"向{direction.cardinal_direction}方向走{direction.distance:.1f}米",
                "text_relative": f"向{direction.relative_direction}走{direction.distance:.1f}米",
                "text_full": f"{direction.turn_instruction}，向{direction.cardinal_direction}（{direction.relative_direction}）走{direction.distance:.1f}米"
            }
            
            instructions.append(instruction)
        
        return instructions
    
    def get_compass_display(self) -> Dict:
        """
        获取指南针显示信息
        
        Returns:
            指南针显示数据
        """
        direction = self._angle_to_direction(self.user_heading)
        
        return {
            "heading": round(self.user_heading, 1),
            "cardinal": direction.cardinal,
            "arrow_rotation": -self.user_heading,  # 用于CSS旋转
            "display_text": f"朝向: {direction.cardinal} ({round(self.user_heading)}°)"
        }


class RegionalAdapter:
    """地域适配器 - 处理南北方对方位的不同认知"""
    
    # 地域特定的方位偏好
    REGIONAL_PREFERENCES = {
        "north": {
            "primary": "cardinal",      # 北方人偏好东南西北
            "secondary": "relative",    # 次选前后左右
            "description": "北方人习惯使用东南西北指路"
        },
        "south": {
            "primary": "relative",      # 南方人偏好前后左右
            "secondary": "cardinal",    # 次选东南西北
            "description": "南方人习惯使用前后左右指路"
        },
        "universal": {
            "primary": "both",          # 两者都显示
            "secondary": None,
            "description": "同时显示两种方位表示"
        }
    }
    
    def __init__(self, region: str = "universal"):
        """
        初始化地域适配器
        
        Args:
            region: 地域类型 ("north", "south", "universal")
        """
        self.region = region if region in self.REGIONAL_PREFERENCES else "universal"
        self.preference = self.REGIONAL_PREFERENCES[self.region]
    
    def format_instruction(self, instruction: Dict) -> str:
        """
        根据地域偏好格式化导航指令
        
        Args:
            instruction: 导航指令字典
        
        Returns:
            格式化后的指令文本
        """
        cardinal = instruction.get("text_cardinal", "")
        relative = instruction.get("text_relative", "")
        
        if self.region == "north":
            return f"【方位】{cardinal}\n【参考】{relative}"
        elif self.region == "south":
            return f"【方向】{relative}\n【参考】{cardinal}"
        else:
            return f"{cardinal} ({relative})"
    
    def get_display_priority(self) -> List[str]:
        """获取显示优先级"""
        primary = self.preference["primary"]
        secondary = self.preference["secondary"]
        
        if primary == "both":
            return ["cardinal", "relative"]
        elif secondary:
            return [primary, secondary]
        else:
            return [primary]


# 便捷函数
def create_orientation_navigator(pixel_to_meter: float = 0.1) -> OrientationNavigator:
    """创建方位导航器实例"""
    return OrientationNavigator(pixel_to_meter)


def create_regional_adapter(region: str = "universal") -> RegionalAdapter:
    """创建地域适配器实例"""
    return RegionalAdapter(region)


# 测试代码
if __name__ == "__main__":
    print("=== 方位感知导航测试 ===\n")
    
    # 创建导航器
    navigator = create_orientation_navigator(pixel_to_meter=0.5)
    
    # 测试不同朝向
    test_cases = [
        # (用户朝向, 起点, 终点, 描述)
        (0, (100, 100), (100, 50), "向前走"),
        (0, (100, 100), (150, 100), "向右走"),
        (0, (100, 100), (50, 100), "向左走"),
        (0, (100, 100), (100, 150), "向后走"),
        (45, (100, 100), (150, 50), "朝东北方向"),
    ]
    
    for heading, from_pt, to_pt, desc in test_cases:
        navigator.set_user_heading(heading)
        direction = navigator.calculate_direction(from_pt, to_pt)
        
        print(f"测试: {desc}")
        print(f"  用户朝向: {heading}°")
        print(f"  移动方向: {direction.cardinal_direction} ({direction.angle}°)")
        print(f"  相对方向: {direction.relative_direction}")
        print(f"  转向指令: {direction.turn_instruction}")
        print(f"  距离: {direction.distance:.1f}米")
        print()
    
    # 地域适配测试
    print("=== 地域适配测试 ===\n")
    
    test_instruction = {
        "text_cardinal": "向东方向走10.5米",
        "text_relative": "向右走10.5米"
    }
    
    for region in ["north", "south", "universal"]:
        adapter = create_regional_adapter(region)
        formatted = adapter.format_instruction(test_instruction)
        print(f"{region} 地区:")
        print(f"  {formatted}")
        print()
    
    # 路径导航测试
    print("=== 路径导航测试 ===\n")
    
    path = [(100, 100), (100, 80), (120, 80), (120, 60)]
    names = ["东门", "走廊入口", "电梯口", "D402"]
    
    navigator.set_user_heading(0)  # 用户朝北
    path_instructions = navigator.generate_path_directions(path, names)
    
    for inst in path_instructions:
        print(f"步骤 {inst['step']}: {inst['from']} → {inst['to']}")
        print(f"  {inst['text_full']}")
        print()

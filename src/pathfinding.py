"""
路径规划模块
使用A*算法实现楼宇拓扑图上的最短路径搜索
"""

import json
import heapq
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import math


@dataclass
class Node:
    """节点数据类"""
    id: str
    type: str
    floor: str
    zone: str
    name: str
    description: str
    x: float
    y: float
    
    def __hash__(self):
        return hash(self.id)
    
    def __eq__(self, other):
        return self.id == other.id


class BuildingGraph:
    """楼宇图结构"""
    
    def __init__(self, building_data: dict):
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Tuple[str, str]] = []
        self.adjacency: Dict[str, List[str]] = {}
        
        self._load_building_data(building_data)
    
    def _load_building_data(self, data: dict):
        """加载建筑数据"""
        # 加载节点
        for node_id, node_data in data.get("nodes", {}).items():
            self.nodes[node_id] = Node(
                id=node_id,
                type=node_data.get("type", "unknown"),
                floor=node_data.get("floor", "1F"),
                zone=node_data.get("zone", ""),
                name=node_data.get("name", node_id),
                description=node_data.get("description", ""),
                x=node_data.get("x", 0),
                y=node_data.get("y", 0)
            )
        
        # 加载边
        self.edges = [tuple(edge) for edge in data.get("edges", [])]
        
        # 构建邻接表
        for node1, node2 in self.edges:
            if node1 not in self.adjacency:
                self.adjacency[node1] = []
            if node2 not in self.adjacency:
                self.adjacency[node2] = []
            self.adjacency[node1].append(node2)
            self.adjacency[node2].append(node1)
    
    def get_neighbors(self, node_id: str) -> List[str]:
        """获取节点的邻居"""
        return self.adjacency.get(node_id, [])
    
    def get_node(self, node_id: str) -> Optional[Node]:
        """获取节点"""
        return self.nodes.get(node_id)


class AStarPathfinder:
    """A*路径规划器"""
    
    def __init__(self, graph: BuildingGraph):
        self.graph = graph
    
    def heuristic(self, node1_id: str, node2_id: str) -> float:
        """
        启发式函数：计算两节点之间的估计距离
        使用欧几里得距离 + 楼层惩罚
        """
        node1 = self.graph.get_node(node1_id)
        node2 = self.graph.get_node(node2_id)
        
        if not node1 or not node2:
            return float('inf')
        
        # 欧几里得距离
        dx = node1.x - node2.x
        dy = node1.y - node2.y
        euclidean = math.sqrt(dx * dx + dy * dy)
        
        # 楼层差异惩罚（基于 1400px 坐标空间调整）
        floor_diff = self._floor_distance(node1.floor, node2.floor)
        floor_penalty = floor_diff * 350  # 调整为 350 (约 1/4 的坐标空间)
        
        return euclidean + floor_penalty
    
    def _floor_distance(self, floor1: str, floor2: str) -> int:
        """计算楼层差异"""
        try:
            f1 = int(floor1.replace("F", ""))
            f2 = int(floor2.replace("F", ""))
            return abs(f1 - f2)
        except:
            return 0
    
    def edge_cost(self, from_id: str, to_id: str) -> float:
        """
        计算边的代价
        不同类型的边有不同的代价
        """
        from_node = self.graph.get_node(from_id)
        to_node = self.graph.get_node(to_id)
        
        if not from_node or not to_node:
            return float('inf')
        
        # 基础距离
        dx = from_node.x - to_node.x
        dy = from_node.y - to_node.y
        distance = math.sqrt(dx * dx + dy * dy)
        
        # 根据节点类型调整代价
        type_costs = {
            "stairs": 2.0,      # 走楼梯代价较高
            "elevator": 1.5,    # 电梯代价适中
            "corridor": 1.0,    # 走廊代价最低
            "room": 1.0,        # 房间
            "entrance": 1.0     # 入口
        }
        
        multiplier = type_costs.get(to_node.type, 1.0)
        
        # 如果跨楼层，增加额外代价（基于 1400px 坐标空间调整）
        if from_node.floor != to_node.floor:
            floor_diff = self._floor_distance(from_node.floor, to_node.floor)
            distance += floor_diff * 200  # 调整为 200 (约 1/7 的坐标空间)
        
        return distance * multiplier
    
    def find_path(self, start_id: str, goal_id: str) -> Optional[List[str]]:
        """
        A*算法寻找最短路径
        
        Args:
            start_id: 起点节点ID
            goal_id: 终点节点ID
        
        Returns:
            路径节点ID列表，如果找不到则返回None
        """
        if start_id not in self.graph.nodes or goal_id not in self.graph.nodes:
            return None
        
        # 优先队列: (f_score, counter, node_id)
        counter = 0
        open_set = [(0, counter, start_id)]
        
        # 记录每个节点的来源
        came_from: Dict[str, str] = {}
        
        # g_score: 从起点到当前节点的实际代价
        g_score: Dict[str, float] = {start_id: 0}
        
        # f_score: g_score + 启发式估计
        f_score: Dict[str, float] = {start_id: self.heuristic(start_id, goal_id)}
        
        # 已访问的节点
        closed_set = set()
        
        while open_set:
            _, _, current = heapq.heappop(open_set)
            
            if current in closed_set:
                continue
            
            if current == goal_id:
                # 重建路径
                return self._reconstruct_path(came_from, current)
            
            closed_set.add(current)
            
            for neighbor in self.graph.get_neighbors(current):
                if neighbor in closed_set:
                    continue
                
                tentative_g = g_score[current] + self.edge_cost(current, neighbor)
                
                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score[neighbor] = tentative_g + self.heuristic(neighbor, goal_id)
                    
                    counter += 1
                    heapq.heappush(open_set, (f_score[neighbor], counter, neighbor))
        
        return None  # 没找到路径
    
    def _reconstruct_path(self, came_from: Dict[str, str], current: str) -> List[str]:
        """重建路径"""
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        path.reverse()
        return path
    
    def calculate_path_distance(self, path: List[str]) -> float:
        """
        计算路径的总距离
        
        Args:
            path: 路径节点ID列表
            
        Returns:
            总距离（像素单位）
        """
        if not path or len(path) < 2:
            return 0.0
        
        total_distance = 0.0
        for i in range(len(path) - 1):
            total_distance += self.edge_cost(path[i], path[i + 1])
        
        return total_distance
    
    def get_path_details(self, path: List[str]) -> List[dict]:
        """
        获取路径详细信息
        
        Args:
            path: 路径节点ID列表
            
        Returns:
            每段路径的详细信息列表
        """
        if not path or len(path) < 2:
            return []
        
        details = []
        for i in range(len(path) - 1):
            from_id = path[i]
            to_id = path[i + 1]
            
            from_node = self.graph.get_node(from_id)
            to_node = self.graph.get_node(to_id)
            
            if not from_node or not to_node:
                continue
            
            distance = self.edge_cost(from_id, to_id)
            
            details.append({
                "step": i + 1,
                "from": from_id,
                "to": to_id,
                "from_floor": from_node.floor,
                "to_floor": to_node.floor,
                "distance": distance,
                "action": "elevator" if "elevator" in to_id else "stairs" if "stairs" in to_id else "walk"
            })
        
        return details


class NavigationGuide:
    """导航指引生成器"""
    
    def __init__(self, graph: BuildingGraph):
        self.graph = graph
    
    def generate_instructions(self, path: List[str]) -> List[dict]:
        """
        根据路径生成导航指令
        
        Returns:
            导航指令列表，每条指令包含:
            - step: 步骤编号
            - from_node: 起始节点
            - to_node: 目标节点
            - action: 动作类型
            - instruction: 自然语言指令
        """
        if not path or len(path) < 2:
            return []
        
        instructions = []
        
        for i in range(len(path) - 1):
            from_node = self.graph.get_node(path[i])
            to_node = self.graph.get_node(path[i + 1])
            
            if not from_node or not to_node:
                continue
            
            action, instruction = self._generate_step_instruction(from_node, to_node)
            
            instructions.append({
                "step": i + 1,
                "from_node": from_node.id,
                "to_node": to_node.id,
                "from_name": from_node.name,
                "to_name": to_node.name,
                "action": action,
                "instruction": instruction
            })
        
        return instructions
    
    def _generate_step_instruction(self, from_node: Node, to_node: Node) -> Tuple[str, str]:
        """生成单步导航指令"""
        
        # 入口进入
        if from_node.type == "entrance":
            return "enter", f"从{from_node.name}进入"
        
        # 使用楼梯上楼/下楼
        if to_node.type == "stairs" and from_node.floor != to_node.floor:
            floor_diff = self._floor_distance(from_node.floor, to_node.floor)
            if floor_diff > 0:
                return "stairs_up", f"前往{from_node.name}，上至{to_node.floor}"
            else:
                return "stairs_down", f"前往{from_node.name}，下至{to_node.floor}"
        
        # 使用电梯
        if to_node.type == "elevator" and from_node.floor != to_node.floor:
            return "elevator", f"乘坐电梯至{to_node.floor}"
        
        # 到达房间
        if to_node.type == "room":
            return "arrive", f"到达{to_node.name}（{to_node.description}）"
        
        # 沿走廊前行
        if to_node.type == "corridor":
            return "walk", f"沿{to_node.name}前行"
        
        # 默认
        return "move", f"前往{to_node.name}"
    
    def _floor_distance(self, floor1: str, floor2: str) -> int:
        """计算楼层差异"""
        try:
            f1 = int(floor1.replace("F", ""))
            f2 = int(floor2.replace("F", ""))
            return f2 - f1
        except:
            return 0


def load_building_data(filepath: str) -> dict:
    """加载建筑数据文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


# 测试代码
if __name__ == "__main__":
    # 加载数据
    data = load_building_data("../data/wencui_building.json")
    
    # 构建图
    graph = BuildingGraph(data)
    
    # 创建路径规划器
    pathfinder = AStarPathfinder(graph)
    
    # 测试路径规划
    start = "entrance_east_1F"
    goal = "D402"
    
    path = pathfinder.find_path(start, goal)
    
    if path:
        print(f"路径: {' → '.join(path)}")
        
        # 生成导航指令
        guide = NavigationGuide(graph)
        instructions = guide.generate_instructions(path)
        
        print("\n导航指令:")
        for inst in instructions:
            print(f"{inst['step']}. {inst['instruction']}")
    else:
        print("未找到路径")

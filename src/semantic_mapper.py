"""
语义映射模块
将用户自然语言输入映射到系统节点ID
支持规则匹配和LLM增强（可扩展）
"""

import json
import re
from typing import Optional, Dict, List
from difflib import SequenceMatcher


class SemanticMapper:
    """语义映射器"""
    
    def __init__(self, mapping_data: dict, building_nodes: dict):
        self.semantic_mappings = mapping_data.get("semantic_mappings", {})
        self.location_keywords = mapping_data.get("location_keywords", {})
        self.floor_descriptions = mapping_data.get("floor_descriptions", {})
        self.building_nodes = building_nodes
        
        # 构建反向映射（节点ID到名称）
        self.node_names = {}
        for node_id, node_data in building_nodes.items():
            self.node_names[node_id] = node_data.get("name", node_id)
    
    def parse_target(self, user_input: str) -> Optional[dict]:
        """
        解析用户输入的目标
        
        Args:
            user_input: 用户输入（如 "教务办公室"、"D402"、"我要去教务"）
        
        Returns:
            解析结果字典:
            - node_id: 目标节点ID
            - node_name: 节点名称
            - floor: 楼层
            - type: 节点类型
            - description: 描述
            - match_method: 匹配方式
        """
        user_input = user_input.strip()
        
        # 方法1: 直接房间号匹配
        result = self._match_room_number(user_input)
        if result:
            return result
        
        # 方法2: 语义映射匹配
        result = self._match_semantic(user_input)
        if result:
            return result
        
        # 方法3: 节点名称匹配
        result = self._match_node_name(user_input)
        if result:
            return result
        
        # 方法4: 模糊匹配
        result = self._fuzzy_match(user_input)
        if result:
            return result
        
        return None
    
    def parse_location(self, user_input: str) -> Optional[dict]:
        """
        解析位置关键词
        
        Args:
            user_input: 用户输入（如 "东门"、"一层大厅"、"A102"）
        
        Returns:
            解析结果字典
        """
        user_input = user_input.strip()
        
        # 直接匹配位置关键词
        for keyword, node_id in self.location_keywords.items():
            if keyword in user_input:
                return self._build_result(node_id, "location_keyword")
        
        # 房间号匹配
        result = self._match_room_number(user_input)
        if result:
            return result
        
        # 语义映射匹配
        result = self._match_semantic(user_input)
        if result:
            return result
        
        # 节点名称匹配
        result = self._match_node_name(user_input)
        if result:
            return result
        
        # 模糊匹配位置关键词
        for keyword, node_id in self.location_keywords.items():
            if self._similarity(user_input, keyword) > 0.7:
                return self._build_result(node_id, "fuzzy_location")
        
        # 模糊匹配
        result = self._fuzzy_match(user_input)
        if result:
            return result
        
        return None
    
    def _match_room_number(self, user_input: str) -> Optional[dict]:
        """匹配房间号"""
        # 提取可能的房间号
        room_pattern = r'[A-Z]\d{3}'
        matches = re.findall(room_pattern, user_input.upper())
        
        for match in matches:
            if match in self.building_nodes:
                return self._build_result(match, "room_number")
        
        return None
    
    def _match_semantic(self, user_input: str) -> Optional[dict]:
        """语义映射匹配"""
        # 完全匹配
        if user_input in self.semantic_mappings:
            return self._build_result(self.semantic_mappings[user_input], "semantic_exact")
        
        # 包含匹配
        for keyword, node_id in self.semantic_mappings.items():
            if keyword in user_input:
                return self._build_result(node_id, "semantic_contains")
        
        return None
    
    def _match_node_name(self, user_input: str) -> Optional[dict]:
        """节点名称匹配"""
        for node_id, node_name in self.node_names.items():
            if node_name == user_input:
                return self._build_result(node_id, "node_name_exact")
            if node_name in user_input:
                return self._build_result(node_id, "node_name_contains")
        
        return None
    
    def _fuzzy_match(self, user_input: str) -> Optional[dict]:
        """模糊匹配"""
        best_match = None
        best_score = 0
        
        # 在所有可能的映射中搜索
        all_targets = {}
        all_targets.update(self.semantic_mappings)
        all_targets.update(self.location_keywords)
        
        for keyword, node_id in all_targets.items():
            score = self._similarity(user_input, keyword)
            if score > best_score and score > 0.5:
                best_score = score
                best_match = node_id
        
        if best_match:
            return self._build_result(best_match, f"fuzzy_match({best_score:.2f})")
        
        return None
    
    def _build_result(self, node_id: str, match_method: str) -> dict:
        """构建结果字典"""
        node_data = self.building_nodes.get(node_id, {})
        
        return {
            "node_id": node_id,
            "node_name": node_data.get("name", node_id),
            "floor": node_data.get("floor", "未知"),
            "type": node_data.get("type", "未知"),
            "description": node_data.get("description", ""),
            "match_method": match_method
        }
    
    def _similarity(self, s1: str, s2: str) -> float:
        """计算字符串相似度"""
        return SequenceMatcher(None, s1, s2).ratio()
    
    def get_all_targets(self) -> List[dict]:
        """获取所有可用的目标"""
        targets = []
        
        # 从语义映射中获取
        for keyword, node_id in self.semantic_mappings.items():
            if node_id not in [t["node_id"] for t in targets]:
                result = self._build_result(node_id, "semantic")
                result["keywords"] = [k for k, v in self.semantic_mappings.items() if v == node_id]
                targets.append(result)
        
        # 从房间节点中获取
        for node_id, node_data in self.building_nodes.items():
            if node_data.get("type") == "room":
                if node_id not in [t["node_id"] for t in targets]:
                    targets.append(self._build_result(node_id, "room_node"))
        
        return targets
    
    def get_all_locations(self) -> List[dict]:
        """获取所有可用的起点位置"""
        locations = []
        
        for keyword, node_id in self.location_keywords.items():
            if node_id not in [l["node_id"] for l in locations]:
                locations.append(self._build_result(node_id, "location"))
        
        # 添加所有入口
        for node_id, node_data in self.building_nodes.items():
            if node_data.get("type") == "entrance":
                if node_id not in [l["node_id"] for l in locations]:
                    locations.append(self._build_result(node_id, "entrance_node"))
        
        return locations


def load_mapping_data(filepath: str) -> dict:
    """加载语义映射数据"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


# 测试代码
if __name__ == "__main__":
    # 加载数据
    mapping_data = load_mapping_data("../data/semantic_mapping.json")
    building_data = json.load(open("../data/wencui_building.json", 'r', encoding='utf-8'))
    
    # 创建映射器
    mapper = SemanticMapper(mapping_data, building_data["nodes"])
    
    # 测试
    test_inputs = [
        "教务办公室",
        "D402",
        "我要去教务",
        "东门",
        "会议室在哪",
        "老师办公室"
    ]
    
    print("=== 目标解析测试 ===")
    for inp in test_inputs:
        result = mapper.parse_target(inp)
        if result:
            print(f"\n输入: {inp}")
            print(f"  → 节点: {result['node_id']} ({result['node_name']})")
            print(f"  → 楼层: {result['floor']}")
            print(f"  → 匹配方式: {result['match_method']}")
        else:
            print(f"\n输入: {inp} → 无法识别")
    
    print("\n=== 所有可用目标 ===")
    targets = mapper.get_all_targets()
    for t in targets[:5]:  # 只显示前5个
        print(f"  {t['node_name']} ({t['floor']}) - {t['description']}")

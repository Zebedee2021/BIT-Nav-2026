"""
大模型导航助手 - 集成阿里通义千问 API
实现自然语言理解、导航指令优化、多轮对话等功能
"""

import os
import json
import requests
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class NavigationIntent:
    """导航意图解析结果"""
    destination: str  # 目的地描述
    confidence: float  # 置信度
    node_id: Optional[str] = None  # 匹配到的节点ID
    floor: Optional[str] = None  # 楼层
    reasoning: str = ""  # 推理过程


class QwenNavigator:
    """通义千问导航助手"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化通义千问导航助手
        
        Args:
            api_key: 阿里云 API Key，如果不提供则从环境变量获取
        """
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError("请提供 API Key 或设置 DASHSCOPE_API_KEY 环境变量")
        
        self.base_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
        self.model = "qwen-turbo"  # 使用通义千问 Turbo 模型
        
        # 对话历史（用于多轮对话）
        self.conversation_history: List[Dict[str, str]] = []
    
    def _call_api(self, prompt: str, system_prompt: str = "") -> str:
        """
        调用通义千问 API
        
        Args:
            prompt: 用户输入
            system_prompt: 系统提示词
            
        Returns:
            API 返回的文本
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # 添加对话历史
        messages.extend(self.conversation_history)
        
        # 添加当前用户输入
        messages.append({"role": "user", "content": prompt})
        
        data = {
            "model": self.model,
            "input": {
                "messages": messages
            },
            "parameters": {
                "result_format": "message",
                "max_tokens": 1500,
                "temperature": 0.7,
                "top_p": 0.8
            }
        }
        
        try:
            response = requests.post(
                self.base_url,
                headers=headers,
                json=data,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            
            # 提取回复内容
            if "output" in result and "choices" in result["output"]:
                content = result["output"]["choices"][0]["message"]["content"]
                
                # 更新对话历史
                self.conversation_history.append({"role": "user", "content": prompt})
                self.conversation_history.append({"role": "assistant", "content": content})
                
                # 限制历史长度（保留最近10轮）
                if len(self.conversation_history) > 20:
                    self.conversation_history = self.conversation_history[-20:]
                
                return content
            else:
                return "抱歉，我无法理解您的请求。"
                
        except requests.exceptions.RequestException as e:
            return f"API 调用失败: {str(e)}"
        except Exception as e:
            return f"发生错误: {str(e)}"
    
    def parse_destination(self, user_input: str, building_nodes: Dict) -> NavigationIntent:
        """
        解析用户的导航意图
        
        Args:
            user_input: 用户输入，如"我要去教务处"
            building_nodes: 建筑节点信息
            
        Returns:
            NavigationIntent 对象
        """
        # 构建节点列表
        nodes_info = []
        for node_id, node in building_nodes.items():
            nodes_info.append(f"- {node_id}: {node.get('name', '')} ({node.get('floor', '')}) - {node.get('description', '')}")
        
        nodes_text = "\n".join(nodes_info[:30])  # 限制节点数量避免过长
        
        system_prompt = f"""你是文萃楼导航助手。请分析用户的导航请求，从以下节点中找出最匹配的目的地。

可用节点：
{nodes_text}

请用 JSON 格式回复：
{{
    "destination": "用户想去的地方",
    "node_id": "匹配的节点ID",
    "confidence": 0.95,
    "reasoning": "为什么匹配这个节点"
}}

如果无法确定，confidence 设为 0，node_id 设为 null。"""

        response = self._call_api(user_input, system_prompt)
        
        # 尝试解析 JSON
        try:
            # 提取 JSON 部分
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                result = json.loads(json_str)
                
                return NavigationIntent(
                    destination=result.get("destination", user_input),
                    confidence=result.get("confidence", 0),
                    node_id=result.get("node_id"),
                    floor=result.get("floor"),
                    reasoning=result.get("reasoning", "")
                )
        except json.JSONDecodeError:
            pass
        
        # 解析失败，返回默认值
        return NavigationIntent(
            destination=user_input,
            confidence=0,
            reasoning="无法解析意图"
        )
    
    def optimize_navigation_instruction(self, steps: List[Dict], style: str = "natural") -> str:
        """
        优化导航指令，生成更自然的描述
        
        Args:
            steps: 导航步骤列表
            style: 风格 (natural/verbose/concise)
            
        Returns:
            优化后的导航文本
        """
        steps_text = "\n".join([
            f"{i+1}. {step['instruction']} (从 {step['from_name']} 到 {step['to_name']})"
            for i, step in enumerate(steps)
        ])
        
        style_prompt = {
            "natural": "用自然、口语化的方式描述",
            "verbose": "详细描述，包含更多细节和提示",
            "concise": "简洁明了，只保留关键信息"
        }.get(style, "用自然的方式描述")
        
        prompt = f"""请将以下导航步骤转换为{style_prompt}：

{steps_text}

要求：
1. 像人类向导一样说话
2. 合并相似的步骤
3. 添加方位提示（如"左转"、"直走"）
4. 在关键节点给出提示

直接输出优化后的导航文本："""

        return self._call_api(prompt)
    
    def answer_question(self, question: str, context: Dict) -> str:
        """
        回答用户关于导航的问题
        
        Args:
            question: 用户问题
            context: 上下文信息（当前位置、目的地等）
            
        Returns:
            回答文本
        """
        context_text = json.dumps(context, ensure_ascii=False, indent=2)
        
        system_prompt = f"""你是文萃楼智能导航助手。请根据上下文回答用户问题。

当前上下文：
{context_text}

回答要求：
1. 简洁明了
2. 如果涉及导航，给出具体指引
3. 如果不确定，诚实说明
4. 保持友好和乐于助人的语气"""

        return self._call_api(question, system_prompt)
    
    def clear_history(self):
        """清空对话历史"""
        self.conversation_history = []


class LLMNavigationService:
    """LLM 导航服务（兼容现有系统的封装）"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.navigator = None
        try:
            self.navigator = QwenNavigator(api_key)
        except ValueError:
            pass  # 没有 API Key 时不报错
    
    def is_available(self) -> bool:
        """检查 LLM 服务是否可用"""
        return self.navigator is not None
    
    def find_destination(self, query: str, building_nodes: Dict) -> Optional[str]:
        """
        查找目的地节点ID
        
        Args:
            query: 用户查询
            building_nodes: 建筑节点
            
        Returns:
            节点ID 或 None
        """
        if not self.navigator:
            return None
        
        intent = self.navigator.parse_destination(query, building_nodes)
        
        if intent.confidence > 0.7 and intent.node_id:
            return intent.node_id
        
        return None
    
    def generate_natural_description(self, steps: List[Dict]) -> str:
        """生成自然语言导航描述"""
        if not self.navigator or not steps:
            return ""
        
        return self.navigator.optimize_navigation_instruction(steps)

"""
智能模型路由器
根据硬件等级+任务复杂度+生成模式，自动选择最优模型通道
"""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, List
from .hardware_detector import HardwareDetector, HardwareProfile, ComputeTier


class TaskComplexity(Enum):
    LIGHT = "light"         # 润色/分类/简单问答
    MEDIUM = "medium"       # 大纲生成/意图理解
    HEAVY = "heavy"         # 内容填充/多页生成
    MULTIMODAL = "multimodal" # 视觉反思/多模态理解


class GenerationMode(Enum):
    QUICK = "quick"
    COLLABORATIVE = "collaborative"
    FULL_CONTROL = "full_control"


@dataclass
class ModelRoute:
    """模型路由结果"""
    provider: str           # agnes / zhipu / ollama
    model_name: str
    url: Optional[str] = None
    estimated_cost: float = 0.0
    estimated_tokens: int = 0


class ModelRouter:
    """智能模型路由器"""
    
    # 4x4 路由矩阵 (硬件等级 x 任务复杂度)
    ROUTING_MATRIX = {
        ComputeTier.LIGHT: {
            TaskComplexity.LIGHT: ModelRoute("agnes", "agnes-2.0-flash"),
            TaskComplexity.MEDIUM: ModelRoute("agnes", "agnes-2.0-flash"),
            TaskComplexity.HEAVY: ModelRoute("zhipu", "glm-4-flash"),
            TaskComplexity.MULTIMODAL: ModelRoute("zhipu", "glm-4-flash"),
        },
        ComputeTier.MAINSTREAM: {
            TaskComplexity.LIGHT: ModelRoute("agnes", "agnes-2.0-flash"),
            TaskComplexity.MEDIUM: ModelRoute("agnes", "agnes-2.0-flash"),
            TaskComplexity.HEAVY: ModelRoute("agnes", "agnes-2.5-flash"),
            TaskComplexity.MULTIMODAL: ModelRoute("agnes", "agnes-2.5-flash"),
        },
        ComputeTier.ADVANCED: {
            TaskComplexity.LIGHT: ModelRoute("agnes", "agnes-2.0-flash"),
            TaskComplexity.MEDIUM: ModelRoute("agnes", "agnes-2.5-flash"),
            TaskComplexity.HEAVY: ModelRoute("agnes", "agnes-2.5-flash"),
            TaskComplexity.MULTIMODAL: ModelRoute("agnes", "agnes-image-2.1-flash"),
        },
        ComputeTier.PROFESSIONAL: {
            TaskComplexity.LIGHT: ModelRoute("agnes", "agnes-2.5-flash"),
            TaskComplexity.MEDIUM: ModelRoute("agnes", "agnes-2.5-flash"),
            TaskComplexity.HEAVY: ModelRoute("agnes", "agnes-2.5-flash"),
            TaskComplexity.MULTIMODAL: ModelRoute("agnes", "agnes-image-2.1-flash"),
        },
    }
    
    def __init__(self, hardware_profile: HardwareProfile):
        self.hardware = hardware_profile
    
    def route(self, task_complexity: TaskComplexity, mode: GenerationMode = GenerationMode.QUICK) -> ModelRoute:
        """根据任务复杂度和模式路由到最优模型"""
        matrix = self.ROUTING_MATRIX.get(self.hardware.tier, {})
        route = matrix.get(task_complexity)
        
        if route:
            return route
        
        # 降级策略：选择最轻量的模型
        light_routes = matrix.get(TaskComplexity.LIGHT)
        return light_routes or ModelRoute("agnes", "agnes-2.0-flash")
    
    def get_fallback_chain(self, base_route: ModelRoute) -> List[str]:
        """获取降级链"""
        if base_route.provider == "agnes":
            return ["agnes", "zhipu", "ollama"]
        elif base_route.provider == "zhipu":
            return ["zhipu", "agnes", "ollama"]
        else:
            return ["ollama", "agnes", "zhipu"]

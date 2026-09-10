"""
硬件检测模块
检测GPU/内存/CPU配置，自动划分算力等级
"""
import psutil
import platform
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ComputeTier(Enum):
    LIGHT = "light"              # 无独显/4GB以下显存
    MAINSTREAM = "mainstream"    # 6-8GB显存
    ADVANCED = "advanced"        # 12-16GB显存
    PROFESSIONAL = "professional" # 24GB+显存


@dataclass
class HardwareProfile:
    tier: ComputeTier
    gpu_vram_gb: float
    system_ram_gb: float
    cpu_cores: int
    cpu_model: str
    has_gpu: bool
    gpu_model: Optional[str] = None
    ollama_available: bool = False


class HardwareDetector:
    """硬件检测器"""
    
    @staticmethod
    def detect() -> HardwareProfile:
        """执行硬件检测"""
        # CPU信息
        cpu_model = platform.processor() or platform.machine()
        cpu_cores = psutil.cpu_count(logical=True)
        
        # 内存信息
        total_mem = psutil.virtual_memory().total
        total_memory_gb = round(total_mem / (1024**3), 1)
        
        # GPU信息
        has_gpu = False
        gpu_model = None
        gpu_memory_gb = 0.0
        
        try:
            import torch
            if torch.cuda.is_available():
                has_gpu = True
                gpu_model = torch.cuda.get_device_name(0)
                gpu_memory_gb = round(
                    torch.cuda.get_device_properties(0).total_mem / (1024**3), 1
                )
        except ImportError:
            pass
        
        # 算力分级
        tier = HardwareDetector._classify_tier(has_gpu, gpu_memory_gb, total_memory_gb)
        
        return HardwareProfile(
            tier=tier,
            gpu_vram_gb=gpu_memory_gb,
            system_ram_gb=total_memory_gb,
            cpu_cores=cpu_cores,
            cpu_model=cpu_model,
            has_gpu=has_gpu,
            gpu_model=gpu_model
        )
    
    @staticmethod
    def _classify_tier(has_gpu: bool, gpu_mem_gb: float, system_ram_gb: float) -> ComputeTier:
        """算力等级分类"""
        if has_gpu and gpu_mem_gb >= 24:
            return ComputeTier.PROFESSIONAL
        elif has_gpu and gpu_mem_gb >= 12:
            return ComputeTier.ADVANCED
        elif has_gpu and gpu_mem_gb >= 6:
            return ComputeTier.MAINSTREAM
        else:
            return ComputeTier.LIGHT
    
    @staticmethod
    def get_recommended_model(tier: ComputeTier) -> str:
        """根据算力等级返回推荐的本地模型"""
        models = {
            ComputeTier.PROFESSIONAL: "qwen3.5:32b",
            ComputeTier.ADVANCED: "qwen3:14b",
            ComputeTier.MAINSTREAM: "qwen3:8b",
            ComputeTier.LIGHT: "qwen3:4b",
        }
        return models.get(tier, "qwen3:4b")

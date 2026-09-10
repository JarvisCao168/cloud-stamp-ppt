"""
硬件检测路由
提供GPU/内存/CPU检测、算力分级等接口
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import platform
import psutil

from ...core.hardware_detector import HardwareDetector, ComputeTier
from ...core.config import settings

router = APIRouter()


class HardwareInfo(BaseModel):
    cpu_model: str
    cpu_cores: int
    total_memory_gb: float
    gpu_available: bool
    gpu_model: Optional[str] = None
    gpu_memory_gb: Optional[float] = None
    os_type: str
    tier: str  # 兼容前端期望的字段名
    compute_tier: str = ""  # 别名，实际值与 tier 相同
    recommended_model: str


class ModelRecommendation(BaseModel):
    tier: str
    local_model: str
    cloud_model: str
    reasoning: str


@router.get("/detect", response_model=HardwareInfo)
async def detect_hardware():
    """检测硬件配置并返回算力等级"""
    try:
        profile = HardwareDetector.detect()
        
        tier_value = profile.tier.value
        return HardwareInfo(
            cpu_model=profile.cpu_model,
            cpu_cores=profile.cpu_cores,
            total_memory_gb=profile.system_ram_gb,
            gpu_available=profile.has_gpu,
            gpu_model=profile.gpu_model,
            gpu_memory_gb=profile.gpu_vram_gb,
            os_type=platform.system(),
            tier=tier_value,
            compute_tier=tier_value,
            recommended_model=HardwareDetector.get_recommended_model(profile.tier)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"硬件检测失败: {str(e)}")


@router.get("/recommendations", response_model=list[ModelRecommendation])
async def get_recommendations():
    """获取所有算力等级的模型推荐"""
    recommendations = []
    for tier in ComputeTier:
        local_model = HardwareDetector.get_recommended_model(tier)
        recommendations.append(ModelRecommendation(
            tier=tier.value,
            local_model=local_model,
            cloud_model="agnes-2.0-flash",
            reasoning=f"{tier.value}等级推荐本地模型: {local_model}"
        ))
    return recommendations


@router.get("/tier/{tier}")
async def get_tier_info(tier: str):
    """获取特定算力等级的信息"""
    try:
        tier_enum = ComputeTier(tier)
        recommended = HardwareDetector.get_recommended_model(tier_enum)
        return {
            "tier": tier,
            "recommended_local_model": recommended,
            "suitable_for": _get_tier_capabilities(tier_enum)
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的算力等级")


def _get_tier_capabilities(tier: ComputeTier) -> list:
    """获取各等级的能力描述"""
    capabilities = {
        ComputeTier.LIGHT: ["简单文本生成", "基础润色", "轻量级任务"],
        ComputeTier.MAINSTREAM: ["大纲生成", "内容填充", "多页PPT生成"],
        ComputeTier.ADVANCED: ["复杂内容生成", "多轮对话", "创意写作"],
        ComputeTier.PROFESSIONAL: ["大规模内容处理", "多模态任务", "高精度生成"]
    }
    return capabilities.get(tier, [])

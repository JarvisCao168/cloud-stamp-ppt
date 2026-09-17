"""
云章PPT智能体系统 - 后端应用入口
FastAPI + CORS + 路由注册
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from app.core.config import settings
from app.core.hardware_detector import HardwareDetector
from app.core.model_router import ModelRouter
from app.db import init_db
from app.api.routes import hardware, generation, checkpoints, assets, export, quota, auth


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 初始化数据库（创建表 + 种子数据）
    await init_db()

    print(f"[云章] 启动中...")
    print(f"[云章] AI模型: {settings.agnes_model}")

    hardware_profile = HardwareDetector.detect()
    print(f"[云章] 硬件等级: {hardware_profile.tier.value}")

    yield

    print("[云章] 服务关闭")


app = FastAPI(
    title="云章PPT智能体系统",
    description="AI驱动的演示文稿智能操作系统",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(hardware.router, prefix="/api/hardware", tags=["硬件检测"])
app.include_router(generation.router, prefix="/api/generation", tags=["AI生成"])
# 协作 MVP: 同一 SSE 路由（含 collab_publish 广播）再注册到 /api/collab 前缀下
app.include_router(generation.router, prefix="/api/collab", tags=["协作MVP"])
app.include_router(checkpoints.router, prefix="/api/checkpoints", tags=["检查点管理"])
app.include_router(assets.router, prefix="/api/assets", tags=["设计资产"])
app.include_router(export.router, prefix="/api/export", tags=["导出服务"])
app.include_router(quota.router, prefix="/api/quota", tags=["积分额度"])
app.include_router(auth.router, prefix="/api/auth", tags=["用户认证"])

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "云章PPT智能体系统",
        "version": "1.0.0",
        "env": os.getenv("APP_ENV", "development")
    }

@app.get("/")
async def root():
    return {
        "message": "欢迎使用云章PPT智能体系统",
        "docs": "/docs",
        "health": "/health"
    }

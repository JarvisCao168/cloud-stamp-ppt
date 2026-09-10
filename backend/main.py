"""云章PPT后端服务 — FastAPI 应用入口。

提供演示文稿生成、检查点管理、资产查询和多格式导出接口。
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import generation, export, assets, hardware

app = FastAPI(
    title="云章PPT API",
    description="演示文稿智能生成后端服务",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(generation.router, prefix="/api")
app.include_router(export.router, prefix="/api")
app.include_router(assets.router, prefix="/api")
app.include_router(hardware.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/")
async def root():
    return {"service": "cloud-stamp-ppt-backend", "status": "running"}

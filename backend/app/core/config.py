"""
全局配置管理
使用Pydantic Settings自动加载.env文件
"""
from pathlib import Path

from pydantic_settings import BaseSettings
from typing import List, Optional

# 项目根目录：config.py 位于 backend/app/core/，向上 4 层为 repo 根。
# 用作 .env 与相对路径的锚点，避免 CWD 漂移导致根目录重建 DB 等事故。
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# 数据库文件锚定在 repo 的 backend/ 下（0a1c75d 双DB统一后唯一权威库）
_DB_PATH = str(_PROJECT_ROOT / "backend" / "yunzhang.db")


def _anchor_db_url(raw: str) -> str:
    """把 sqlite 的 database_url 改为绝对路径。

    默认值 sqlite+aiosqlite:///./yunzhang.db 是 CWD 相对路径——uvicorn 从哪个目录
    启动就从哪个目录建库（历史事故：根目录 yunzhang.db 被重建）。这里统一锚定到
    backend/yunzhang.db 绝对路径；显式通过 DATABASE_URL 配置了非 sqlite 源（如 postgres）时原样保留。
    """
    if raw.startswith("sqlite"):
        return "sqlite+aiosqlite:///" + _DB_PATH
    return raw


class Settings(BaseSettings):
    # 应用配置
    app_name: str = "云章PPT智能体系统"
    debug: bool = True
    env: str = "development"
    
    # CORS配置
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    # AgnesAI配置
    agnes_api_key: str = ""
    agnes_base_url: str = "https://apihub.agnes-ai.com/v1"
    agnes_model: str = "agnes-2.0-flash"
    agnes_coding_model: str = "agnes-2.5-flash"
    
    # 智谱GLM配置
    zhipu_api_key: str = ""
    zhipu_base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    zhipu_model: str = "glm-4-flash"
    
    # 数据库配置（默认值由 _anchor_db_url 锚定到 backend/yunzhang.db 绝对路径，
    # 堵住 CWD 漂移重建根目录 DB 的风险）
    database_url: str = "sqlite+aiosqlite:///./yunzhang.db"
    redis_url: str = "redis://localhost:6379/0"
    
    # 文件存储
    export_dir: str = "./outputs"
    upload_dir: str = "./uploads"
    
    # AI超时设置
    ai_timeout: int = 120
    ai_retry_count: int = 3

    # 免费额度配置（每日生成次数上限，可通过环境变量 FREE_DAILY_LIMIT 覆盖）
    free_daily_limit: int = 10
    
    class Config:
        # .env 锚定在 repo 根目录，不随启动 CWD 漂移
        env_file = str(_PROJECT_ROOT / ".env")
        env_file_encoding = "utf-8"
        case_sensitive = True


# 全局配置实例
_raw = Settings()
_raw.database_url = _anchor_db_url(_raw.database_url)
settings = _raw

"""
全局配置管理
使用Pydantic Settings自动加载.env文件
"""
from pydantic_settings import BaseSettings
from typing import List, Optional


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
    
    # 数据库配置
    database_url: str = "sqlite+aiosqlite:///./yunzhang.db"
    redis_url: str = "redis://localhost:6379/0"
    
    # 文件存储
    export_dir: str = "./outputs"
    upload_dir: str = "./uploads"
    
    # AI超时设置
    ai_timeout: int = 120
    ai_retry_count: int = 3
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# 全局配置实例
settings = Settings()

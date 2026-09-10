"""
Ollama本地模型客户端
"""
import httpx
import asyncio
from typing import Dict, Any, Optional, List
from .config import settings


class OllamaClient:
    """Ollama客户端"""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or settings.agnes_base_url.replace("apihub.agnes-ai.com", "localhost:11434")
    
    async def generate(self, prompt: str, model: str = None, **kwargs) -> str:
        """生成文本"""
        model = model or "qwen3:8b"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    **kwargs
                },
                timeout=settings.ai_timeout
            )
            response.raise_for_status()
            return response.json().get("response", "")
    
    async def chat(self, messages: List[Dict], model: str = None, **kwargs) -> str:
        """聊天接口"""
        model = model or "qwen3:8b"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False,
                    **kwargs
                },
                timeout=settings.ai_timeout
            )
            response.raise_for_status()
            return response.json().get("message", {}).get("content", "")
    
    async def list_models(self) -> List[str]:
        """列出可用模型"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            return [m["name"] for m in response.json().get("models", [])]
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except:
            return False


# 全局实例
ollama_client = OllamaClient()

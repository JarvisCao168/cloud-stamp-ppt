"""
智谱GLM API客户端（备用）
"""
import httpx
import json
from typing import Dict, Any, Optional, List
from .config import settings


class ZhipuClient:
    """智谱GLM客户端"""
    
    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key or settings.zhipu_api_key
        self.base_url = base_url or settings.zhipu_base_url
    
    async def chat(self, messages: List[Dict], model: str = None, **kwargs) -> Dict[str, Any]:
        """发送聊天请求"""
        model = model or settings.zhipu_model
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            **kwargs
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=settings.ai_timeout
            )
            response.raise_for_status()
            return response.json()
    
    async def generate(self, prompt: str, model: str = None, system_prompt: str = None, **kwargs) -> str:
        """生成文本"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        result = await self.chat(messages, model=model, **kwargs)
        return result.get("choices", [{}])[0].get("message", {}).get("content", "")

    @property
    def is_available(self) -> bool:
        """检查API是否可用"""
        return bool(self.api_key) and len(self.api_key) > 10


# 全局实例
zhipu_client = ZhipuClient()

"""
AgnesAI API客户端
接入真实AI模型进行PPT生成
"""
import httpx
import json
from typing import Dict, Any, Optional, List
from .config import settings


class AgnesAIClient:
    """AgnesAI客户端"""
    
    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key or settings.agnes_api_key
        self.base_url = base_url or settings.agnes_base_url
    
    async def chat(self, messages: List[Dict], model: str = None, stream: bool = False, **kwargs) -> Dict[str, Any]:
        """发送聊天请求"""
        model = model or settings.agnes_model
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
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
        """生成文本（简化接口）"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        result = await self.chat(messages, model=model, **kwargs)
        return result.get("choices", [{}])[0].get("message", {}).get("content", "")
    
    async def generate_json(self, prompt: str, model: str = None, **kwargs) -> Dict:
        """生成JSON格式输出"""
        system_prompt = """You are a helpful assistant that returns JSON only. 
        Always output valid JSON without markdown formatting."""
        
        text = await self.generate(prompt, model=model, system_prompt=system_prompt, **kwargs)
        
        # 尝试解析JSON
        try:
            # 移除可能的markdown代码块
            text = text.strip()
            if text.startswith("```"):
                text = text.split("\n")[1]
                if text.endswith("```"):
                    text = text[:-3]
            return json.loads(text)
        except json.JSONDecodeError:
            # 返回原始文本作为兜底
            return {"raw": text}
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=10
                )
                return response.status_code == 200
        except:
            return False
    
    @property
    def is_available(self) -> bool:
        """检查API是否可用"""
        return bool(self.api_key) and self.api_key != "sk-wXCyourkeyhere"


# 全局实例
agnes_client = AgnesAIClient()

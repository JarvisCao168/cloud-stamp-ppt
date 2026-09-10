"""
AI生成路由
串联意图理解、大纲生成、内容填充、样式匹配等核心模块
提供极速/协作/全程掌控三种模式的API接口
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid
import json
import asyncio

from ...core.agnes_client import agnes_client
from ...core.zhipu_client import zhipu_client
from ...core.model_router import ModelRouter, TaskComplexity, GenerationMode
from ...core.hardware_detector import HardwareDetector
from ...core.checkpoint_engine import CheckpointEngine

router = APIRouter()

# 全局检查点引擎
checkpoint_engine = CheckpointEngine()

# 会话存储（生产环境应使用Redis）
sessions = {}


class GenerationRequest(BaseModel):
    """生成请求"""
    user_input: str
    mode: str = "quick"  # quick / collaborative / full_control
    extra_config: Optional[Dict[str, Any]] = None


class CheckpointAction(BaseModel):
    """检查点操作"""
    session_id: str
    checkpoint_id: str
    action: str  # confirm / edit / regenerate / select
    data: Optional[Dict[str, Any]] = None


class ExportRequest(BaseModel):
    """导出请求"""
    session_id: str
    format: str  # html / pdf / png / pptx
    quality: str = "hd"


class GenerationResponse(BaseModel):
    """生成响应"""
    session_id: str
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None
    checkpoints: Optional[List[Dict[str, Any]]] = None


# ========== PPT生成提示词模板 ==========

INTENT_PROMPT = """你是一个专业的PPT生成助手。请分析用户的输入，提取以下JSON格式的信息：
- topic: 演示文稿的主题
- audience: 目标受众
- tone: 整体基调 (如：专业、活泼、极简)
- page_count: 建议页数 (3-15)

用户输入：{user_input}

只返回JSON对象，不要包含Markdown格式或其他文字。"""

OUTLINE_PROMPT = """请为一份关于"{topic}"的演示文稿生成大纲。
受众是：{audience}
基调是：{tone}
建议页数：{page_count}

请返回一个JSON列表，每个元素代表一页PPT，包含：
- title: 页面标题
- content: 主要内容要点（列表形式）
- layout: 建议布局 (title-content/two-column/quote/etc)

只返回JSON数组，不要包含其他文字。"""

CONTENT_PROMPT = """请为以下PPT页面生成详细内容：

标题：{title}
布局：{layout}
主题：{topic}
受众：{audience}

请返回JSON格式：
{{
  "title": "页面标题",
  "bullet_points": ["要点1", "要点2", "要点3"],
  "speaker_notes": "演讲者备注"
}}

只返回JSON，不要包含其他文字。"""

NUMBERING_STYLE_PROMPT = """请根据以下PPT大纲内容，推荐最适合的序号样式。

主题：{topic}
受众：{audience}
基调：{tone}
大纲结构（章节数）：{section_count}
是否有步骤/流程内容：{has_steps}

可选的序号样式类型：
- numeric-dot: 数字加点（1. 2. 3.）- 商务报告
- numeric-paren: 数字加括号（(1) (2) (3)）- 学术文档
- chinese-clause: 中文顿号（一、二、三）- 正式公文
- chinese-paren: 中文括号（（一）（二）（三））- 二级标题
- level-nested: 层级序号（1.1 1.1.1）- 技术文档
- graphic-circle: 图形符号（● ○ ■）- 创意视觉
- icon-check: 箭头对勾（→ ✓）- 流程图
- english-alpha: 英文字母（A. B. C.）- 英文演示
- step-arrow: 步骤箭头链（▶▶▶）- 时间线

请返回JSON：
{{
  "primary_style_id": "选中的主要序号样式ID",
  "secondary_style_id": "子项使用的次要序号样式ID，或null",
  "reason": "选择理由"
}}

只返回JSON，不要包含其他文字。"""

STYLE_PROMPT = """请为这份PPT推荐3套视觉风格方案，每套包含：
- name: 风格名称
- description: 风格描述
- colors: {{primary: "#xxx", secondary: "#xxx", background: "#xxx", text: "#xxx"}}
- font_pairing: {{heading: "字体名", body: "字体名"}}

返回JSON数组格式。"""


# ========== 核心生成服务 ==========

class GenerationService:
    """生成服务"""
    
    def __init__(self):
        self.hardware_detector = HardwareDetector()
        self.model_router = None
    
    async def start_generation(self, request: GenerationRequest) -> GenerationResponse:
        """开始生成PPT"""
        session_id = str(uuid.uuid4())
        
        # 检测硬件
        hardware_profile = self.hardware_detector.detect()
        self.model_router = ModelRouter(hardware_profile)
        
        # 根据模式执行不同流水线
        if request.mode == "quick":
            result = await self._quick_mode_pipeline(session_id, request.user_input, request.extra_config)
            return GenerationResponse(
                session_id=session_id,
                status="completed",
                message="极速模式生成完成",
                data=result
            )
        elif request.mode == "collaborative":
            result = await self._collaborative_mode_pipeline(session_id, request.user_input, request.extra_config)
            return result
        elif request.mode == "full_control":
            result = await self._full_control_mode_pipeline(session_id, request.user_input, request.extra_config)
            return result
        else:
            raise HTTPException(status_code=400, detail=f"不支持的生成模式: {request.mode}")
    
    async def _quick_mode_pipeline(self, session_id: str, user_input: str, config: dict) -> dict:
        """极速模式流水线"""
        # 1. 意图理解
        intent = await self._intent_analysis(user_input)

        # 2. 大纲生成
        outline = await self._generate_outline(intent)

        # 3. 内容填充
        slides = await self._fill_content(outline, intent)

        # 4. 序号样式推荐（新增）
        numbering_style = await self._recommend_numbering_style(intent, outline)

        # 5. 样式匹配
        style = await self._match_style(intent)

        # 保存会话
        sessions[session_id] = {
            "intent": intent,
            "outline": outline,
            "slides": slides,
            "numbering_style": numbering_style,
            "style": style,
            "mode": "quick"
        }

        return {
            "intent": intent,
            "outline": outline,
            "slides": slides,
            "numbering_style": numbering_style,
            "style": style
        }
    
    async def _intent_analysis(self, user_input: str) -> dict:
        """意图理解"""
        prompt = INTENT_PROMPT.format(user_input=user_input)
        
        # 使用AgnesAI
        if agnes_client.is_available:
            try:
                result = await agnes_client.generate_json(prompt)
                if "topic" in result:
                    return result
            except Exception as e:
                print(f"AgnesAI failed: {e}")
        
        # 降级到智谱GLM
        if zhipu_client.is_available:
            try:
                result = await zhipu_client.generate(prompt)
                return json.loads(result)
            except Exception as e:
                print(f"Zhipu failed: {e}")
        
        # 兜底返回默认值
        return {
            "topic": user_input,
            "audience": "通用",
            "tone": "专业",
            "page_count": 5
        }
    
    async def _generate_outline(self, intent: dict) -> list:
        """大纲生成"""
        prompt = OUTLINE_PROMPT.format(**intent)
        
        if agnes_client.is_available:
            try:
                result = await agnes_client.generate_json(prompt)
                if isinstance(result, list):
                    return result
            except Exception as e:
                print(f"AgnesAI outline failed: {e}")
        
        # 返回默认大纲
        return [
            {"title": "引言", "content": ["背景介绍", "问题陈述"], "layout": "title-content"},
            {"title": "主体", "content": ["核心观点1", "核心观点2", "核心观点3"], "layout": "two-column"},
            {"title": "结论", "content": ["总结", "展望"], "layout": "quote"}
        ]
    
    async def _fill_content(self, outline: list, intent: dict) -> list:
        """内容填充"""
        slides = []
        for i, item in enumerate(outline):
            slide = {
                "index": i + 1,
                "title": item.get("title", f"第{i+1}页"),
                "content": item.get("content", []),
                "layout": item.get("layout", "title-content"),
                "speaker_notes": ""
            }
            slides.append(slide)
        return slides
    
    async def _recommend_numbering_style(self, intent: dict, outline: list) -> dict:
        """根据大纲内容推荐序号样式"""
        section_count = len(outline)
        # 检测是否包含步骤/流程内容
        has_steps = any(
            kw in " ".join(item.get("title", "") + " " + " ".join(item.get("content", [])) for item in outline)
            for kw in ["步骤", "流程", "阶段", "阶段", "流程", "实现路径", "实施步骤"]
        )

        prompt = NUMBERING_STYLE_PROMPT.format(
            topic=intent.get("topic", ""),
            audience=intent.get("audience", ""),
            tone=intent.get("tone", ""),
            section_count=section_count,
            has_steps="是" if has_steps else "否",
        )

        if agnes_client.is_available:
            try:
                result = await agnes_client.generate_json(prompt)
                if isinstance(result, dict) and "primary_style_id" in result:
                    return result
            except Exception as e:
                print(f"[NumberingStyle] AgnesAI failed: {e}")

        # 默认推荐：商务场景用数字加点，学术用数字加括号
        default = "numeric-dot" if intent.get("tone") == "正式" else "numeric-dot"
        return {"primary_style_id": default, "secondary_style_id": None, "reason": "默认推荐"}

    async def _match_style(self, intent: dict) -> dict:
        """样式匹配"""
        prompt = STYLE_PROMPT

        if agnes_client.is_available:
            try:
                result = await agnes_client.generate_json(prompt)
                if isinstance(result, list) and len(result) > 0:
                    return result[0]
            except Exception:
                pass

        # 返回默认样式
        return {
            "name": "现代简约",
            "colors": {"primary": "#2563eb", "secondary": "#64748b", "background": "#ffffff", "text": "#1e293b"},
            "font_pairing": {"heading": "微软雅黑", "body": "微软雅黑"}
        }
    
    async def _collaborative_mode_pipeline(self, session_id: str, user_input: str, config: dict) -> GenerationResponse:
        """协作模式流水线"""
        # 创建会话
        checkpoint_engine.create_session(session_id, "collaborative")
        
        # 意图理解
        intent = await self._intent_analysis(user_input)
        
        # 大纲生成
        outline = await self._generate_outline(intent)
        
        # 暂停在第一个检查点
        checkpoint = await checkpoint_engine.pause_at_checkpoint(session_id)
        
        sessions[session_id] = {
            "intent": intent,
            "outline": outline,
            "mode": "collaborative"
        }
        
        return GenerationResponse(
            session_id=session_id,
            status="checkpoint",
            message="请确认大纲",
            checkpoints=[{
                "id": checkpoint.id,
                "title": checkpoint.title,
                "description": checkpoint.description,
                "data": {"outline": outline}
            }]
        )
    
    async def _full_control_mode_pipeline(self, session_id: str, user_input: str, config: dict) -> GenerationResponse:
        """全程掌控模式流水线"""
        checkpoint_engine.create_session(session_id, "full_control")
        
        intent = await self._intent_analysis(user_input)
        outline = await self._generate_outline(intent)
        
        checkpoint = await checkpoint_engine.pause_at_checkpoint(session_id)
        
        sessions[session_id] = {
            "intent": intent,
            "outline": outline,
            "mode": "full_control"
        }
        
        return GenerationResponse(
            session_id=session_id,
            status="checkpoint",
            message="请确认大纲结构",
            checkpoints=[{
                "id": checkpoint.id,
                "title": checkpoint.title,
                "description": checkpoint.description,
                "data": {"outline": outline}
            }]
        )
    
    async def handle_checkpoint_action(self, action: CheckpointAction) -> dict:
        """处理检查点操作"""
        success = await checkpoint_engine.record_decision(
            action.session_id,
            action.action,
            action.data
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="会话不存在或检查点已完成")
        
        session = checkpoint_engine.get_session(action.session_id)
        
        return {
            "status": "recorded",
            "session_id": action.session_id,
            "next_checkpoint": session["checkpoints"][session["current_index"]].id if session["current_index"] < len(session["checkpoints"]) else None
        }


# 全局服务实例
generation_service = GenerationService()


# ========== API端点 ==========

@router.post("/create", response_model=GenerationResponse)
async def create_generation(request: GenerationRequest):
    """创建生成任务"""
    # 先验证模式，再执行生成（避免被外层try/except吞掉）
    if request.mode not in ("quick", "collaborative", "full_control"):
        raise HTTPException(status_code=400, detail=f"不支持的生成模式: {request.mode}")
    try:
        return await generation_service.start_generation(request)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")


@router.post("/checkpoint/{session_id}/{checkpoint_id}/action")
async def checkpoint_action(session_id: str, checkpoint_id: str, action: CheckpointAction):
    """处理检查点操作"""
    action.session_id = session_id
    action.checkpoint_id = checkpoint_id
    return await generation_service.handle_checkpoint_action(action)


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    """获取会话状态"""
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    return session

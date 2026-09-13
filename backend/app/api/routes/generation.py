"""
AI生成路由
串联意图理解、大纲生成、内容填充、样式匹配等核心模块
提供极速/协作/全程掌控三种模式的API接口
"""
from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, AsyncGenerator
import uuid
import json
import asyncio
import time

from ...core.agnes_client import agnes_client
from ...core.zhipu_client import zhipu_client
from ...core.model_router import ModelRouter, TaskComplexity, GenerationMode
from ...core.hardware_detector import HardwareDetector
from ...core.checkpoint_engine import CheckpointEngine
from ...core.quota import check_quota, record_usage
from ...core.config import settings

router = APIRouter()

# 全局检查点引擎
checkpoint_engine = CheckpointEngine()

# 会话存储（生产环境应使用Redis）
sessions = {}

# ========== 协作 MVP: SSE 实时广播 ==========
# 事件订阅表：session_id -> 所有在线订阅者的 asyncio.Queue
_collab_subscribers: Dict[str, List[asyncio.Queue]] = {}
# 每个会话的最近 100 条事件，新订阅者 join 时回放（避免错过 join 前的进度）
_collab_event_log: Dict[str, List[Dict[str, Any]]] = {}
_COLLAB_MAX_LOG = 100


def _sse_format(event: str, data: Dict[str, Any]) -> str:
    """格式化单条 SSE 事件（event: + data: JSON）"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def collab_publish(session_id: str, event: str, payload: Dict[str, Any]) -> None:
    """发布协作事件：写入会话事件日志并推送给所有在线订阅者（非阻塞）"""
    entry = {"ts": time.time(), "event": event, "data": payload}
    log = _collab_event_log.setdefault(session_id, [])
    log.append(entry)
    if len(log) > _COLLAB_MAX_LOG:
        log.pop(0)
    for q in _collab_subscribers.get(session_id, []):
        q.put_nowait(entry)


def _collab_snapshot(session_id: str) -> Dict[str, Any]:
    """会话当前状态快照（发给新 join 的订阅者，让其恢复上下文）"""
    session = sessions.get(session_id) or {}
    return {
        "session_id": session_id,
        "mode": session.get("mode"),
        "keep_original": session.get("keep_original"),
        "slides_count": len(session.get("slides") or []),
    }


@router.get("/stream")
async def collab_stream(
    session_id: str = Query(..., description="生成会话ID"),
):
    """
    协作 MVP SSE 端点：GET /api/collab/stream?session_id=...
    （主端点挂 generation 路由；main.py 将同一路由再注册到 /api/collab 前缀下）

    事件协议（锁定版，供前端 components/collab/* 消费）：
      event: snapshot             连接建立时下发一次会话状态快照
      event: generation_progress  流水线各阶段进度（data: {stage, detail, ts}）
      event: collab_status        协作状态变更（data: {status, message}）
      event: ping                 心跳（30s 间隔保活，data: {ts}）
    """
    async def event_stream() -> AsyncGenerator[str, None]:
        q: asyncio.Queue = asyncio.Queue()
        _collab_subscribers.setdefault(session_id, []).append(q)
        try:
            # 1) 回放该会话历史事件（新 join 者不漏进度）
            for entry in _collab_event_log.get(session_id, []):
                yield _sse_format(entry["event"], entry["data"])
            # 2) 下发快照
            yield _sse_format("snapshot", _collab_snapshot(session_id))
            # 3) 持续消费队列，30s 无事件则发 ping 心跳
            while True:
                try:
                    entry = await asyncio.wait_for(q.get(), timeout=30)
                    yield _sse_format(entry["event"], entry["data"])
                except asyncio.TimeoutError:
                    yield _sse_format("ping", {"ts": time.time()})
        finally:
            subs = _collab_subscribers.get(session_id, [])
            if q in subs:
                subs.remove(q)
            if not subs:
                _collab_subscribers.pop(session_id, None)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


class GenerationRequest(BaseModel):
    """生成请求"""
    user_input: str
    mode: str = "quick"  # quick / collaborative / full_control
    extra_config: Optional[Dict[str, Any]] = None
    keep_original: bool = False  # 保持原文模式：禁用LLM改写，仅做排版分页
    user_id: Optional[str] = None  # 用于每日免费额度计数（可选，未登录时用客户端指纹）


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
            result = await self._quick_mode_pipeline(session_id, request.user_input, request.extra_config or {}, request.keep_original)
            return GenerationResponse(
                session_id=session_id,
                status="completed",
                message="极速模式生成完成" + ("（保持原文模式）" if request.keep_original else ""),
                data=result
            )
        elif request.mode == "collaborative":
            result = await self._collaborative_mode_pipeline(session_id, request.user_input, request.extra_config or {}, request.keep_original)
            return result
        elif request.mode == "full_control":
            result = await self._full_control_mode_pipeline(session_id, request.user_input, request.extra_config or {}, request.keep_original)
            return result
        else:
            raise HTTPException(status_code=400, detail=f"不支持的生成模式: {request.mode}")
    
    async def _quick_mode_pipeline(self, session_id: str, user_input: str, config: dict, keep_original: bool = False) -> dict:
        """极速模式流水线"""
        # 保持原文模式：优先解析用户输入为结构化内容
        if keep_original:
            collab_publish(session_id, "generation_progress", {"stage": "keep_original", "detail": "保持原文解析分页"})
            slides = self._fill_keep_original(user_input, session_id)
        else:
            # 1. 意图理解
            collab_publish(session_id, "generation_progress", {"stage": "intent", "detail": "意图理解"})
            intent = await self._intent_analysis(user_input)
            # 2. 大纲生成
            collab_publish(session_id, "generation_progress", {"stage": "outline", "detail": "大纲生成"})
            outline = await self._generate_outline(intent)
            # 3. 内容填充
            collab_publish(session_id, "generation_progress", {"stage": "content", "detail": "内容填充"})
            slides = await self._fill_content(outline, intent)
            # 4. 序号样式推荐（新增）
            collab_publish(session_id, "generation_progress", {"stage": "numbering", "detail": "序号样式推荐"})
            numbering_style = await self._recommend_numbering_style(intent, outline)
            # 5. 样式匹配
            collab_publish(session_id, "generation_progress", {"stage": "style", "detail": "样式匹配"})
            style = await self._match_style(intent)

            # 保存会话
            sessions[session_id] = {
                "intent": intent,
                "outline": outline,
                "slides": slides,
                "numbering_style": numbering_style,
                "style": style,
                "mode": "quick",
                "keep_original": keep_original,
            }
            return {
                "intent": intent,
                "outline": outline,
                "slides": slides,
                "numbering_style": numbering_style,
                "style": style,
                "keep_original": keep_original,
            }

        # 保持原文模式：长文本预研兜底——空输入或分页失败时插入标题页，
        # 确保任何输入都产出 ≥1 页，前端/导出链路不会收到空 slides
        if not slides:
            slides = [{
                "index": 1,
                "title": "保持原文模式",
                "content": ["（暂无内容，请在输入框填写正文后重新生成）"],
                "layout": "title-content",
                "speaker_notes": "",
            }]
            collab_publish(session_id, "generation_progress", {
                "stage": "keep_original_progress",
                "detail": "空输入兜底标题页",
                "pages": 1,
            })
        sessions[session_id] = {
            "slides": slides,
            "mode": "quick",
            "keep_original": keep_original,
        }
        return {"slides": slides, "keep_original": keep_original}

    # ========== 长文本保持原文：分页常量 ==========
    # 单页最大内容行数（超出则继续分页，避免单页溢出/不可读）
    _SLIDES_PER_PAGE = 8
    # 单行最大字符数（长于该值的段落按句子边界拆成多行）
    _MAX_PARA_CHARS = 300
    # 标题行识别阈值：长度低于该值且不以句号/句点结尾，视为小标题
    _TITLE_MAX_LEN = 40

    @staticmethod
    def _split_para_to_lines(text: str) -> list:
        """将长段落按句子边界（。！？!?；;）拆为多行；无边界时才硬切。

        拆分不改变任何文字（原句完整保留），只决定分页呈现粒度。
        短段落原样返回单行。
        """
        s = text.strip()
        if len(s) <= GenerationService._MAX_PARA_CHARS:
            return [s]
        lines, buf = [], ""
        for ch in s:
            buf += ch
            if ch in "。！？!?；;":
                lines.append(buf)
                buf = ""
        if buf:
            lines.append(buf)
        # 无句子边界的超长片段按长度硬切，保证单行不溢出
        out = []
        for ln in lines:
            while len(ln) > GenerationService._MAX_PARA_CHARS:
                out.append(ln[:GenerationService._MAX_PARA_CHARS])
                ln = ln[GenerationService._MAX_PARA_CHARS:]
            out.append(ln)
        return [x for x in out if x]

    @staticmethod
    def _is_title_line(line: str) -> bool:
        """标题行识别：短行且不以句号/句点结尾"""
        l = line.strip()
        return (
            len(l) < GenerationService._TITLE_MAX_LEN
            and not l.endswith('。')
            and not l.endswith('.')
        )

    @classmethod
    def _paginate_keep_original(cls, paragraphs: list) -> list:
        """保持原文分页：

        1. 长段落先按 _split_para_to_lines 拆行
        2. 标题行 + 紧随其后的内容行归入同一页；内容超单页行数时继续分页
        3. 无标题行的纯内容流按每页行数切分，多页时该页首行提升为页标题
        4. 单页无标题时兜底为"要点"；空输入返回 []（调用方插入标题页兜底）

        任何非空输入都会产出带标题的页面，杜绝无标题页。
        """
        if not paragraphs:
            return []
        items = [ln for p in paragraphs for ln in cls._split_para_to_lines(p)]
        n, per_page = len(items), cls._SLIDES_PER_PAGE
        slides = []
        i = 0
        while i < n:
            if cls._is_title_line(items[i]):
                # 标题 + 其内容行合并为一组
                group, j = [items[i]], i + 1
                while j < n and not cls._is_title_line(items[j]):
                    group.append(items[j])
                    j += 1
                title, body = group[0], group[1:]
                # 内容超单页行数时继续分页
                while body:
                    page_body, body = body[:per_page], body[per_page:]
                    slides.append({
                        "index": len(slides) + 1,
                        "title": title,
                        "content": page_body,
                        "layout": "title-content",
                        "speaker_notes": "",
                    })
                i = j
            else:
                # 多页时首行提升为页标题；单页时兜底为"要点"，避免无标题页
                # 首行提升后该页内容行数为 per_page - 1（首行已用于标题）
                will_be_multi_page = (n - i) > per_page
                if will_be_multi_page or len(items[i:i + per_page]) > 1:
                    body_chunk = items[i + 1:i + per_page]
                    slides.append({
                        "index": len(slides) + 1,
                        "title": items[i],
                        "content": body_chunk,
                        "layout": "title-content",
                        "speaker_notes": "",
                    })
                    i += per_page
                else:
                    # 仅 1 行且是标题行（长段落残段）：兜底为"要点"
                    slides.append({
                        "index": len(slides) + 1,
                        "title": "要点",
                        "content": [items[i]],
                        "layout": "title-content",
                        "speaker_notes": "",
                    })
                    i += 1
        return slides

    def _fill_keep_original(self, user_input: str, session_id: str = None) -> list:
        """保持原文模式：将用户输入按段落/标题解析为幻灯片内容，不做改写。

        长文本优化（Phase 3 P1）：
        - 空输入直接返回 []（调用方统一插入"标题页"兜底）
        - 超过单页行数上限时继续分页（_paginate_keep_original）
        - 每生成一页即通过 SSE 广播 `generation_progress` 事件
          （stage="keep_original_progress"，含 pages 计数），供
          components/collab/* 前端实时展示"第 x/y 页"进度
        """
        paragraphs = [p.strip() for p in user_input.split('\n') if p.strip()]
        slides = self._paginate_keep_original(paragraphs)
        if not slides:
            # 空输入兜底：不产生无标题页，由调用方插入标题页
            return []
        total = len(slides)
        for idx, slide in enumerate(slides, 1):
            if session_id is not None:
                collab_publish(session_id, "generation_progress", {
                    "stage": "keep_original_progress",
                    "detail": f"保持原文分页 {idx}/{total}",
                    "pages": idx,
                })
        return slides

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
    
    async def _collaborative_mode_pipeline(self, session_id: str, user_input: str, config: dict, keep_original: bool = False) -> GenerationResponse:
        """协作模式流水线"""
        # 创建会话
        checkpoint_engine.create_session(session_id, "collaborative")

        # 意图理解
        collab_publish(session_id, "generation_progress", {"stage": "intent", "detail": "协作模式·意图理解"})
        intent = await self._intent_analysis(user_input)

        # 大纲生成
        collab_publish(session_id, "generation_progress", {"stage": "outline", "detail": "协作模式·大纲生成"})
        outline = await self._generate_outline(intent)

        # 暂停在第一个检查点
        checkpoint = await checkpoint_engine.pause_at_checkpoint(session_id)

        sessions[session_id] = {
            "intent": intent,
            "outline": outline,
            "mode": "collaborative",
            "keep_original": keep_original,
        }
        collab_publish(session_id, "collab_status", {"status": "checkpoint", "message": "请确认大纲"})

        return GenerationResponse(
            session_id=session_id,
            status="checkpoint",
            message="请确认大纲" + ("（保持原文模式）" if keep_original else ""),
            checkpoints=[{
                "id": checkpoint.id,
                "title": checkpoint.title,
                "description": checkpoint.description,
                "data": {"outline": outline, "keep_original": keep_original}
            }]
        )
    
    async def _full_control_mode_pipeline(self, session_id: str, user_input: str, config: dict, keep_original: bool = False) -> GenerationResponse:
        """全程掌控模式流水线"""
        checkpoint_engine.create_session(session_id, "full_control")

        collab_publish(session_id, "generation_progress", {"stage": "intent", "detail": "全程掌控·意图理解"})
        intent = await self._intent_analysis(user_input)
        collab_publish(session_id, "generation_progress", {"stage": "outline", "detail": "全程掌控·大纲生成"})
        outline = await self._generate_outline(intent)

        checkpoint = await checkpoint_engine.pause_at_checkpoint(session_id)

        sessions[session_id] = {
            "intent": intent,
            "outline": outline,
            "mode": "full_control",
            "keep_original": keep_original,
        }
        collab_publish(session_id, "collab_status", {"status": "checkpoint", "message": "请确认大纲结构"})

        return GenerationResponse(
            session_id=session_id,
            status="checkpoint",
            message="请确认大纲结构" + ("（保持原文模式）" if keep_original else ""),
            checkpoints=[{
                "id": checkpoint.id,
                "title": checkpoint.title,
                "description": checkpoint.description,
                "data": {"outline": outline, "keep_original": keep_original}
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
async def create_generation(request: GenerationRequest, http_request: Request):
    """创建生成任务"""
    # 先验证模式，再执行生成（避免被外层try/except吞掉）
    if request.mode not in ("quick", "collaborative", "full_control"):
        raise HTTPException(status_code=400, detail=f"不支持的生成模式: {request.mode}")
    # 免费额度检查：user_id 未登录时用客户端 IP 兜底
    if request.user_id:
        quota_user_id = request.user_id
    elif http_request.client:
        quota_user_id = f"anon-{http_request.client.host}"
    else:
        quota_user_id = "anon-unknown"
    allowed, used, limit = await check_quota(quota_user_id)
    if not allowed:
        from datetime import datetime, timedelta
        reset_at = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d 00:00:00")
        raise HTTPException(status_code=429, detail={
            "error": "daily_free_quota_exceeded",
            "used": used,
            "limit": limit,
            "reset_at": reset_at,
        })
    try:
        response = await generation_service.start_generation(request)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")
    # 生成成功记入每日免费额度
    record_usage(quota_user_id, ip=http_request.client.host if http_request.client else None)
    # 协作 MVP: POST /create 成功后触发 SSE 广播（状态落定）
    collab_publish(response.session_id, "collab_status", {"status": response.status, "message": response.message})
    return response


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

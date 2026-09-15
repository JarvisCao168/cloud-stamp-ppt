"""
积分/额度状态查询（Phase 4 §3.4）

鉴权规则：绑定调用方自身 user_id（与 /create 的 quota_user_id 同源——
localStorage 指纹 header 链路 X-User-Id or 匿名指纹 anon-{host}），
不接受任意 user_id 查询参数；跨 user_id 查询一律 404（不区分「不存在」
与「无权」，防余额/流水 oracle 枚举）。MVP 过渡期无登录；
登录体系立项后升级为 session-bound 鉴权。
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from ...core.quota import check_quota, check_credits
from ...db import init_db

router = APIRouter()


def _resolve_user_id(http_request: Request) -> str:
    """与 generation.py /create L665-670 同源三级解析：
    请求头 X-User-Id（localStorage 指纹链路）→ anon-{host} → anon-unknown"""
    fingerprint = http_request.headers.get("X-User-Id", "").strip()
    if fingerprint:
        return fingerprint
    if http_request.client:
        return f"anon-{http_request.client.host}"
    return "anon-unknown"


@router.get("/status")
async def quota_status(http_request: Request):
    """
    查询当前会话账户的 usage + credits 状态（§3.4 schema）。
    跨 user_id 一律 404 不枚举（不返回 403，不区分「不存在」与「无权」）。
    """
    # 防御性建表（user_credits/credit_ledger，幂等）：
    # 路由层 init_db() 为同步阻塞点，FastAPI 自动丢进线程池执行，不卡事件循环；
    # 正常路径下 lifespan 已完成建表，此调用为 no-op
    init_db()
    user_id = _resolve_user_id(http_request)

    # 可选查询参数 user_id 仅在与调用方自身指纹一致时放行，否则 404（oracle 防护，R6）
    explicit = http_request.query_params.get("user_id")
    if explicit is not None and explicit != user_id:
        raise HTTPException(status_code=404, detail="not found")

    allowed, used, limit = await check_quota(user_id)
    credit_allowed, balance, credit_used, credit_limit = await check_credits(user_id)

    # §3.4 schema：usage 块 = 免费额度计数（used/limit/reset_at）+ credits 块 = 积分账户
    # required 固定 0（M1 无预扣点，402 拦截路径挂 M2）
    return JSONResponse(content={
        "usage": {
            "used": used,
            "limit": limit,
            "allowed": allowed,
            "reset_at": _next_utc_midnight_iso(),
        },
        "credits": {
            "balance": balance,
            "required": 0,
        },
    })


def _next_utc_midnight_iso() -> str:
    """次日 0 点（UTC 零点口径，与 P1-#7 修复后 generation.py 429 分支 reset_at 同口径）"""
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    return (
        (now + timedelta(days=1))
        .replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
        .strftime("%Y-%m-%dT%H:%M:%SZ")
    )

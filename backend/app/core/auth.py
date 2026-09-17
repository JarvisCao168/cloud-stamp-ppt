"""
M7-A 登录 session 模块
- 密码哈希（pbkdf2_hmac sha256）
- session 生成/验证（内存存储，MVP 阶段；Redis 留后手）
- session 锚定 user_id 解析
"""
import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass
from typing import Optional

# session TTL（秒），MVP 默认 24h
SESSION_TTL = 86400
# 密码哈希迭代次数
PBKDF2_ITERATIONS = 100_000


@dataclass
class SessionInfo:
    user_id: str
    created_at: float
    expires_at: float


# 内存 session 存储（MVP 阶段；多实例部署时切换 Redis）
_sessions: dict[str, SessionInfo] = {}


def _purge_expired_sessions() -> None:
    now = time.time()
    expired = [k for k, v in _sessions.items() if v.expires_at < now]
    for k in expired:
        del _sessions[k]


def hash_password(password: str, salt: Optional[bytes] = None) -> tuple[bytes, bytes]:
    """返回 (salt, digest)"""
    if salt is None:
        salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return salt, digest


def verify_password(password: str, salt: bytes, expected_digest: bytes) -> bool:
    _, digest = hash_password(password, salt)
    return hmac.compare_digest(digest, expected_digest)


def create_session(user_id: str, ttl: int = SESSION_TTL) -> str:
    """生成随机 session token 并存储"""
    _purge_expired_sessions()
    token = secrets.token_urlsafe(32)
    now = time.time()
    _sessions[token] = SessionInfo(user_id=user_id, created_at=now, expires_at=now + ttl)
    return token


def get_session_user_id(token: str) -> Optional[str]:
    """验证 session token，返回 user_id；无效/过期返回 None"""
    _purge_expired_sessions()
    info = _sessions.get(token)
    if info is None:
        return None
    if info.expires_at < time.time():
        del _sessions[token]
        return None
    return info.user_id


def destroy_session(token: str) -> bool:
    """销毁 session，返回是否命中"""
    return _sessions.pop(token, None) is not None


def resolve_user_id_from_session(token: Optional[str]) -> Optional[str]:
    """session token → user_id（无效/缺失返回 None）"""
    if not token:
        return None
    return get_session_user_id(token)

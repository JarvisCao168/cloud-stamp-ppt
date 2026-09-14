# 协作 MVP 验收报告（429 / 幂等断言）

- 日期：2026-09-14
- 执行人：Codex
- 提交基线：`722ebb1`（与 `4953829` 口径一致；`722ebb1` 仅同步 STATUS.md / phase3-tasks.md 的 429 关闭决策，无代码改动）
- 并列文件：`docs/e2e-baseline-report.md`（E2E 基线 55/56 + 429 路径 11 连发）

> 内容参考来源：Hermes 提供的 429/幂等断言参考文本，本节以 `722ebb1` 实际代码/DB 结构为准做了两处勘误（见文末"勘误记录"）。

## 一、429 路径验证节（MVP 口径）

### 触发链路

`POST /api/generation/create`（`backend/app/api/routes/generation.py`）
→ `quota.check_quota(quota_user_id)`（`backend/app/core/quota.py`，`fc69cea` 修复 async 后为 `async with aiosqlite.connect` 语义）
→ 查询 `usage_log` 当日计数（`user_id + generated_at >= 当日零点`）
→ `used >= limit`（`FREE_DAILY_LIMIT` 默认 10）时抛 `HTTPException(429)`
→ 生成成功后 `record_usage(quota_user_id, ip)` 记账（整篇一次，不按段落/幻灯片拆分）

### 429 响应结构（`c466fd2` 锁定语义）

```json
{
  "error": "daily_free_quota_exceeded",
  "message": "今日免费额度已用完（10/10），请明天再试",
  "user_id": "anon-…",
  "used": 10,
  "limit": 10,
  "reset_at": "2026-09-15 00:00:00"
}
```

- `message`：中文提示，`used`/`limit` 为数字
- `reset_at`：次日 0 点（本地时区，`c466fd2` 将 UTC 口径修正为本地日零点语义）

### MVP 边界声明

- proxy 层（`next.config.ts`）**不解析、不透传** 429 响应体（Codex 拍板，`722ebb1` STATUS.md 登记关闭）
- 前端收到 429 后仅做简单拦截提示，不展示 `reset_at` 倒计时
- 完整 429 结构化透传（配额面板 + `Last-Event-ID` 鉴权 + 字段统一 schema）留 Phase 4 设计（`docs/phase4-plan.md`）

### 测试验证（基线 `451e25d` 实测值）

- E2E 基线（`e2e-baseline-report.md`）：同一 user_id 连续 11 次调用 `/create` = **10×200 + 1×429** ✅；测试间用动态 user_id（`e2e-test-时间戳`）隔离配额
- `test_keep_original.py` 16/16 ✅（保持原文/分页引擎 + SSE 进度 + fallback 快速模式，**不含 429 路径**，429 路径验证由 E2E 基线承担）

## 二、幂等断言节

### 计数口径

- `usage_log` 表（`backend/app/db.py`）：`PRIMARY KEY (user_id, generated_at)` + 索引 `idx_usage_log_user_date(user_id, generated_at)`
- 每次 `/create` 成功完成 → `record_usage()` 插入一行（`generated_at` = 当前 UTC 时间戳）
- **整篇算一次**，不按段落/幻灯片拆分

### 幂等语义

- `check_quota()` 按"当日 `generated_at >= 零点` 的行数"判断：同一 user 同日第 11 次请求 → 429 短路，**不进入生成流程**
- 重复请求（相同参数）第 2 次：若第 1 次已记账成功且配额满 → 命中 429；配额未满时重复请求会再次生成并再次记账（无请求级去重/缓存——幂等性由配额计数保证，非由请求去重保证）
- `record_usage` 使用 `INSERT OR REPLACE`，主键为 `(user_id, generated_at)` 精确到微秒，正常并发下不互相覆盖

### DB 结构（`db.py`，实测）

```sql
CREATE TABLE IF NOT EXISTS usage_log (
  user_id TEXT NOT NULL,
  generated_at TIMESTAMP NOT NULL,
  ip TEXT,
  PRIMARY KEY (user_id, generated_at)
);
CREATE INDEX IF NOT EXISTS idx_usage_log_user_date ON usage_log(user_id, generated_at);
```

## 勘误记录（相对 Hermes 参考文本）

1. Hermes 参考稿的 `usage_log` DDL 写成 `id INTEGER PRIMARY KEY + date TEXT`，与 `722ebb1` 实际 `db.py`（`user_id + generated_at` 复合主键，无自增 id、无 date 列）不符，本文件以实际代码为准。
2. Hermes 参考稿称 `test_keep_original.py` 16 项"含 quota 满时 429 路径"，实测该文件 16 项均为分页/保持原文/SSE/fallback 用例，无 429 断言；429 路径验证来源为 E2E 基线（11 连发），已更正上文归属。

## 真实链路验证（占位，待 Codex 补跑）

- Agnes key 已由 JARVIS 提供并落盘 repo 根 `D:\yzppt\.env`（变量名 `agnes_api_key`，命中 `.gitignore:30`，零入库；权威位置非 `backend/.env`）
- 补跑已解禁（Hermes 裁定），@Codex 执行；补跑前需重启 8001（现 PID 11700）加载新 `.env`
- 补跑内容：429 连续 11 连发 + 5000 字长文本端到端 + 真实模型 E2E，以补跑当时 HEAD 实际代码为准（当前 HEAD `196192b`），结果追加进本节，不另起文档

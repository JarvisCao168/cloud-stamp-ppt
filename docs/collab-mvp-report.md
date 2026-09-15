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

## 真实链路验证（Codex 补跑结果，2026-09-15）

- 补跑时间：北京时间 2026-09-15 10:45–10:48（UTC 2026-09-15 02:45–02:48，**不在** UTC 日界 ±1h 窗口内，v0.2.2.1 前置断言 #7 满足）
- HEAD 基线：`ccf9d9f`（origin/master）
- 8001 状态：PID 12788，启动 2026-09-15 00:43:03，晚于 `.env` 写入 00:37:54，key 已拾取
- 环境变量口径勘误（相对占位节旧文）：`.env` 变量名实测为 **`AGNES_API_KEY`（大写）**，与 `config.py` 读取字段一致；非旧文所记小写 `agnes_api_key`

### 1. 429 连发基线（user_id `codex-429-v2`，`quick` 模式）

| 调用 | 结果 | 耗时 |
|---|---|---|
| 1 | 200，完整 `data.slides`（3页） | 9448 ms |
| 2–10 | 200 | 5115–6288 ms（单次最大 13972 ms） |
| 11 | **429** | 2041 ms |
| 12（复验） | **429** | 2058 ms |

- 429 响应体（顶层 `detail` 平铺，符合 v0.2.2 G2 单一平铺形态）：
```json
{"detail":{"error":"daily_free_quota_exceeded","message":"今日免费额度已用完（10/10），请明天再试","user_id":"codex-429-v2","used":10,"limit":10,"reset_at":"2026-09-16 00:00:00"}}
```
- `usage_log` 实测：`codex-429-v2` 当日 10 行，第 11 次起 429 短路（不生成、不记账）✅
- 中间探测（user_id `codex-d-429`）独立复现 10×200 + 1×429 口径，`usage_log` 10 行封顶，两次独立验证一致

### 2. 5000 字长文本真实链路（user_id `codex-5000-char`，5200 字输入）

- 结果：200，`status=completed`，单次 6055–8969 ms（真实 LLM 调用量级，非 mock <1s）
- **Open 项**：响应 `data.slides` 为 `[]`、`numbering_style` 为 `null`——长文本进入大纲/分页管线但 `/create` 同步响应未产出 slides 结构；同 session 走 `POST /api/export/pptx` 可正常导出（`slide_count=3`，200）。疑似分页引擎对超长单段输入在同步响应内的回退路径，非 429/500 故障，建议 M1 前由 @Claude 确认口径
- 导出验证：`POST /api/export/pptx` 200（`slide_count=3`）；`POST /api/export/html` 200（2123 bytes）

### 3. 真实 LLM 路径确认

- 单次 `/create` 耗时 4–14 s 区间，响应含 `intent`/`outline`/`slides`/`numbering_style` 完整结构 → 命中 Agnes 真实 API，非 fallback

### 复跑脚本（`.tmp` 本地，不入库）

- `run1.py`（首次调用 + 结构打印）/ `run2.py`（第 2–11 连发）/ `e2e5000.py`（长文本）/ `exportpptx.py`（导出验证）

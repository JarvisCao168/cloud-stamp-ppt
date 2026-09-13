# Phase 4 设计计划 — 积分制 + 协作编辑流 + SSE 生产端

**日期**: 2026-09-14
**作者**: Claude（首席架构师）
**状态**: 设计稿 v0.1（非阻塞文档，纯设计、零代码改动；不依赖 Agnes key）
**前置基线**: `7ff2dce`（Phase 3 P1 全部交付 + 429 路径验证归属勘误锁定）

> 本计划对应 STATUS.md 待办表中 P4 两行：
> - 「积分制设计文档（免费额度计数器之上）」
> - 「`slide_update` / `generation_complete` 生产端实现 + 429 结构化透传字段格式 + `Last-Event-ID` 断点续传/独立鉴权」
>
> 决策上下文：429 结构化透传 MVP 已拍板不加（Codex 决策，`722ebb1` 登记），字段格式随本阶段配额面板 + 协作编辑流统一定义。

---

## 一、阶段目标

| # | 目标 | 依赖 | 预计工作量 |
|---|------|------|-----------|
| G1 | 积分制（credits）落地：替代每日 10 次硬限流，付费/积分用户走同一配额路径 | 无（DB 迁移可独立做） | 2-3 天 |
| G2 | 429 结构化错误透传 + 前端配额面板（余额展示、充值/升级入口、`reset_at` 倒计时） | G1 | 1-2 天 |
| G3 | SSE 生产端补齐：`slide_update` / `generation_complete` 事件落地 + `Last-Event-ID` 断点续传 | 无 | 2 天 |
| G4 | 协作编辑流（MVP 通知层 → 实时协同编辑，WebSocket 升级 + 冲突处理） | G3（先有事件再谈协同） | 4-5 天 |

**总预算**: 约 2 人周（不含 G4 的 WebSocket 服务端选型与压测）。

**验收标准（阶段出口）**:
1. 新用户注册即赠 N 积分（默认 100），每日免费额度由「积分 ≥ 0」判定，429 响应体统一 schema（见 §三）；
2. 配额面板在前端可见当前余额、当日消耗、`reset_at` 倒计时，充值入口可点击（占位页即可，支付通道另立项）；
3. SSE 断线重连后可凭 `Last-Event-ID` 回放漏收事件，`generation_complete` 触发后前端渲染终态；
4. 协作编辑：两人同时编辑同一 slide，后写者变更可见（乐观锁或 CRDT 二选一，见 §四）；
5. 回归：E2E 基线 55/56 不劣化，Vitest ≥173 全绿。

---

## 二、现状锚点（设计所依据的实际代码，`7ff2dce` 基线实测）

| 项 | 现状 | 出处 |
|---|------|------|
| 配额表 | `usage_log(user_id, generated_at, ip)`，主键 `(user_id, generated_at)`，无自增 `id`、无 `date` 列 | `backend/app/db.py:55-61`（`72cf9cc` 勘误锁定） |
| 限流 | 每日 `FREE_DAILY_LIMIT=10` 硬限；超限抛 429，`detail={error, message, user_id, used, limit, reset_at}`，`reset_at`=本地次日 0 点 | `backend/app/core/quota.py:40-58`、`backend/app/api/routes/generation.py:671-684` |
| 记账 | `record_usage` 用 `INSERT OR REPLACE` + 微秒精度 `generated_at` —— 语义是「同日超限短路 429」，**不是**请求级去重 | `backend/app/core/quota.py:74-85` |
| 429 验证归属 | E2E 基线 11 连发 = 10×200 + 1×429；`test_keep_original.py` 16 项不含 429 断言 | `docs/collab-mvp-report.md`（`72cf9cc` 补建） |
| SSE 协议 | 4 基础事件（`snapshot`/`generation_progress`/`collab_status`/`ping`）+ 2 预留事件（`slide_update`/`generation_complete`，**无生产端**）；`stage` 枚举 7 值 | `app/components/collab/useCollabStream.ts:9-41`、STATUS.md SSE 事件协议表 |
| 广播总线 | `collab_publish()`：每会话最近 100 条事件 + `asyncio.Queue` 扇出 + 30s `ping` + join 回放 | `backend/app/api/routes/generation.py`（`0146a54`） |
| 双路由 | `generation.router` 同时挂在 `/api/generation` 与 `/api/collab` 前缀下 | `backend/app/main.py:50-52` |
| 模型路由 | `ModelRoute.estimated_cost` / `estimated_tokens` 字段已定义但**未被消费**（全库 grep 无调用点） | `backend/app/core/model_router.py:24-31` |
| 用户身份 | 无登录态，`user_id` 缺省 `anon-{IP}`，指纹存前端 localStorage | `generation.py:665-670` |

---

## 三、G1 + G2：积分制与 429 结构化透传

### 3.1 数据模型（DB 迁移，可独立先行）

```sql
-- 用户积分账户（新增表；保留 usage_log 作审计日志）
CREATE TABLE IF NOT EXISTS user_credits (
    user_id        TEXT PRIMARY KEY,
    balance        INTEGER NOT NULL DEFAULT 0,   -- 当前积分余额
    daily_cost     INTEGER NOT NULL DEFAULT 0,   -- 当日已扣积分
    updated_at     TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS credit_ledger (
    seq            INTEGER PRIMARY KEY AUTOINCREMENT,  -- 流水自增
    user_id        TEXT NOT NULL,
    delta          INTEGER NOT NULL,      -- +充值/退款, -扣减
    reason         TEXT NOT NULL,         -- 'gen_quick' | 'gen_heavy' | 'topup' | 'refund' | 'adjust'
    session_id     TEXT,                  -- 关联生成会话（可空）
    created_at     TIMESTAMP NOT NULL
);
CREATE INDEX idx_credit_ledger_user_time ON credit_ledger(user_id, created_at);
```

设计取舍：
- **积分余额与 usage_log 分离**：`usage_log` 保持审计口径不变（已有 E2E 基线与勘误记录锚定它），积分消耗走 `credit_ledger` 流水。
- **扣减点**：`/create` 成功生成后按「整篇一次」扣费（沿用 usage_log 计数规则：不按段落拆分）。扣费在 `record_usage` 同一事务内完成，失败不回滚生成。
- **迁移顺序**：`user_credits` 建表 + 种子（注册赠 100）→ `quota.py` 增加 `check_credits()` → `/create` 路由切换判定源 → 旧 `usage_log` 每日 10 次硬限**降级为告警日志**（不再 429）→ 一个观察期后下线。

### 3.2 计费公式（初版，可调）

| 任务 | 复杂度（`TaskComplexity`） | 扣减积分 |
|------|------|------|
| 润色/分类 | LIGHT | 1 |
| 大纲/意图 | MEDIUM | 3 |
| 多页生成 | HEAVY | 5（长文本 8000+ 字 ×1.5，上限 8） |
| 视觉反思 | MULTIMODAL | 6 |

- 积分单价与 `ModelRoute.estimated_cost` 联动：`estimated_tokens` 超阈值（HEAVY 默认 32K）时按 1.5× 系数。`estimated_cost`/`estimated_tokens` 字段在 `model_router.py` 已有、当前无消费点，本阶段正好接上。
- 余额 < 所需积分 → **预扣失败即 402**（新增 `code=insufficient_credits`，与 429 区分：429 是限流、402 是没钱）。

### 3.3 429 / 402 统一响应 schema（本阶段定稿，取代 MVP 嵌套结构）

MVP 嵌套结构（`detail={error, message, user_id, used, limit, reset_at}`，`generation.py:677-684`）保留兼容，Phase 4 起新增统一 `code` 字段：

```json
{
  "code": "daily_free_quota_exceeded",   // 或 "insufficient_credits"
  "message": "今日免费额度已用完（10/10），请明天再试",
  "user_id": "anon-…",
  "usage": { "used": 10, "limit": 10, "reset_at": "2026-09-15 00:00:00" },
  "credits": { "balance": 3, "required": 5 }   // 仅 402 时出现
}
```

**proxy 层（`next.config.ts`）透传规则（与 Codex 拍板的「MVP 不加」对齐——MVP 不解析，本阶段在 proxy 加最小解析）**:
1. 仅当上游状态码 ∈ {402, 429} 且 body 含 `code` 字段时，原样透传整个 body（不做结构转换）；
2. 其余 4xx/5xx 一律原样透传（现状行为不变）；
3. 前端 `api.ts` 统一拦截：`code=daily_free_quota_exceeded` → 配额面板展示 `usage.reset_at` 倒计时 + 「升级积分」CTA；`code=insufficient_credits` → 展示 `credits.balance/required` + 充值入口。

### 3.4 前端配额面板

- 新组件 `app/components/quota/CreditPanel.tsx`（文件级隔离，不碰 collab/keep-original 文件，沿用协作 MVP 的目录隔离约定）。
- 展示：余额、当日消耗、`reset_at` 倒计时（仅免费额度模式）、积分流水最近 5 条。
- 数据源：新增 `GET /api/quota/status?user_id=...`（返回 §3.3 schema 的 `usage` + `credits` 块，MVP 已有字段 + Phase 4 新字段）。
- 充值入口：占位页 `/pay`（支付通道选型另立项，不在本阶段范围）。

---

## 四、G3 + G4：SSE 生产端补齐与协作编辑流

### 4.1 SSE 协议扩展（在锁定版 4+2 事件上补生产端，不破坏已锁 7 值 stage 枚举）

| 事件 | 触发 | data schema（本阶段定稿） |
|------|------|--------------------------|
| `slide_update` | 任一 slide 内容/样式变更后 | `{session_id, slide_index, op: "add"|"patch"|"remove", payload, rev}` |
| `generation_complete` | 流水线终态（成功/失败/中止） | `{session_id, status: "success"|"error"|"aborted", slides_count, error?}` |

- 生产端落点：`generation.py` 三条流水线（quick/collaborative/full_control）在终态处 `collab_publish(session_id, "generation_complete", ...)`；`full_control` 检查点操作（`checkpoints.py`）每次 slide 变更后发布 `slide_update`。
- **事件序号**：广播总线为每条事件分配单调递增 `event_id`（每会话 1 起），写入 SSE 帧 `id:` 字段 —— 这是 `Last-Event-ID` 断点续传的前提（现状总线只保留最近 100 条且无序号，MVP 靠 join 全量回放）。

### 4.2 `Last-Event-ID` 断点续传

1. 客户端重连时带 `Last-Event-ID: N`（浏览器 `EventSource` 自动带，自定义 SSE 需手动）；
2. 服务端从会话事件环形缓冲（容量 100，现状不变）取 `id > N` 的帧回放，缓冲外则降级为全量 `snapshot` 重发；
3. 鉴权：MVP 依赖 `session_id` 透传（无鉴权，已知风险）；本阶段加 **per-session token**（`snapshot` 事件中下发一次性 token，后续事件帧校验），token 存内存，会话结束即失效；
4. 出口验收：断网 30s → 恢复后事件无重复无丢失（回放去重指纹 `(event_id)` 替代现状 `(stage, pages, detail)`，`useCollabStream.ts:118`）。

### 4.3 协作编辑流（G4）

- **方案 A（推荐）：乐观锁 + 服务端仲裁** —— 客户端携带 `rev`，并发 patch 由服务端按 `slide_update` 事件顺序串行仲裁（广播总线已是有序队列，天然适配），冲突时后写者收 `collab_status` 的 `conflict` 状态并 rebase。实现成本最低，不改协议层。
- **方案 B：CRDT（Yjs/Automerge）** —— 客户端合并无冲突，但引入重依赖 + 服务端需持久化 CRDT 文档，工作量翻倍。
- 决策点（阶段内拍板）：编辑粒度 = slide 级（非字符级）。若后续要字符级协同编辑，直接升 B 案。
- 通道：WebSocket 升级（SSE 保留为通知层，决策已锁定于 `docs/phase3-tasks.md` §4 技术选型节）。服务端 WebSocket 与 SSE 共进程（FastAPI `WebSocket` 端点），房间模型 = session_id。
- 并发目标：单会话 ≤10 在线编辑者，p95 广播延迟 < 500ms。

### 4.4 与现有组件的接口

- `useCollabStream.ts`：新增 2 个事件 type（`slide_update`/`generation_complete`），`processedProgressRef` 去重指纹升级为 `event_id`；`Last-Event-ID` 由 `es.onopen` 时从本地存储读取重连前最后 id。
- `CollabStatusPanel.tsx`：`generation_complete` 终态渲染（status=success 转绿 / error 转 rose 错误态，复用现有断线错误态样式）；`slide_update` 驱动进度条按 slide 粒度推进（`currentSlide` 字段已预留于 `useCollabStream.ts:34`，本阶段启用）。
- 测试：`__tests__/collabStream.test.ts` 扩 4 项（event_id 去重、Last-Event-ID 回放、generation_complete 终态、slide_update 驱动进度）；E2E 基线 55/56 补 1 项断线回放（1 flaky 项维持现状，另计 retry 加固任务）。

---

## 五、实施顺序与里程碑

| 里程碑 | 内容 | 前置 | 产出 |
|--------|------|------|------|
| M1 | DB 迁移（`user_credits` + `credit_ledger`）+ `check_credits()` + `/create` 切换 + `GET /api/quota/status` | 无 | 积分制可用，旧 10 次硬限降级为告警 |
| M2 | 429/402 统一 schema + proxy 最小解析 + `CreditPanel` | M1 | 配额面板上线，`reset_at` 倒计时可见 |
| M3 | 事件序号 + `slide_update`/`generation_complete` 生产端 + `Last-Event-ID` + per-session token | 无（与 M1 并行） | SSE 断点续传可用 |
| M4 | WebSocket 协作编辑（A 案乐观锁）+ 冲突 rebase + 4 项专属测试 + E2E 补断线回放 | M3 | 协作编辑流 MVP，两编辑器场景验证 |

**风险与对策**:
- **R1 积分切换影响 E2E 基线**：M1 切换后基线 429 连发用例需改判定源（积分不足 402）——切换与基线更新同一 PR 内完成，CI 红不允许合入。
- **R2 双路由前缀（`/api/generation` + `/api/collab`）**：事件序号若在两条前缀分别起算会乱序——序号总线挂在 `session_id` 维度而非路由维度，路由前缀只影响 URL，不影响 `event_id`。
- **R3 `anon-{IP}` 指纹不稳**（NAT/代理环境 IP 漂移 → 积分账户串号）：本阶段不做登录，接受该限制并在配额面板文案标注「匿名账户积分不跨设备」；登录体系另立项。
- **R4 长文本 8000+ 字 ×1.5 系数**：系数拍脑袋值，上线前用 5000/8000/15000 三档实测 token 消耗回归校准（数据在材料库 Phase 2 预研，见 MEMORY 材料库条目）。

**明确不做（本阶段边界外）**:
- 支付通道选型/接入（仅占位 `/pay`）
- 登录/注册体系（沿用 `anon-{IP}` 指纹 + localStorage）
- 字符级协同编辑（slide 级够用，CRDT 留后手）
- 多区域部署下的配额一致性（当前单实例 SQLite，`config.py` 已绝对路径锚定 `backend/yunzhang.db`；多实例时配额表需迁移，另立项）

---

## 六、文档变更记录

| 版本 | 日期 | 变更 |
|------|------|------|
| v0.1 | 2026-09-14 | 初稿（Claude）：基于 `7ff2dce` 基线实测现状锚点撰写；429 响应体口径与 `72cf9cc` 勘误记录对齐 |

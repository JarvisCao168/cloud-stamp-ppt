# Phase 4 设计计划 — 积分制 + 协作编辑流 + SSE 生产端

**日期**: 2026-09-14
**作者**: Claude（首席架构师）
**状态**: 设计稿 v0.2.4（M3 启动令 A+B 裁定（@JARVIS 2026-09-16）：新增 §4·B M3 B 案 SSE 增量事件（presence）协议草案登记——独立 `event` 命名空间（`viewer_joined`/`viewer_left`/`presence_snapshot`）+ payload「只增不删不改义」+ 分发点清单 D1-D5/S1-S2 + 预扣点章节引用组长终审裁定 #4 原文「整篇计一次」+ 429/402 路径分离标注 + 基座 `098cde9` 不动声明 + 三条收口硬约束落档（含 `config.py` 完整路径勘误）+ 实码勘误行（当日计数口径三处行号以 HEAD `bcd202c` 实测 `:205/:248/:273` 为准）；§4.1-4.4 既有锁定内容零改动；M3 零生产代码变更，B 落码在 M4。v0.2.3 §3.5 M2 预扣点接入设计 + v0.2.2.4 行号实测锁定基线不变。JARVIS 终审基准 = 本稿落档 commit）
**前置基线**: `83fda71`（Phase 3 P1 全部交付 + `docs/phase4-plan.md` v0.1 首次落盘）

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
1. 每日免费额度改由积分路径判定（余额 ≥ 0 或免费额度未耗尽），`quota/status` 与 402/429 响应体统一 schema（见 §三）；
   - **v0.2 修订**：删除 v0.1 中「注册即赠 N 积分（默认 100）」——§五 明确不做登录/注册，无「注册事件」可挂赠额（F#5）；赠额统一挪到登录体系立项后随 M4 之后的版本再开（见 §五 R5）。
2. 配额面板在前端可见当前余额、当日消耗、`reset_at` 倒计时，充值入口可点击（占位页即可，支付通道另立项）；面板数据源 `GET /api/quota/status` 须走 §3.4 的鉴权规则（MVP 免鉴权仅限匿名账户自查询，禁止跨 user_id 枚举，见 §五 R6）；
3. SSE 断线重连后可凭 `Last-Event-ID` 在**进度帧可回放边界内**回放漏收事件（进度帧不可回放的降级行为见 §4.2 修订 3），`generation_complete` 触发后前端渲染终态；
4. 协作编辑：两人同时编辑同一 slide，后写者变更可见（乐观锁或 CRDT 二选一，见 §四）；`slide_update` 生产端在 G4 落地（见 §4.1 修订）；
5. 回归：E2E 基线 55/56 不劣化，Vitest ≥173 全绿；**M1 切换后基线 429 连发用例改判 402 的判定源更新与本阶段 §五 R1 同 PR 完成，不得分叉**；**时区口径统一（§二 现状锚点勘误行）与 E2E 基线跨 UTC 边界的回归在同一窗口内验证一次**。
   - **v0.2.2 补充 ①（#3 改判窗口前置，Codex 补充意见，起稿同步落实）**：v0.2 终审定稿后，E2E 基线脚本/报告的 429 断言改判窗口与 M1 实施**同批**完成——即 M1 PR（判定源切换 + `reset_at` UTC ISO 化 + 基线改判 429→402）须在同一 PR 内合并，不得拆成「先改判定源、后补基线」两批；终审 commit 进 origin/master 时基线脚本附件（`docs/e2e-baseline-report.md` 对应 11 连发操作记录）须同步更新改判说明，避免终审后二次改判抖动。
   - **v0.2.2 补充 ②（#7 UTC 边界前置断言，Codex 补充意见，起稿同步落实）**：P1-#7 修复（`generation.py:674-675` 改 UTC 口径）合入后，**E2E 429 连发回归须在 UTC 日界前后 1h 窗口内不执行**；若回归落在该窗口，须改判 `reset_at` 期望值或直接重跑基线并同步更新报告。该断言作为 M1 开工前的前置验证项，与 §3.3 M1 开工前前置动作同批执行。

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
| 时区口径（现状 bug） | `quota.py:15-18` `_today_start_utc()` 按 UTC 零点截断日窗；`generation.py:674-675` `reset_at` 却按本地时区（`datetime.now()`，无时区）次日 0 点计算 —— UTC+8 下偏差 8h，`generation.py:674` 注释「与 quota 重置口径一致」是错的；本阶段 §3.2 修复，统一 UTC | `quota.py:15-18`、`generation.py:674-675` |

---

## 三、G1 + G2：积分制与 429 结构化透传

### 3.1 数据模型（DB 迁移，可独立先行）

```sql
-- 用户积分账户（新增表；保留 usage_log 作审计日志）
CREATE TABLE IF NOT EXISTS user_credits (
    user_id        TEXT PRIMARY KEY,
    balance        INTEGER NOT NULL DEFAULT 0,   -- 当前积分余额
    daily_cost     INTEGER NOT NULL DEFAULT 0,   -- 当日已扣积分
    last_cost_date DATE     NOT NULL DEFAULT '1970-01-01',  -- 当日消耗清零锚点（§3.4 面板「当日消耗」语义）
    version        INTEGER NOT NULL DEFAULT 0,   -- 乐观锁列：M2 扣减 SQL 用 WHERE version=? 原子更新（防并发双扣）
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
- **并发扣减（v0.2 修订，对应 findings #12）**：M2 接入 `/create` 扣减时，同一 `user_id` 并发两个 `/create` 存在竞态读 balance → 双扣或负余额风险。M1 DDL 已带 `version` 乐观锁列，M2 扣减 SQL 定为 `UPDATE user_credits SET balance=?, daily_cost=?, version=version+1 WHERE user_id=? AND version=?`，影响行数 = 0（版本已被并发请求推进）时**重试**（上限 3 次，仍冲突则 503），不做悲观锁（SQLite 写锁粒度太粗）。
- **迁移顺序（v0.2 修订，对齐 §一 验收标准#1 / §五 R5）**：`user_credits` 建表（**不赠额**，`balance` 初值 = 0；`daily_cost` 列增补 `last_cost_date DATE NOT NULL` 日期锚点，供「当日消耗」清零语义，见 §3.4）→ `quota.py` 增加 `check_credits()`（免费额度 = 「余额 ≥ 0 或当日免费额度未耗尽」的复合判定，耗尽走 429 旧 schema，余额不足走 402 新 schema，见 §3.3 修订）→ `/create` 路由切换判定源 → 旧 `usage_log` 每日 10 次硬限**降级为告警日志**（不再 429）→ 一个观察期后下线。赠额统一挂到登录体系立项后（§五 明确不做登录/注册），不在 M1 内做「注册赠 100」。

### 3.2 计费公式（初版，可调）

| 任务 | 复杂度（`TaskComplexity`） | 扣减积分 |
|------|------|------|
| 润色/分类 | LIGHT | 1 |
| 大纲/意图 | MEDIUM | 3 |
| 多页生成 | HEAVY | 5（长文本 8000+ 字 ×1.5，上限 8） |
| 视觉反思 | MULTIMODAL | 6 |

- 积分单价与 `ModelRoute.estimated_cost` 联动：`estimated_tokens` 超阈值（HEAVY 默认 32K）时按 1.5× 系数。`estimated_cost`/`estimated_tokens` 字段在 `model_router.py` 已有、当前无消费点，本阶段正好接上。
- 余额 < 所需积分 → **预扣失败即 402**（新增 `code=insufficient_credits`，与 429 区分：429 是限流、402 是没钱）。

### 3.3 429 / 402 统一响应 schema（本阶段定稿，单一形态：平铺顶层 `code`）

**v0.2 修订稿终稿确认（对应 findings #3/#4 裁定）**：v0.1 措辞「取代 MVP 嵌套结构」与正文「保留兼容」自相矛盾——同一响应体不可能既「取代」又「保留」；且 `raise HTTPException(status_code=429, detail={...})` 只能产出 `{"detail": {...}}`（嵌套结构），**平铺顶层 `code` 需要不同的响应机制**。v0.2 按组长裁定定稿如下——**§3.3 的 schema 定稿只保留一种（平铺顶层 `code`），嵌套 `detail` 形态仅存在于 M1 切换前 `generation.py:677-684` 现状代码中，不进本节 schema 定稿**；本节定稿的平铺 schema 即 G1 切换后 M1/M2 落地的唯一目标形态，过渡兼容段（嵌套结构并存）删除，避免实施侧二义：

- **响应机制**：统一 schema 的响应不走 `HTTPException(detail=...)`，改用 `JSONResponse(status_code=429/402, content={...})` 直接返回平铺顶层 `code`；或挂全局异常处理器统一转换。**M1 切换动作即把 `generation.py:677-684` 的 `HTTPException` 429 分支替换为 `JSONResponse` 平铺形态**，切换完成后旧嵌套 `detail` 形态下线，不再有「同一端点两种形态并存」的过渡兼容段；proxy 透传规则相应简化——M1 切换后 402/429 响应体一律平铺顶层 `code`，proxy 只在「状态码 ∈ {402,429} 且 body 顶层含 `code` 字段」时原样透传，不再解析 `body.detail`。
- **稳态 429 触发路径**：§3.1 说旧 10 次硬限降级为「告警日志（不再 429）」，v0.2 补一条**唯一保留的 429 路径**——积分制切换后，「当日免费额度（`FREE_DAILY_LIMIT` 折算的积分额度）耗尽且余额 = 0」仍发 429（`code=daily_free_quota_exceeded`），与 402（`code=insufficient_credits`，余额 < 所需且当日免费额度已耗尽）区分：429 = 免费额度耗尽（等次日重置或充值解锁），402 = 余额不足（充值解锁）。稳态下 429 有且仅有这一条触发路径，v0.1 的「429 统一 schema」验收措辞保留但限定在此路径内。
- **schema 定稿（唯一形态，平铺顶层 `code`）**：

```json
{
  "code": "insufficient_credits",   // 或 "daily_free_quota_exceeded"
  "message": "积分不足（余额 3 / 需 5），请充值或明日免费额度重置后再试",
  "user_id": "anon-…",
  "usage": { "used": 10, "limit": 10, "reset_at": "2026-09-15T00:00:00Z" },   // 仅 429 出现
  "credits": { "balance": 3, "required": 5 }   // 仅 402 出现
}
```

> **M1 切换前现状锚定**：`generation.py:677-684` 现走 `HTTPException` 嵌套 `detail` 结构（`error=daily_free_quota_exceeded`），该形态仅存在于 M1 切换前的过渡窗口内，作为代码现状描述供实施侧参考，**不进本节 schema 定稿**。

- **proxy 层（`next.config.ts`）透传规则**（与 Codex 拍板的「MVP 不加」对齐——MVP 不解析，本阶段在 proxy 加最小解析）：
  1. 仅当上游状态码 ∈ {402, 429} 且 body 顶层或 `body.detail` 含 `code`/`error` 字段时，原样透传整个 body（不做结构转换；M1 切换前过渡窗口内嵌套结构与平铺结构都会出现，切换完成后统一为平铺）；
  2. 其余 4xx/5xx 一律原样透传（现状行为不变）；
  3. 前端 `api.ts` 统一拦截：`code`/`detail.error` ∈ {`daily_free_quota_exceeded`} → 配额面板展示 `usage.reset_at` 倒计时 + 「升级积分」CTA；`code=insufficient_credits` → 展示 `credits.balance/required` + 充值入口。

**M1 开工前前置动作（v0.2 新增，对应 findings #3/#4 对 E2E 基线的影响；Codex 已独立核认，Hermes 终审 NIT① 确认）**：切换判定源（旧 429 → 新 402 或新 429 唯一路径）前，E2E 基线 11 连发（10×200 + 1×429）的断言粒度已三方核认（Hermes/Codex/Claude 一致）——`e2e-baseline-report.md`「429 免费额度路径验证」节 + `collab-mvp-report.md`「429 路径验证节」均只断言「状态码 = 429 + `message`/`error` 字段存在」，**未断言嵌套 `detail` 结构本身**；且 `e2e/` 目录 grep `429` 零命中（11 连发验证是报告层操作记录，非 e2e 用例断言）→ M1 切换后稳态 429 唯一路径保留，基线不需改断言；M1 PR 仅需同步改 `reset_at` 值（UTC ISO 格式，随 P1-#7 一起推），不需同步改嵌套 `detail` 结构断言（与 §五 R1 同 PR 完成，不得分叉）。

### 3.4 前端配额面板

- 新组件 `app/components/quota/CreditPanel.tsx`（文件级隔离，不碰 collab/keep-original 文件，沿用协作 MVP 的目录隔离约定）。
- 展示：余额、当日消耗（`last_cost_date` 锚点做「当日」清零判定）、`reset_at` 倒计时（仅免费额度模式）、积分流水最近 5 条。
- 数据源：新增 `GET /api/quota/status`（返回 §3.3 schema 的 `usage` + `credits` 块，MVP 已有字段 + Phase 4 新字段）。
  - **鉴权规则（v0.2 新增，对应 findings #2 / R6）**：`quota/status` 必须绑定调用方自身的 `user_id`（来自同一 localStorage 指纹链路，与 `/create` 的 `quota_user_id` 同一来源），**不接受任意 `user_id` 查询参数**——v0.1 的 `?user_id=...` 写法在匿名指纹链路下是余额/流水 oracle，可枚举任意 user_id。MVP 过渡期（无登录）该端点只做「查询当前会话指纹对应的账户」，跨 user_id 查询一律 404（不区分「不存在」与「无权」，避免枚举探测）。登录体系立项后升级为 session-bound 鉴权。
- 充值入口：占位页 `/pay`（支付通道选型另立项，不在本阶段范围）。

---

### 3.5 M2 预扣点接入设计（v0.2.3 新增，Claude 起草）

> 本节为 M2 实施唯一设计基准。M1 已落档 `check_credits()` 4 元组签名 + §3.3 平铺 schema + 拦截式判定式注释，本节补齐 M2 起 `required > 0` 后完整的预扣点接入路径。

#### 3.5.1 `estimate_required()` 折算函数（计费点路由映射）

**职责**：根据当前请求的生成模式 + 输入规模，计算本次 `/create` 应预扣的积分数 `required`。

**路由映射表**（沿用 §3.2 计费公式，按 `/create` 请求入口统一折算，不逐段拆分）：

| 触发场景 | `TaskComplexity` | 基础扣减 | 附加系数 | `required` 取值 |
|---|---|---|---|---|
| `mode=quick` + 润色/分类（输入 ≤500 字） | LIGHT | 1 | — | 1 |
| `mode=quick` + 大纲/意图（500 < 输入 ≤4000 字） | MEDIUM | 3 | — | 3 |
| `mode=quick` + 多页生成（4000 < 输入 ≤8000 字） | HEAVY | 5 | — | 5 |
| `mode=quick` + 多页生成（输入 >8000 字） | HEAVY | 5 | ×1.5 | 8（封顶，§3.2 / R4） |
| `mode=quick` + 视觉反思/多模态（`complexity=MULTIMODAL`） | MULTIMODAL | 6 | — | 6 |
| `mode=collaborative` / `full_control`（checkpoint 暂停态，`/create` 不产 slides） | —（不计费点） | 0 | — | 0（M4 协作流 checkpoint 动作计费单独立项） |

- `required` 为整数，单位 = 积分（§3.2 各任务档位）；
- 输入字数阈值（500 / 4000 / 8000）按 `request.user_input` 长度直接判定，无需调用 `model_router.route()`——`model_router` 只负责模型通道选择，**不承担计费折算职责**（§二 现状锚点：`estimated_cost` / `estimated_tokens` 字段已有、当前无消费点，本函数独立实现，不依赖 `model_router` 实例）；
- `estimated_tokens` 超 32K 的 ×1.5 系数（§3.2）仅在 `required=5` 档生效（HEAVY >8000 字），上限封 8，与 R4 一致（上线前三档实测校准）；
- 本函数为纯函数，入参 `(mode: str, input_len: int, complexity: str = "auto")` → 出参 `int`，`complexity` 缺省 `"auto"` 时按字数阈值路由，视觉反思场景由调用方显式传 `"multimodal"`；
- 单测 9 组覆盖见 §3.5.5 PR 1 验收。

#### 3.5.2 `debit_credits()` / `refund_credits()` 实现（version 乐观锁，§3.1 并发扣减定稿）

**位置**：`backend/app/core/quota.py`，与 `check_credits()` 同模块，供 `generation.py` `/create` 路由在判定放行后调用。

**辅助函数**：

```python
def _now_utc_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
```

**`debit_credits(user_id, required, session_id, reason)`**：

```python
async def debit_credits(user_id: str, required: int, session_id: Optional[str] = None, reason: str = "gen") -> Tuple[bool, int]:
    """
    预扣积分（乐观锁，§3.1 并发扣减定稿）
    返回 (成功, 新余额)；余额不足返回 (False, 当前余额)；账户行不存在返回 (False, -1)；
    版本冲突重试 ≤3 次，仍冲突返回 (False, -2)
    """
    import aiosqlite
    db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
    for attempt in range(3):
        conn = await aiosqlite.connect(db_path)
        try:
            cursor = await conn.execute(
                "SELECT version, balance FROM user_credits WHERE user_id = ?", (user_id,)
            )
            row = await cursor.fetchone()
            if row is None:
                # 账户行不存在（M1 不赠额，R5）→ 视为余额 0，直接 402 语义兜底
                return (False, -1)
            old_version, balance = row[0], row[1]
            if balance < required:
                return (False, balance)   # 余额不足，调用方走 402
            # 原子更新（乐观锁，§3.1 定稿 SQL 形态）
            cursor = await conn.execute(
                "UPDATE user_credits SET balance = ?, daily_cost = daily_cost + ?, version = version + 1, "
                "updated_at = ? WHERE user_id = ? AND version = ?",
                (balance - required, required, _now_utc_iso(), user_id, old_version),
            )
            await conn.commit()
            if cursor.rowcount == 0:
                continue   # 版本已被并发请求推进 → 重试
            new_balance = balance - required
            await conn.execute(
                "INSERT INTO credit_ledger (user_id, delta, reason, session_id, created_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, -required, reason, session_id, _now_utc_iso()),
            )
            await conn.commit()
            return (True, new_balance)
        except Exception:
            pass
        finally:
            await conn.close()
    return (False, -2)   # 3 次版本冲突均失败
```

**`refund_credits(user_id, required, session_id, reason)`**：

```python
async def refund_credits(user_id: str, required: int, session_id: Optional[str] = None, reason: str = "refund") -> bool:
    """
    生成失败 / 中止时退款（乐观锁同上；流水 delta = +required；daily_cost 用 CASE WHEN 防负数——SQLite 无 GREATEST，§3.5.2 勘误行）
    返回成功（余额加回）；账户行不存在或 3 次版本冲突均失败 → 返回 False（不抛异常，由调用方记日志）
    """
    import aiosqlite
    db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
    for attempt in range(3):
        conn = await aiosqlite.connect(db_path)
        try:
            cursor = await conn.execute(
                "SELECT version FROM user_credits WHERE user_id = ?", (user_id,)
            )
            row = await cursor.fetchone()
            if row is None:
                return False
            old_version = row[0]
            cursor = await conn.execute(
                "UPDATE user_credits SET balance = balance + ?, "
                "daily_cost = CASE WHEN daily_cost - ? > 0 THEN daily_cost - ? ELSE 0 END, "
                "version = version + 1, updated_at = ? WHERE user_id = ? AND version = ?",
                (required, required, _now_utc_iso(), user_id, old_version),
            )
            await conn.commit()
            if cursor.rowcount == 0:
                continue
            await conn.execute(
                "INSERT INTO credit_ledger (user_id, delta, reason, session_id, created_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, +required, reason, session_id, _now_utc_iso()),
            )
            await conn.commit()
            return True
        except Exception:
            pass
        finally:
            await conn.close()
    return False
```

**关键设计决策**：
- `session_id` 在预扣时点尚未生成（`start_generation` 调用前），预扣流水允许 `session_id=NULL`；生成完成后由调用方（`generation.py`）在同一事务内补写流水（`update_credit_ledger_session_id(session_id, user_id, since_ts)`，M2 PR 1 一并实现）；
- 流水 `reason` 枚举：`gen_quick` / `gen_heavy` / `refund` / `topup`（充值挂登录体系后）/ `adjust`（运营手动，仅 M4 后）；
- `debit_credits` 返回 `(False, -1)` = 账户行不存在（402 兜底，`required>0` 时余额视为 0）；`(False, -2)` = 3 次版本冲突均失败（503，§3.5.4）；
- `refund_credits` 失败不抛异常（退款是后台操作，失败记日志由 M4 运营看板告警，不影响生成响应）。
- **工程核认提醒 ①（Codex M2 核认，PR 1 吸收）**：`debit_credits` / `refund_credits` 3 次版本冲突重试退避固定 50ms 起步（`asyncio.sleep(0.05)`），非忙等裸重试。
- **工程核认提醒 ②（Codex M2 核认，PR 1 吸收）**：`refund_credits` 按流水号（`session_id`）幂等去重——同一流水号重复调用先查 `credit_ledger` 既有 `delta=+required` 退款流水，命中直接返回成功，防 500 重试路径双重返还；`session_id=None` 时不去重（保持与 debit 同语义）。
- **SQLite 勘误**（随 M2 PR 1 同批落档）：§3.5.2 `refund_credits` 原稿 SQL 用 `GREATEST(0, daily_cost - ?)` 防负数——SQLite 无内建 `GREATEST` 标量函数（实测 `sqlite3.OperationalError: no such function: GREATEST`），M2 PR 1 落码改用 `CASE WHEN daily_cost - ? > 0 THEN daily_cost - ? ELSE 0 END` 等价写法，语义与 R5 口径不变。

#### 3.5.3 `/create` 402 分支激活 + 拦截式判定式定稿

**M2 起 `generation.py` 判定域（L671-700）改造（随 M2 PR 1 同批，替换 M1 注释 `required = 0` 预留行）**：

```python
# 判定 + 拦截（M2 起 required > 0，激活 402 / 503 分支）
allowed, used, limit = await check_quota(quota_user_id)
required = estimate_required(request.mode, len(request.user_input or ""), complexity)
credit_allowed, balance, credit_used, credit_limit = await check_credits(quota_user_id, required)

if not allowed and balance == 0:
    # 稳态 429 唯一路径（§3.3）：免费额度耗尽 且 余额 = 0（M1 起不变）
    ...  # 现有 JSONResponse(429) 不动
    return JSONResponse(status_code=429, content={...})

if not credit_allowed and balance < required:
    # 402：免费额度耗尽 且 余额 < 所需积分（M2 起 required > 0 时此分支可达）
    return JSONResponse(status_code=402, content={
        "code": "insufficient_credits",
        "message": f"积分不足（余额 {balance} / 需 {required}），请充值或明日免费额度重置后再试",
        "user_id": quota_user_id,
        "credits": {"balance": balance, "required": required},
    })

# 放行 → 预扣（M2 起 required > 0 时执行；M1 required=0 时跳过扣减）
if required > 0:
    debit_ok, new_balance = await debit_credits(quota_user_id, required, reason=f"gen_{complexity}")
    if debit_ok:
        pass  # 扣减成功，继续生成
    elif new_balance >= 0:
        # 余额不足（乐观锁竞态窗口内并发读到的 balance < required）→ 402 兜底
        return JSONResponse(status_code=402, content={...})  # 同上
    else:
        # new_balance = -1（账户行不存在）→ 402（balance 视为 0）；-2（版本冲突 3 次）→ 503
        if new_balance == -2:
            return JSONResponse(status_code=503, content={
                "code": "service_unavailable",
                "message": "积分扣减服务暂时不可用，请稍后重试",
                "user_id": quota_user_id,
            })
        return JSONResponse(status_code=402, content={
            "code": "insufficient_credits",
            "message": f"积分不足（余额 0 / 需 {required}），请充值或明日免费额度重置后再试",
            "user_id": quota_user_id,
            "credits": {"balance": 0, "required": required},
        })
```

**判定式定稿（§2.3 NIT 收敛后正式表述，M2 PR 1 落地时同步写回 `check_credits` docstring + `generation.py` 注释）**：

> 免费额度优先：`free_allowed = used < limit`；`credit_allowed = balance >= required`。
> - `free_allowed = True` → 直接放行，**不扣积分**（免费额度未耗尽时不额外消耗余额）；
> - `free_allowed = False and balance >= required` → 放行 + 预扣 `required`；
> - `free_allowed = False and 0 < balance < required` → 拦截 402（余额不足）；
> - `free_allowed = False and balance = 0` → 拦截 429（免费额度耗尽且无积分）；
> - `debit_credits` 返回 `(False, -2)` → 拦截 503（版本冲突 3 次，服务不可用，非用户侧错误）。

此定稿取代 M1 落码注释中"OR 判定式"残留措辞（`quota.py` docstring + `generation.py` L673 注释），M2 PR 1 落地后同步更新，**不单独开文档 commit**（随 PR 1 同批）。

#### 3.5.4 402 / 503 / 429 / 200 四态触发条件汇总（M2 起生效）

| 状态码 | 触发条件 | `code` | 解锁路径 |
|---|---|---|---|
| 429 | `used ≥ limit`（免费额度耗尽）且 `balance = 0` | `daily_free_quota_exceeded` | 次日 UTC 零点重置 / 充值 |
| 402 | `used ≥ limit` 且 `0 ≤ balance < required`（含 `balance = 0` 账户行不存在的兜底） | `insufficient_credits` | 充值至 `balance ≥ required` |
| 503 | `debit_credits` 乐观锁 3 次版本冲突均失败 | `service_unavailable` | 稍后重试（非用户侧操作） |
| 200 | `used < limit`（免费额度未耗尽，不扣积分）或 `balance ≥ required`（预扣成功） | —（正常响应） | — |

> **M1 现状锚定**（E2E 基线对照，M2 合入后作废）：M1 下 `required = 0`，402 / 503 分支不可达，稳态 429 为唯一拦截路径（§3.3 已定稿）。M2 合入后 E2E 基线改判 402 用例须与 M2 PR 1 同 PR 完成（§五 R1 口径延续，不得分叉）。

#### 3.5.5 M2 两 PR 拆分产出清单（排期基准，待 @Codex 工程核认后启动）

**PR 1（折算函数 + 扣减实现 + 单测 9 组 + E2E 改判）**：
- `backend/app/core/quota.py`：新增 `estimate_required()` / `debit_credits()` / `refund_credits()` / `update_credit_ledger_session_id()` / `_now_utc_iso()`；`check_credits` docstring 更新为 §3.5.3 定稿判定式；
- `backend/app/api/routes/generation.py`：`/create` 判定域（L671-700）按 §3.5.3 改造，L694 `required = 0` 替换为 `estimate_required()` 调用，激活 402 / 503 分支；生成失败 / 中止路径挂 `refund_credits()`（`generation.py` `except` 块，M2 PR 1 一并实现）；
- **单测 9 组**（新文件 `backend/tests/test_quota_m2.py`，随 PR 1 同批）：
  1. `estimate_required("quick", 100, "auto")` → 1（LIGHT，≤500 字）
  2. `estimate_required("quick", 3000, "auto")` → 3（MEDIUM，500-4000 字）
  3. `estimate_required("quick", 5000, "auto")` → 5（HEAVY 基础，4000-8000 字）
  4. `estimate_required("quick", 8500, "auto")` → 8（HEAVY >8000 字 ×1.5 封顶）
  5. `estimate_required("quick", 100, "multimodal")` → 6（视觉反思）
  6. `estimate_required("collaborative", 5000, "auto")` → 0（checkpoint 暂停态不计费）
  7. `debit_credits` 余额充足 → `(True, 新余额)`，`credit_ledger` 写入 `delta=-required`，`version` +1
  8. `debit_credits` 余额不足 → `(False, 当前余额)`，不写流水，`version` 不变
  9. `refund_credits` 正常退款 → 余额加回，`daily_cost` 不出现负数（`CASE WHEN … > 0 THEN … ELSE 0 END` 断言，§3.5.2 SQLite 勘误行）
- E2E 基线改判 402 用例（1 条，随 PR 1 同批更新，§五 R1 / §3.5.4 M1 锚定作废注记）；
- `next.config.ts` proxy 透传白名单新增 503（§3.3 proxy 节 1 对齐，402 已有）。

**PR 2（CreditPanel 前端 + E2E 402 断言）**：
- `app/components/quota/CreditPanel.tsx`：余额 / 当日消耗（`last_cost_date` 清零锚点）/ `reset_at` 倒计时（仅免费额度模式显示）/ 积分流水最近 5 条（§3.4 数据源 `GET /api/quota/status`，M1 已落档）；
- 前端 `api.ts` 拦截器补 402 / 503 分支（§3.3 proxy 节 3，503 新增）；
- E2E 402 断言（1 条）：余额 < `required` 时 `/create` 返回 402，`credits.balance` / `credits.required` 字段存在且值正确；
- Vitest 新增 1 项（CreditPanel 402 态 CTA 渲染），总用例数 +1（173 → 174）。

**排期（待 @Codex 核认后确认）**：
- PR 1：2-3 天（`estimate_required` 0.5 天 + 扣减/退款实现 1 天 + 单测 9 组 1 天 + E2E 改判 0.5 天）；
- PR 2：1-2 天（CreditPanel 1 天 + 402 断言 0.5 天）；
- 合计 3-5 天，与 §五 M2 里程碑「配额面板上线，`reset_at` 倒计时可见」产出对齐。

#### 3.5.6 文档对齐勘误行（§二 时区口径行）

§二 现状锚点表「时区口径（现状 bug）」行末注「本阶段 §3.2 修复」→ 实际修复 commit 为 `833f0a8`（M1 commit 1，P1-#7 时区修复已落 origin/master），`§3.2` 为历史残留引用，更正为「§五 P1-#7 修复节（`833f0a8` 已落 origin/master）」。随本 commit 同步修正，不单独开勘误 commit。

---

## 三·附、M1 验收节（v0.2.2.2 新增，JARVIS 终审基准内落档）

### M1-1 `slides=[]` 回退行为口径定稿（原 open 项，经实测勘误后关闭）

**结论：「同步响应完整携带 slides」为定稿口径，不存在「响应延迟到 SSE 流补齐」的设计路径。**

依据（实测 + 代码核对，均经 origin/master 落档）：

1. **现状即完整携带，open 项系复跑脚本取错字段层级（非工程 bug）**：`bd3ddc8` 报告 5000 字长文本 `/create` 同步响应 `data.slides=[]`、`numbering_style=null` 的 open 项，经 `f8220a0` 勘误复核——原脚本 `e2e5000.py` 读的是响应**顶层** `data.get("slides")`，而实际结构中 `slides`/`numbering_style` 嵌套在 `data` 字段内（`data.data.slides`），故恒读到缺省空值。同一 5200 字输入、`keep_original=true` 独立复核（user_id `claude-5000-check`）：`data.data.slides` 实为 **10 页**且首末页无截断，PPTX 导出 `slide_count=10` 与 `/create` 页数一致。
2. **代码路径无延迟补齐设计**：`_quick_mode_pipeline` keep_original 分支（`generation.py:262-321`）为**同步返回**——`_fill_keep_original()` 直接返回分页结果装入响应 `data` 并写 `sessions`；SSE 仅发布 `keep_original_progress` 进度帧（`generation.py:311-315` 空输入兜底 + `:447-452` 逐页进度），是**进度通知**而非「补齐缺失 slides 的数据通道」。分页契约「非空输入必产 ≥1 页」（`generation.py:379-380`，单测 `test_long_content_paginates_no_loss` 锁定）。collaborative / full_control 两条流水线的同步响应 `data` 仅含 outline + 暂停态消息（`generation.py:565-628`），slides 在 checkpoint 确认动作后生成——这是 checkpoint 暂停态语义，不属于本次讨论的超长输入回退场景。
3. **超长输入回退路径定稿**：超长单段输入（长文本 8000+ 字档同理）在 `/create` 同步响应内必须完整携带分页后的 `slides`（keep_original 分支）或 `slides` + `numbering_style`（非 keep_original 分支）；SSE 帧不得作为数据补齐依赖。M1 实施与验收时若出现 `data.slides` 为空的同 session 导出正常情形，按 bug 处理（对照 `_paginate_keep_original` 契约定位），不再作设计口径讨论。
4. **M1 验收断言（随 commit 2 同批落档，进 E2E 回归基线）**：
   - 长文本 ≥5000 字、`keep_original=true`：`/create` 同步响应 `data.data.slides` 页数 ≥1 且首/末页含内容行，`numbering_style` 缺省（设计口径，非 null 断言——keep_original 分支响应 dict 本就不含该键，见 `generation.py:321`；导出端由客户端传 `numbering_style_id` 独立解析，`export.py:58`）；
   - 同 session `POST /api/export/pptx` `slide_count` 与 `/create` 响应页数一致；
   - 非 keep_original 路径（8000 字档）：`data.data.slides` + `data.data.numbering_style` 均非空。

### M1-2 PR 拆分裁定（v0.2.2.3 更正：单 PR 双 commit，Hermes 组长最终裁定 + Codex 工程核认）

> **勘误注记（v0.2.2.3）**：本节 v0.2.2.2 原文写「2 PR（PR-A 积分制 + PR-B P1-#7 时区修复）」，系组长早期裁定残留。最终裁定（Hermes，与 Codex「402/端点可见性中间态」论证一致）为**单 PR 双 commit**：commit 1 时区修复与 commit 2 积分制切换同函数相邻分支（`:672-683`）耦合，拆 2 PR 会在中间态窗口内使 429 路径走旧时区逻辑、402 改判与 `quota/status` 端点不可见，v0.2.2.1 验收 #3「改判窗口与 M1 同批」在单次合入时点无法成立。按以下最终形态执行，本节正文不再保留旧 2 PR 措辞。

- **形态**：单 PR、双 commit，同批一次合入 origin/master。
  - **commit 1（P1-#7 时区修复）**：`generation.py:672-676` 改 UTC 口径（≤5 行，§五 P1 修复节方案；含 L672 `if not allowed:` 入口、L675 `datetime.now()`、L676 `reset_at` 计算行——`reset_at` 计算与时区修复合并 revert 才完整，L675/L676 同属时区域），独立 bug fix，可独立 revert。
  - **commit 2（积分制全套）**：DB 迁移（`user_credits` + `credit_ledger`，含 #12 `version` 乐观锁列 + #13 `idx_credit_ledger_user_time`）+ `check_credits()`（4 元组签名 `(allowed, balance, used, limit)`，§2.3 OR 判定 `(not allowed or not allowed_credits) and balance < required`，`311473b` 勘误收敛口径）+ 402/429 路由切换（`generation.py` 429 分支 `:677-684` → JSONResponse 平铺 + 429→402 改判，§3.3 唯一形态；`used/limit/reset_at` 平铺结构不变）+ `GET /api/quota/status`（§3.4 鉴权规则）+ **M1-1 口径确认与验收断言随本 commit 同批落档**（含 `numbering_style=null` 为 keep_original 设计口径单行注释，防后续 reviewer 再当 open 项捞起）+ **NIT 行号脚注随 commit 2 同批回补**（勘误：commit 2 下界 :677、:676 `reset_at` 计算行归 commit 1 时区修复域，与 commit 1 独立 revert 边界对齐；不另发独立勘误 commit）。
- **行号实测锁定（三方共核，实施时不再改）**：HEAD `3930d02` 实测 `generation.py` L672 `if not allowed:` / L675 `datetime.now()` / L676 `reset_at` 计算行 → commit 1 时区修复域 `:672-676`；L677 `raise HTTPException(status_code=429...)` 起至 L684 闭括号 → commit 2 切换动作域 `:677-684`；两区间相邻无交叠（`:676` 归 1、`:677` 起归 2）。历史措辞 `:676-684`/`:672-683` 均 NIT，以本行锁定为准。
  > **NIT 行号脚注（随 M1 commit 2 同批回补，不另发独立勘误 commit）**：**M1-2 :676-684 → :677-684**——勘误：下界 :677，:676 `reset_at` 计算行归 commit 1 时区修复域，与 commit 1 独立 revert 边界对齐。
- **理由**：commit 1 与 commit 2 覆盖同函数相邻分支（`:672-683`），一次合入统一消灭中间态窗口（时区 + 402 改判 + 端点可见性三层）；双 commit 粒度保留独立回滚能力（revert 时可按 commit 粒度），review 面不因合并而扩大。
- **执行分工**：Claude 主导起草（单 PR 双 commit + M1-1 口径确认）→ Hermes 组长终审单 PR → Codex 工程核认 + 测试三项（429→402 改判、P1-#7 日界复跑、quota/status 健康断言；E2E 基线 429/402 改判 + Vitest 全绿，R1 同一 PR 内完成不得分叉）。

---

## 四、G3 + G4：SSE 生产端补齐与协作编辑流

### 4.1 SSE 协议扩展（在锁定版 4+2 事件上补生产端，不破坏已锁 7 值 stage 枚举）

| 事件 | 触发 | data schema（本阶段定稿） |
|------|------|--------------------------|
| `slide_update` | 任一 slide 内容/样式变更后（**G4 落地**，见下行说明） | `{session_id, slide_index, op: "add"|"patch"|"remove", payload, rev}` |
| `generation_complete` | 流水线**非暂停态**终态（成功/失败/中止） | `{session_id, status: "success"|"error"|"aborted", slides_count, error?}` |

- **生产端落点（v0.2 修订，对应 findings #8）**：
  - `generation_complete`：`generation.py` 三条流水线在**非暂停态终态**处 `collab_publish(session_id, "generation_complete", ...)`。v0.1 措辞「终态」对 `collaborative`/`full_control` 两条流水线不成立——二者 `/create` 返回的是 checkpoint 暂停态（`GenerationResponse.status` 非终态），不是流水线终态；只有 `quick` 模式 `/create` 直接返回真终态。v0.2 明确：`generation_complete` 只在「无待处理检查点」的终态发，暂停态不发（改由 `collab_status` 的 `status` 字段标记暂停）。
  - `slide_update`：v0.1 写「`full_control` 检查点操作（`checkpoints.py`）每次 slide 变更后发布」有误——`checkpoints.py` 实测只有 `GET /flow/{session_id}` + `POST /flow/{session_id}/action`（记录决策），全后端**无 slide 编辑端点**（我侧 grep 全库确认）。`slide_update` 生产端改挂 **G4 WebSocket 编辑路由**（M4 落地时才有生产端；M3 内该事件只定 schema、不实现生产端，客户端侧 `useCollabStream.ts` 先行预留 type + 去重指纹即可）。
- **事件序号**：广播总线为每条事件分配单调递增 `event_id`（每会话 1 起），写入 SSE 帧 `id:` 字段 —— 这是 `Last-Event-ID` 断点续传的前提（现状总线只保留最近 100 条且无序号，MVP 靠 join 全量回放）。

### 4.2 `Last-Event-ID` 断点续传

1. 客户端重连时带 `Last-Event-ID: N`（浏览器 `EventSource` 自动带，自定义 SSE 需手动）；
2. 服务端从会话事件缓冲（现状 `generation.py:35-50` 为 `list + append + pop(0)` FIFO，非 deque，容量 100）取 `id > N` 的帧回放；**缓冲外则降级为全量 `snapshot` 重发——此时 `generation_progress` 进度帧不可回放（现状 snapshot 不含进度状态，边界声明见下行第 3 条），前端需容忍进度条重置；若需保留进度上下文，须将当前进度（`current_stage`/`current_slide`/`percent`）写入 snapshot payload，由 M3 评审拍板 A 案时补上（B 案则明确「进度不可回放」边界）**；
3. **进度帧可回放边界（v0.2 修订，对应 findings #9）**：v0.1 未界定 `snapshot` 是否含 `generation_progress`——实测 `_collab_snapshot()`（`generation.py:55-63`）只含 `mode/slides_count`，不含进度帧。v0.2 定稿两条边界：
   - **A 案（推荐）**：`snapshot` 增补当前进度帧（`stage`/`currentSlide`/`percent`），使降级重发可恢复进度上下文；缓冲外的漏收进度帧统一收敛到 snapshot 重发，不做「逐帧补发」（逐帧补发与「缓冲外」语义矛盾）。
   - **B 案**：明确「进度不可回放」边界——`generation_progress` 是瞬态通知帧，缓冲外漏收即丢，客户端靠 `generation_complete` 终态帧兜底渲染；snapshot 不含进度帧。
   两案二选一在 M3 评审时拍板（我侧倾向 A，成本约 +10 行，用户体验更完整）；**A 案未拍板前，M3 内实施默认按 B 案语义执行**——即缓冲外降级 snapshot 重发时进度帧不可回放，前端容忍进度条重置；M3 评审若拍板 A，则 snapshot payload 增补 `current_stage`/`current_slide`/`percent` 字段，降级重发可恢复进度上下文。无论选 A 或 B，`slide_update`/`generation_complete` 属持久帧，必须走 `event_id` 断点续传回放，不受此边界影响。
4. 鉴权（v0.2 修订，对应 findings #6）：MVP 依赖 `session_id` 透传（无鉴权，已知风险）；本阶段加 **session-lifetime token**——token 在会话**创建时**生成（非「随每次 `snapshot` 下发」，v0.1 措辞有误：`generation.py:88` snapshot 每次 join 重发，新连接每次 join 都会重发 snapshot，若 token 绑定在 snapshot 上则「一次性」与「后续帧逐帧校验」互斥），存内存（`_collab_tokens: Dict[session_id, token]`），`Last-Event-ID` 重连时校验该 token 是否属于该 session；token 生命周期 = 会话生命周期（会话结束/超时清理时失效），**非**一次性。
5. 出口验收：断网 30s → 恢复后事件无重复无丢失（回放去重指纹 `(event_id)` 替代现状 `(stage, pages, detail)`，`useCollabStream.ts:118`）。

### 4.3 协作编辑流（G4）

- **方案 A（推荐）：乐观锁 + 服务端仲裁** —— 客户端携带 `rev`，并发 patch 由服务端按 `slide_update` 事件顺序串行仲裁（广播总线已是有序队列，天然适配），冲突时后写者收 `collab_status` 的 `conflict` 状态并 rebase。实现成本最低，不改协议层。
- **方案 B：CRDT（Yjs/Automerge）** —— 客户端合并无冲突，但引入重依赖 + 服务端需持久化 CRDT 文档，工作量翻倍。
- 决策点（阶段内拍板）：编辑粒度 = slide 级（非字符级）。若后续要字符级协同编辑，直接升 B 案。
- 通道：WebSocket 升级（SSE 保留为通知层，决策已锁定于 `docs/phase3-tasks.md` §4 技术选型节）。服务端 WebSocket 与 SSE 共进程（FastAPI `WebSocket` 端点），房间模型 = session_id。
- 并发目标：单会话 ≤10 在线编辑者，p95 广播延迟 < 500ms。

### 4.4 与现有组件的接口

- `useCollabStream.ts`：新增 2 个事件 type（`slide_update`/`generation_complete`），`processedProgressRef` 去重指纹升级为 `event_id`；`Last-Event-ID` 由 `es.onopen` 时从本地存储读取重连前最后 id。
- `CollabStatusPanel.tsx`：`generation_complete` 终态渲染（status=success 转绿 / error 转 rose 错误态）——**v0.2 修订（对应 findings 表「CollabStatusPanel 终态渲染」勘误行）**：该组件现状**无任何 `generation_complete` 处理分支**，success 态渲染是**全新**渲染逻辑，不是「复用现有断线错误态样式」（v0.1 措辞不准确）；rose 错误态可**部分复用**现有断线错误态的 `animate-pulse` 底色类，但 success 绿色态须新写。`slide_update` 驱动进度条按 slide 粒度推进（`currentSlide` 字段已预留于 `useCollabStream.ts:34`，本阶段启用）。
- 测试：`__tests__/collabStream.test.ts` 扩 4 项（event_id 去重、Last-Event-ID 回放、generation_complete 终态、slide_update 驱动进度）；E2E 基线 55/56 补 1 项断线回放（1 flaky 项维持现状，另计 retry 加固任务）。

### 4·B M3 · B 案 SSE 增量事件（presence）协议草案（v0.2.4 新增，Claude 按 M3 启动令 A+B 裁定第 3 步交付）

> **本节为 B 线协议唯一设计基准**。M3 范围裁定 A+B（@JARVIS 2026-09-16）后，B SSE 增量事件协议在 M3 定稿、M4 落码；基座 `098cde9` 不动，M3 内零生产代码变更。独立草案全文见 `docs/m3-b-sse-incremental-events-draft.md`（M3 收口同 commit 落库），本节为登记 + 6 章节锁定口径 + 实码勘误行（行号以工作树 HEAD `bcd202c` 实测为准，M4 落码时随 commit 再核一次）。

#### 4·B.1 独立 `event` 命名空间（终审裁定 #2 锁定口径）

B 案 3 新增事件独立命名空间，不复用 `stage` 链路、不复用既有 4 事件名（`snapshot` / `generation_progress` / `collab_status` / `ping` schema 冻结，「只增不删不改义」）：

| 事件 | 触发 | data schema |
|------|------|------------|
| `viewer_joined` | 观察者 join 回放完成首帧 | `{session_id, viewer_id, ts, viewers_total}` |
| `viewer_left` | 连接关闭 / 30s 超时无重连 | `{session_id, viewer_id, ts, viewers_total}` |
| `presence_snapshot` | 新 join 者全量在场快照（join 回放首帧同批，先于后续增量） | `{session_id, viewers:[{viewer_id, last_seen_ts}], ts}` |

`viewer_id` = SSE 调用方 `user_id` 指纹（与 `/create` `quota_user_id` 同源三级解析链）；多标签页同指纹 = 同一 viewer（MVP 接受，登录体系立项后升级，R3/R5 同批）。

#### 4·B.2 payload 规则

1. 新增事件扩展只允许**新增字段**，不删不改义已发版字段；
2. 既有 4 事件 + 2 预留事件（`slide_update` / `generation_complete`，§4.1）M4 内字段增补同受「只增不删不改义」约束；
3. 客户端兼容：未知字段忽略；缺失新字段降级为「未上报」而非报错（旧客户端上 B 事件为未知 `event` 名 → EventSource 不触发监听器，天然静默，M4 升级前零回归面）。

#### 4·B.3 分发点清单（M4 落码验收项）

- **前端** `useCollabStream.ts`（`app/components/collab/`，行号 HEAD `bcd202c` 实测）：
  - D1 `:23-39` `CollabEvent` 联合类型**新增 3 成员**（schema 即 4·B.1 表），既有 4 成员零改动；
  - D2 `:41-50` `CollabStreamState` **新增** `viewersTotal` / `lastPresenceTs` 两字段（全缺失 = `null` →「未上报」降级）；
  - D3 `:111-136` `onEvent` 分发闭包**新增 3 分支**（只写 `viewersTotal`/`lastPresenceTs`，不复用 `processedProgressRef` 去重指纹）；
  - D4 `:138-141` `es.addEventListener` 注册块**新增 3 行监听器**；
  - D5 `:9` 头注释协议表同步 3 事件行（与 STATUS.md SSE 协议表同批）。
- **后端** `generation.py`（`_collab_event_log` 容量 100 条不变）：
  - S1 `:53` `collab_publish()` 总线新增 3 类事件写入；join 回放路径（`:94-102`）天然覆盖 `presence_snapshot`，无需新增回放通道；
  - S2 `:89-113` `event_stream()` 订阅端 per-connection 簿记（建立 → `viewer_joined`；Queue 关闭/30s 心跳超时 → `viewer_left`；join 回放完成首帧 → `presence_snapshot`）。
- **验收基线**：M4 落码 PR diff 面必须与 D1-D5 + S1-S2 清单一一对应，清单外 B 相关 diff 即终审打回（效力同 §4·B.5 三条收口硬约束）。

#### 4·B.4 预扣点章节（整篇计一次口径，引用组长终审裁定 #4 原文）

> 协作会话预扣次数口径：维持 M2 裁定——**按整篇计一次，不逐观察者拆分**。

- 预扣由**生成方（编辑者）单点触发**（`generation.py:685` 实测 `estimate_required(request.mode, ...)` 调用点，HEAD `bcd202c`）；**观察者不触发任何预扣路径**（B 事件 `required=0`，不入 `estimate_required` 折算域）；
- `mode="collaborative"` 落入既有分桶路径 `quota.py:39-40`（`if mode in ("collaborative", "full_control"): return 0`，实测），**无需新增枚举值**；单测 9 组 #6（`estimate_required("collaborative", 5000, "auto")` → 0，§3.5.1）即实码承载；checkpoint 动作计费走 §3.5.1 路由表末行「M4 单独立项」，不在 B 线；
- `debit_credits`（`quota.py:57-107`）零改动、`record_usage`（`quota.py:296-307`，`generation.py:751` 同步调用点）零改动——B 线不引入第二条计数通道，当日计数与「整篇计一次」同源闭合（见 §4·B.6 勘误行②）。

#### 4·B.5 429/402 路径分离标注 + 基座声明 + 三条收口硬约束

- **429 属 `check_quota` 免费额度耗尽路径**（`quota.py:262` 实测，`code=daily_free_quota_exceeded`，§3.5.4 四态表 429 行）；**402 属 `check_credits` 路径**（`quota.py:214` 实测，`code=insufficient_credits`）；B 线 presence 事件 `required=0` 不经 429/402 拦截域——M4 若观察到 presence 关联 4xx/429，按 bug 排查（是否误入 `/create` 计费域），不回改协议（@Codex M3 风险清单须标注）；
- **基座 `098cde9` 不动**：M3 全部 B 线交付物为纯文档（本稿 + 本节登记 + @Codex 排期/风险清单），M4 落码基准 = §4·B.3 分发点清单 + 4·B.1 schema 表；
- **M3 收口硬约束三条（验收项，触碰即打回）**：
  1. `usage_log` 复合主键 `(user_id, generated_at)`（`db.py:55-61` 实测：`:59` 主键、`:61` 索引 `idx_usage_log_user_date`，无自增 `id`、无 `AUTOINCREMENT`）保留 git 跟踪；
  2. `config.py` 绝对路径锚定——**完整路径勘误：`backend/app/core/config.py`**（`:12` `_PROJECT_ROOT` / `:15` `_DB_PATH` 锚定 `backend/yunzhang.db` / `:18-27` `_anchor_db_url` / `:75-76` 收尾锚定，HEAD `bcd202c` 实测；台账历史措辞 `backend/app/config.py` 系 NIT 路径误记，本行更正）；
  3. NIT 拦截式判定式（`generation.py:688` 注释 + `quota.py:227` 落码说明，§3.5.3 定稿版）。
- M3 启动令追加硬约束 ④ `quota.py:23` `estimate_required` 签名零改动 / ⑤ `quota.py:57-107` `debit_credits` 乐观锁结构零改动 / ⑥ `record_usage`（`quota.py:296-307`）`INSERT OR REPLACE` 语句不改动 / ⑦ 基座 `098cde9` 不动——B 线 M4 落码时全量生效。

#### 4·B.6 实码勘误行（M3 落档修正台账漂移，M4 落码时随 commit 再核）

| 勘误项 | 台账历史引用 | HEAD `bcd202c` 实测 | 处理 |
|--------|------------|------------------|------|
| ① 当日计数口径三处行号 | `:204-208 / :247-252 / :271-276`（M2 落码后漂移） | `since = _today_start_utc()` 三处 = `:201` / `:236` / `:268`；`COUNT(*) WHERE user_id=? AND generated_at >= ?` 三处 = `:205` / `:248` / `:273`（`get_quota_status_sync` / `check_credits` / `check_quota` 各一处，口径本身三处统一无误） | B 草案 / M3 风险清单引用以实测行号为准；口径统一 = `COUNT(*) WHERE user_id=? AND generated_at >= _today_start_utc()`，与「整篇计一次」同源 |
| ② `usage_log` 计数口径勘误（A 子项 2 落档） | §二 锚点表 DDL 行（`:43`）仅锁定复合主键 + `72cf9cc` 勘误行，未登记 `INSERT OR REPLACE` 语义 | `record_usage`（`quota.py:296-307` 实测）`INSERT OR REPLACE`（`:302`）在**复合主键 `(user_id, generated_at)` 下为 UPSERT 语义**（非「同名即替换」的自增 id 直觉）；`generated_at` 微秒精度（`strftime("%Y-%m-%d %H:%M:%S.%f")`，`:303` 实测）使同日两次调用主键恒不同 → **覆盖路径实际不触发，每次调用各记一行**，「同日超限短路 429」语义（§二 锚点表记账行）不变 | 本行登记为 M3 收口勘误正式落档（并入 §二 锚点表 DDL 行注记，不新建章节）；M4 起再改 `record_usage` 写路径须先核本行 |
| ③ `config.py` 完整路径 | 台账历史措辞 `backend/app/config.py` | `backend/app/core/config.py`（CWD 锚定修复 `c466fd2` 实际落点，M3 硬约束 ② 引用位置） | 见 §4·B.5 硬约束 ② 勘误行 |

#### 4·B.7 M4 衔接（防二次三方对齐）

- `slide_update` / `generation_complete` 生产端（§4.1）接入时 payload 扩展受 4·B.2 规则 2 约束；B 案 3 事件与 2 预留事件在 `event:` 命名空间内共存无冲突（4·B.1 隔离规则）；
- presence 事件为增量通知帧（非持久帧）：M4 同步落地 §4.2 `event_id` 断点续传时，presence 事件可入回放缓冲（容量 100 条内）但**不参与去重指纹升级**（4·B.3 D3 说明）；§4.2 进度帧可回放边界（A/B 案）拍板不受 B 线影响；
- `__tests__/collabStream.test.ts` 扩 3 项（`viewersTotal` 更新 / `presence_snapshot` 收敛 / 未知事件静默忽略），与 §4.4 既有 4 项扩展同 PR。

---

## 五、实施顺序与里程碑

| 里程碑 | 内容 | 前置 | 产出 |
|--------|------|------|------|
| M1 | DB 迁移（`user_credits` + `credit_ledger`）+ `check_credits()` + `/create` 切换 + `GET /api/quota/status` | 无 | 积分制可用，旧 10 次硬限降级为告警 |
| M2 | 429/402/503 统一 schema + proxy 最小解析 + `CreditPanel` + §3.5 预扣点接入（`estimate_required` + `debit_credits`/`refund_credits` + 单测 9 组 + E2E 改判 402） | M1 | 配额面板上线，`reset_at` 倒计时可见，预扣点可用 |
| M3 | 事件序号 + `slide_update`/`generation_complete` 生产端 + `Last-Event-ID` + per-session token | 无（与 M1 并行） | SSE 断点续传可用 |
| M4 | WebSocket 协作编辑（A 案乐观锁）+ 冲突 rebase + 4 项专属测试 + E2E 补断线回放 | M3 | 协作编辑流 MVP，两编辑器场景验证 |

**风险与对策**:
- **R1 积分切换影响 E2E 基线**：M1 切换后基线 429 连发用例需改判定源（积分不足 402）——切换与基线更新同一 PR 内完成，CI 红不允许合入。
- **R2 双路由前缀（`/api/generation` + `/api/collab`）**：事件序号若在两条前缀分别起算会乱序——序号总线挂在 `session_id` 维度而非路由维度，路由前缀只影响 URL，不影响 `event_id`。
- **R3 `anon-{IP}` 指纹不稳**（NAT/代理环境 IP 漂移 → 积分账户串号）：本阶段不做登录，接受该限制并在配额面板文案标注「匿名账户积分不跨设备」；登录体系另立项。
- **R4 长文本 8000+ 字 ×1.5 系数**：系数拍脑袋值，上线前用 5000/8000/15000 三档实测 token 消耗回归校准（数据在材料库 Phase 2 预研，见 MEMORY 材料库条目）。
- **R5 `user_id` 轮换领赠（v0.2 新增，对应 findings #1）**：v0.1 曾设想「注册赠 100」，但 `user_id` 来自客户端（localStorage 指纹 / 请求体可覆盖），无服务端锚定（`generation.py:665-670`），无登录闸门 → 客户端可主动轮换 user_id 无限刷白嫖赠额。v0.2 对策：**M1 不赠额**（`user_credits.balance` 初值 = 0，不做「首见 user_id 赠 100」逻辑），赠额统一挂到登录体系立项后（随 M4 之后的版本再开）；若后续做登录，赠额须绑定服务端可验证的身份锚点（登录 session），不复用 anon 指纹。
- **R6 `quota/status` oracle（v0.2 新增，对应 findings #2）**：v0.1 §3.4 写的 `GET /api/quota/status?user_id=...` 在无鉴权下可枚举任意 user_id 读余额 + 流水 5 条 = 敏感数据 oracle。v0.2 对策：§3.4 已改为「端点不接受任意 `user_id` 查询参数，只查当前会话指纹对应账户，跨 user_id 查询一律 404」。登录体系立项后升级为 session-bound 鉴权。

**P1 修复节（v0.2 新增，对应 findings #7 / #8 / #9 / #10，M1 开工前须随本文件一起推上）**:
- **P1-#7 时区错配（真 bug，现状即存在）**：`quota.py:15-18` `_today_start_utc()` 按 UTC 零点截断日窗（口径正确）；`generation.py:674-675` `reset_at` 用 `datetime.now()`（本地时区，无时区对象）次日 0 点计算，注释「与 quota 重置口径一致」是错的（UTC+8 下偏差 8h，UI 倒计时到点仍 429）。**修复方案（≤5 行，M1 开工前顺手修，随 v0.2 终审 commit 一起推，不单独起提交）**：
  1. `generation.py:674-675` 改为 `now = datetime.now(timezone.utc)`，`reset_at` 按 UTC 次日 0 点计算，`strftime("%Y-%m-%dT%H:%M:%SZ")`；
  2. `generation.py:674` 注释勘误为「与 quota 重置口径一致（均按 UTC 零点）」；
  3. 不动 `quota.py`（其口径本就正确，bug 在 `generation.py` 误用本地时区——若实施侧按组长裁定误改 `quota.py`，会破坏日窗截断语义，须以本节勘误定位为准）。
  改动不影响 E2E 基线 429 连发路径（不跨 UTC 边界），须与 §一 验收标准#5「时区口径统一」的同一窗口内验证一次。
- **P1-#8 `slide_update` 生产端改挂 G4**：见 §4.1 修订（`checkpoints.py` 无 slide 编辑端点，`slide_update` 生产端改挂 G4 WebSocket 编辑路由，M3 内只定 schema + 客户端预留 type）。
- **P1-#9 snapshot 增补进度帧或明确边界**：见 §4.2 修订（A/B 案二选一，M3 评审拍板，我侧倾向 A）。
- **P1-#10 `user_credits.daily_cost` 增补 `last_cost_date` 列**：见 §3.1 修订（「当日消耗」须有日期锚点做清零语义，否则跨日不重置）。

**明确不做（本阶段边界外）**:
- 支付通道选型/接入（仅占位 `/pay`）
- 登录/注册体系（沿用 `anon-{IP}` 指纹 + localStorage；赠额挂到登录体系立项后，见 R5）
- 字符级协同编辑（slide 级够用，CRDT 留后手）
- 多区域部署下的配额一致性（当前单实例 SQLite，`config.py` 已绝对路径锚定 `backend/yunzhang.db`；多实例时配额表需迁移，另立项）

---

## 六、文档变更记录

| 版本 | 日期 | 变更 |
|------|------|------|
| v0.1 | 2026-09-14 | 初稿（Claude）：基于 `7ff2dce` 基线实测现状锚点撰写；429 响应体口径与 `72cf9cc` 勘误记录对齐 |
| v0.2 | 2026-09-14 | 修订稿（Claude）：并入 Hermes 组长复核意见（9 条成立 / 2 条部分成立判定）+ Claude 设计审查 findings 11 条（P0 6 条 + P1 4 条 + P2 1 条）。变更点：§一 验收标准#1 删「注册赠 N 积分」；§二 新增时区错配 bug 行；§3.1 迁移顺序去赠额 + `daily_cost` 增 `last_cost_date`；§3.3 定稿 429/402 并存 schema + 唯一 429 路径 + JSONResponse 机制 + M1 前置基线断言粒度确认；§3.4 `quota/status` 鉴权规则（禁跨 user_id 枚举）；§4.1 `generation_complete` 改非暂停态终态 + `slide_update` 改挂 G4；§4.2 进度帧可回放边界（A/B 案）+ session-lifetime token；§4.4 `CollabStatusPanel` success 态渲染勘误；§五 新增 R5/R6 + P1 修复节（#7 时区 / #8 / #9 / #10） |
| v0.2.1 | 2026-09-14 | 终审补完（Claude）：按 Hermes 组长终审 4 条 WARN 补齐——#6 §4.2.4 token 语义改 session-lifetime（会话创建时生成，多用途，非「一次性」）；#9 §4.2.2 加「缓冲外降级 snapshot 时进度帧不可回放」边界声明（A 案未拍板前默认 B 案语义，M3 拍板 A 则 snapshot payload 增补 `current_stage`/`current_slide`）；#10 §3.1 DDL 补 `last_cost_date DATE NOT NULL DEFAULT '1970-01-01'` 列；#12 §3.1 DDL 补 `version INTEGER NOT NULL DEFAULT 0` 乐观锁列 + M2 扣减 SQL `WHERE version=?` 原子更新口径。对应 Codex 补充 findings #12/#13（#13 已有 `idx_credit_ledger_user_time` 索引无需另开） |
| v0.2.2 | 2026-09-14 | 组长终审意见（Hermes）11 条 findings 判定 + M1 排期门槛裁定后，v0.2 修订稿终稿定稿（Claude）——§3.3 429/402 定稿 schema 收敛为唯一形态（平铺顶层 `code`），删除「MVP 过渡期嵌套结构并存」兼容段（对应组长裁定 #4）；§3.3 稳态 429 唯一路径锁定为「免费额度耗尽且余额=0」（#3）；P1-#7 时区修复方案明确不动 `quota.py`、只改 `generation.py:674-675`，随终审 commit 一次推上（#7）；STATUS.md L123 背书降调行已随 `2778887` 落盘（#11）。此版为 v0.2 修订稿终稿，待组长终审 commit 推上 origin/master 后 M1 方可排期 |
| v0.2.2.2 | 2026-09-15 | 新增「三·附、M1 验收节」（Claude）：M1-1 `slides=[]` 回退行为口径定稿为「同步响应完整携带」——原 open 项（`bd3ddc8` 5000 字长文本 `data.slides=[]`）经 `f8220a0` 勘误复核确认为复跑脚本取错字段层级（顶层 vs `data` 内嵌），非工程 bug 非设计缺口；定稿 4 条 M1 验收断言随 PR-A 同批落档。M1-2 PR 拆分裁定 2 PR（PR-A 积分制 + PR-B P1-#7 时区修复，JARVIS 核认通过），执行分工 Claude 起草 → Hermes 组长终审 → Codex 核认 + 测试。JARVIS 终审基准 = 本稿落档 commit + `bd3ddc8` + `f8220a0` |
| v0.2.2.3 | 2026-09-15 | M1-2 措辞勘误（Claude，经 Hermes 组长裁定授权）：按组长最终裁定「单 PR 双 commit」更正 M1-2 节 2 PR 残留措辞（commit 1 = P1-#7 时区修复 ≤5 行独立 bug fix；commit 2 = DB 迁移 + `check_credits()` + 429→402 切换 + `GET /api/quota/status` + M1 验收节文档），并同步头部状态行；slides=[]「同步响应完整携带」定稿与 4 条验收断言不变，终审基准顺延为本稿落档 commit |
| v0.2.2.4 | 2026-09-15 | M1-2 行号实测锁定（Claude，三方共核 Hermes/Codex/Claude 一致）：commit 1 域 `:672-676`（含 L676 `reset_at` 计算行）、commit 2 域 `:677-684`（L677 `raise HTTPException(429)` 起至 L684 闭括号），历史措辞 `:676-684`/`:672-683`/`:672-675` 均 NIT 以实测锁定为准；NIT 行号脚注随 commit 2 同批回补规则落档；实施行号基线锚定完成 |
| v0.2.3 | 2026-09-15 | M2 预扣点接入设计 + 文档对齐（Claude）：新增 §3.5（`estimate_required()` 计费点路由映射 6 场景 + `debit_credits()`/`refund_credits()` version 乐观锁实现 + `/create` 402/503 分支激活 + 拦截式判定式定稿取代 M1 OR 判定式残留 + M2 两 PR 拆分产出清单：PR 1 折算函数/扣减实现/单测 9 组/E2E 改判，PR 2 CreditPanel/402 断言）；§二 时区口径行勘误 `833f0a8` 已修复（§3.2 → §五 P1-#7）；§五 M2 里程碑行同步 §3.5；`check_credits` docstring 判定式对齐 §3.5.3（随 M2 PR 1 同批写回） |
| v0.2.4 | 2026-09-16 | M3 启动令 A+B 裁定（@JARVIS）+ B SSE 增量事件协议草案登记（Claude，启动令第 3 步）：新增 §4·B（B 案 3 事件独立 `event` 命名空间 `viewer_joined`/`viewer_left`/`presence_snapshot` + 会话开启全量快照；payload「只增不删不改义」+ 既有 4+2 事件 schema 冻结 + 客户端未知字段忽略/缺失降级「未上报」；分发点清单 D1-D5（`useCollabStream.ts` 实测行号）+ S1-S2（`generation.py` 总线/订阅端）逐条列明为 M4 落码验收项，清单外 B 相关 diff 即打回；预扣点章节直接引用组长终审裁定 #4 原文「按整篇计一次，不逐观察者拆分」——预扣由生成方单点触发（`generation.py:685` 实测），`mode="collaborative"` 落 `quota.py:39-40` 既有分桶路径无需新增枚举值，观察者零预扣路径；429/402 路径分离标注（429 = `check_quota` 免费额度耗尽 `quota.py:262` 实测 `code=daily_free_quota_exceeded`，402 = `check_credits` 路径 `quota.py:214` 实测，presence 事件 `required=0` 不经拦截域）；基座 `098cde9` 不动 + M3 零代码变更声明；三条收口硬约束落档（① `usage_log` 复合主键 + 索引保留 git 跟踪 `db.py:55-61` 实测 ② `config.py` 绝对路径锚定，完整路径勘误为 `backend/app/core/config.py:12-15/:18-27/:75-76` ③ NIT 拦截式判定式 `generation.py:688` + `quota.py:227`）+ 启动令追加 ④⑤⑥⑦ 全量收录；实码勘误行 3 项（当日计数口径三处行号以 HEAD `bcd202c` 实测 `:201/:236/:268` since + `:205/:248/:273` COUNT 为准，台账历史 `:204-208/:247-252/:271-276` 系 M2 落码后漂移；`record_usage` `INSERT OR REPLACE` 在复合主键下 UPSERT 语义 + 微秒精度 `generated_at`（`quota.py:296-307` 实测）覆盖路径实际不触发、每次调用各记一行——「同日超限短路 429」不变；`config.py` 路径勘误）。A 子项 2/3 文档落档（`usage_log` 分页计数口径勘误 + 三条收口硬约束验收项）随本 commit 并入 §4·B.5/§4·B.6，独立草案全文 = `docs/m3-b-sse-incremental-events-draft.md`（同批落库）。§4.1-4.4 既有锁定内容零改动，M3 全部交付物零生产代码变更 |

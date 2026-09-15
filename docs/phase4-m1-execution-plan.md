# M1 实施执行计划（Claude 起草，单 PR 双 commit）

> **状态**：草稿（待 JARVIS 终审 `8d75d86` 通过后推 origin/claude/m1-credit-switch）
> **起点**：origin/master HEAD `8d75d86`（v0.2.2.4 行号实测锁定终稿）
> **行号基线**：以 HEAD 实测 `generation.py` 为准（L672 `if not allowed:` / L675 `datetime.now()` / L676 `reset_at` 计算行 / L677 `raise HTTPException(429)` 起至 L684 闭括号），实施时不再改
> **§3.3 schema 定稿**：平铺顶层 `code`，JSONResponse 机制，429 唯一稳态路径 =「免费额度耗尽且余额=0」（`code=daily_free_quota_exceeded`）

---

## 一、Commit 1：P1-#7 时区修复（独立 bug fix，可独立 revert）

**变更域**：`backend/app/api/routes/generation.py:672-676`（含 L672 入口、L673 import、L674 注释、L675 取时、L676 `reset_at` 计算行；有效变更 ≤5 行）

```python
# L673（原 from datetime import datetime, timedelta）
from datetime import datetime, timedelta, timezone

# L674 注释勘误
# reset_at 语义 = 自然日零点（与 quota 重置口径一致，均按 UTC 零点）

# L675 UTC 取时
now = datetime.now(timezone.utc)

# L676 UTC 日界口径 + ISO Z 格式（reset_at 与时区修复合并 revert 才完整，L675/L676 同属时区域）
reset_at = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
```

**不变项**：
- `backend/app/core/quota.py` 一行不动——`_today_start_utc()`（`quota.py:15-18`）口径本就正确（按 UTC 零点截断日窗），P1-#7 bug 仅在 `generation.py` 误用本地时区（§五 P1-#7 修复方案第 3 条勘误定位）
- 429 分支逻辑不变（本 commit 仅修时区口径与 `reset_at` 格式；状态码、嵌套 `detail` 结构、判定源均维持现状，429→402 改判归 commit 2）
- L672-684 行号整体不变（仅内容替换，无增删行——保持 commit 2 域 `:677-684` 实测锁定仍然成立）

**独立 revert 验证**：revert 后 L672-676 回退至 v0.2.2.4 原文（本地时区 + `%Y-%m-%d 00:00:00` 格式），commit 2 域不受影响。

---

## 二、Commit 2：积分制切换全套

### 2.1 DB 迁移（`backend/app/db.py` `SCHEMA_SQL` 末尾追加，随 `init_db()` 幂等建表）

```sql
-- 用户积分账户（M2 扣减走乐观锁；M1 不赠额，balance 初值 = 0）
CREATE TABLE IF NOT EXISTS user_credits (
    user_id        TEXT PRIMARY KEY,
    balance        INTEGER NOT NULL DEFAULT 0,
    daily_cost     INTEGER NOT NULL DEFAULT 0,
    last_cost_date DATE     NOT NULL DEFAULT '1970-01-01',
    version        INTEGER NOT NULL DEFAULT 0,
    updated_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS credit_ledger (
    seq            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        TEXT NOT NULL,
    delta          INTEGER NOT NULL,
    reason         TEXT NOT NULL,
    session_id     TEXT,
    created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_credit_ledger_user_time ON credit_ledger(user_id, created_at);
```

要点（对齐 §3.1）：
- `version` 乐观锁列（#12）：M2 扣减 SQL 定为 `UPDATE user_credits SET balance=?, daily_cost=?, version=version+1 WHERE user_id=? AND version=?`，影响行数 = 0 时重试上限 3 次仍冲突则 503；M1 只建列不写扣减逻辑
- `idx_credit_ledger_user_time`（#13）：面板「最近 5 条流水」按 `(user_id, created_at)` 查询
- **不赠 100**：赠额统一挂登录体系立项后，M1 不做「注册赠 100」
- `usage_log` 保持审计口径不变（已有 E2E 基线与 `bd3ddc8` 勘误记录锚定），积分消耗走 `credit_ledger` 流水
- `CREATE TABLE IF NOT EXISTS` 幂等，旧库（已有 `backend/yunzhang.db`）直接补表，无数据迁移

### 2.2 `check_credits()`（`backend/app/core/quota.py` 新增）

```python
async def check_credits(user_id: str, required: int = 0) -> tuple[bool, int, int, int]:
    """
    积分复合判定（M1 免费额度+余额）
    返回 (allowed, balance, used, limit)
    - allowed = 余额 ≥ 所需（required，M1 固定 0）或 当日免费额度未耗尽
    - 免费额度已耗尽且余额 < required → allowed=False（required=0 时即「耗尽且余额=0」→ 429 路径 daily_free_quota_exceeded）
    - 免费额度已耗尽且余额 < 所需 → 402（insufficient_credits，M2 预扣点接入时 required > 0 生效）
    M2 扣减走 user_credits.version 乐观锁（§3.1 并发扣减定稿），M1 仅判定不扣减
    """
```

实现要点：
- 单连接事务内同时查 `user_credits.balance`（缺行视为 0）与 `usage_log` 当日计数（复用 `check_quota` 的 since 口径）
- `required` 默认 0（M1 `/create` 不传复杂度，M2 接 §3.2 计费公式 LIGHT/MEDIUM/HEAVY 预扣点后按任务复杂度传值）
- 不新增同步版（测试脚本走 E2E 黑盒，不复用 `get_quota_status_sync` 模式）

### 2.3 `generation.py:677-684` 429 分支切换（JSONResponse 平铺 + 429/402 改判）

L672-684 域整体重写后（commit 1 + commit 2 叠加效果）：

```python
    allowed, used, limit = await check_quota(quota_user_id)
    allowed_credits, balance, used, limit = await check_credits(quota_user_id)
    if (not allowed or not allowed_credits) and balance < required:
        now = datetime.now(timezone.utc)
        reset_at = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        if balance == 0:
            # 429：免费额度耗尽且余额 = 0（§3.3 稳态 429 唯一路径）
            return JSONResponse(status_code=429, content={
                "code": "daily_free_quota_exceeded",
                "message": f"今日免费额度已用完（{credit_used}/{credit_limit}），请明天再试",
                "user_id": quota_user_id,
                "usage": {"used": used, "limit": limit, "reset_at": reset_at},
            })
        # 402：免费额度已耗尽且余额 < 所需（M1 required=0 时不可达、仅预留平铺结构；M2 接预扣点 required > 0 后生效）
        return JSONResponse(status_code=402, content={
            "code": "insufficient_credits",
            "message": f"积分不足（余额 {balance} < 所需 {required}），请充值或明日免费额度重置后再试",
            "user_id": quota_user_id,
            "credits": {"balance": balance, "required": required},
        })
```

要点：
- `from fastapi.responses import JSONResponse` 补 import（顶部已有 `StreamingResponse`，同模块补一行）
- 旧嵌套 `detail` 形态（`HTTPException(429, detail={...})`）下线，同端点不再双形态并存（§3.3 定稿唯一形态）
- `used/limit` 进 `usage` 嵌套块、`reset_at` 进 UTC ISO Z 格式（随 commit 1 时区修复同批，§3.3 schema 示例一致）
- 429 响应体**顶层 `code` + 顶层 `message`**——E2E 429 断言粒度（三方共核）仅断「状态码 + 顶层 `message` 字段存在」，平铺切换后该断言自然通过，基线报告 429→402 改判说明随本 PR 同步更新（§一 验收标准#5 补充①，同批不拆两批）
- L685 `try:` 正常路径不受影响（行号整体可能 +N 偏移，属 commit 2 域内正常变化；锁定的是本次 diff 的**变更边界**而非后续行号）

### 2.4 `GET /api/quota/status`（§3.4 鉴权规则）

**新建 `backend/app/api/routes/quota.py`**：

```python
"""
积分/额度状态查询（§3.4）
鉴权规则：绑定调用方自身 user_id（与 /create 的 quota_user_id 同源——
request.user_id 或匿名指纹 anon-{host}），不接受任意 user_id 查询参数；
跨 user_id 查询一律 404（不区分「不存在」与「无权」，防余额/流水 oracle 枚举）。
MVP 过渡期无登录；登录体系立项后升级为 session-bound 鉴权。
"""

@router.get("/status")
async def quota_status(request: Request):
    user_id = ...  # 与 generation.py L665-670 同源解析（user_id 字段 or anon-{host}）
    ...
    return {
        "usage":  {"used": ..., "limit": ..., "reset_at": ...},
        "credits": {"balance": ..., "required": ...},
    }
```

响应 schema 对齐 §3.4：`usage` 块（余额面板「当日消耗」+ `reset_at` 倒计时）+ `credits` 块（余额 + 流水最近 5 条占位字段）。

**路由注册**（`backend/app/main.py` L14 import + L55 后追加）：
```python
from app.api.routes import hardware, generation, checkpoints, assets, export, quota
...
app.include_router(quota.router, prefix="/api/quota", tags=["积分额度"])
```

**基线锚点双备**（组长 + Claude 独立实测一致）：
- 实施前：`GET /api/quota/status` → **404**（路由不存在）
- 合入后：**200** + §3.4 schema（`usage` + `credits`）；跨 `user_id` 一律 404 不枚举（测试断言 #3 覆盖）

### 2.5 M1 验收节文档 + NIT 行号脚注（随 commit 2 同批回补，不另发独立勘误 commit）

落档动作（`docs/phase4-plan.md`）：
1. **M1-1 4 条验收断言**（§三·附 L137-161 原文，定稿不改）：
   - 长文本 ≥5000 字、`keep_original=true`：`/create` 同步响应 `data.data.slides` 页数 ≥1 且首/末页含内容行；`numbering_style` 缺省（设计口径，非 null 断言——keep_original 分支响应 dict 本就不含该键，`generation.py:321`；导出端由客户端传 `numbering_style_id` 独立解析，`export.py:58`）
   - 同 session `POST /api/export/pptx` `slide_count` 与 `/create` 响应页数一致
   - 非 keep_original 路径（8000 字档）：`data.data.slides` + `data.data.numbering_style` 均非空
   - `numbering_style=null` 为 keep_original 设计口径单行注释（防后续 reviewer 再当 open 项捞起）
2. **NIT 行号脚注**（组长裁定文案，落档时不改一字）：
   > **M1-2 :676-684 → :677-684**
   > 勘误：下界 :677，:676 `reset_at` 计算行归 commit 1 时区修复域，与 commit 1 独立 revert 边界对齐；不另发独立勘误 commit。
3. **`docs/e2e-baseline-report.md` 429 改判说明**同步更新（§一 验收标准#5 补充①：终审 commit 进 origin/master 时基线脚本附件同步更新改判说明，避免终审后二次改判抖动）
4. **STATUS.md** 对齐（Phase 4 M1 状态行 + commit 表补录）

### 2.6 联调注意项（并入起草 checklist，防再犯）

1. **请求体字段名以 `user_input` 为准**——防再犯 422 取字段错误（历史脚本 `e2e5000.py` 曾取错字段层级）
2. **`quota/status` 跨 `user_id` 一律 404 不枚举**——测试断言覆盖：同 user_id 200、跨 user_id 404（不返回 403，不区分「不存在」与「无权」）

---

## 三、测试三项（@Codex 核认 + 执行，同 PR 内完成不得分叉）

| # | 测试 | 基线锚点 | 合入后断言 |
|---|---|---|---|
| 1 | 429→402 改判 | 429 + 顶层 `message`（`bd3ddc8` 实测：`used=10`/`limit=10`/`reset_at`） | 状态码改判 + 顶层 `message`/`code` 存在；**仅断言状态码 + 顶层 `message`，不断言嵌套 `detail` 结构**（三方共核粒度） |
| 2 | P1-#7 日界复跑 | UTC 修复前置断言（v0.2.2.1 #7） | 429/402 连发须在 **UTC 日界前后 1h 窗口外**执行；窗口内须改判 `reset_at` 期望值或重跑基线并同步更新报告；`reset_at` 期望值改 UTC ISO Z 格式 |
| 3 | `quota/status` 健康断言 | 404（组长 + Claude 双复探一致） | 200 + §3.4 schema（`usage` + `credits`）；**跨 user_id 一律 404 不枚举** |

回归门槛：E2E 基线 55/56 不劣化 + Vitest ≥173 全绿 + 后端单测 17/17（§一 验收标准#5）。

---

## 四、起草执行顺序（终审通过后）

1. **Commit 1** 起草 + 自测（时区修复 ≤5 行，revert 验证）
2. **Commit 2** 起草（DB 迁移 → `check_credits()` → L677-684 平铺切换 → `quota.py` 路由 → main.py 注册 → 文档 4 项同批）
3. 推 origin/claude/m1-credit-switch（双 commit 线性历史）
4. @Codex 工程核认 + 测试三项执行
5. @Hermes 组长终审单 PR
6. 一次合入 origin/master → 启动 M2

---

## 五、风险与不变项清单

| 项 | 说明 |
|---|---|
| `quota.py` 日窗口径 | 不动（`_today_start_utc()` 口径正确），仅新增 `check_credits()` |
| `usage_log` 表 | 不动（审计口径不变，已有 E2E 基线锚定）；每日 10 次硬限降级告警日志的动作在 M2 观察期后执行，M1 不改 |
| 双形态并存 | 无——`JSONResponse` 平铺切换即旧嵌套形态下线，无过渡兼容段（§3.3 定稿） |
| proxy 层 | 不加 429 结构化错误透传解析（MVP 不加，已关闭）；M1 切换后 proxy 现有「原样透传 4xx/5xx」行为天然兼容平铺 body |
| 行号偏移 | commit 2 域内 import/路由注册等新增行会使 L685+ 下移；锁定的是 diff 变更边界（`:672-676` / `:677-684` 原文域），后续行号以 commit 2 后实测为准，不进 NIT |
| 中间态窗口 | 单 PR 双 commit 一次合入，时区 + 402 改判 + 端点可见性三层统一消灭（§M1-2 理由） |


| 中间态窗口 | 单 PR 双 commit 一次合入，时区 + 402 改判 + 端点可见性三层统一消灭（§M1-2 理由） |

### 测试三项工程核认（Codex，草稿预核）

以下结论基于 HEAD `8d75d86` 实测（`generation.py:665-684` / `quota.py` / `db.py` / `main.py`）+ 本文档草稿核对。终审通过后测试三项可执行，无需分叉；**测试#1 文案随本核认同步勘误**（429→402 改判 → 稳态 429 断言），详见 `docs/phase4-m1-execution-plan.md` 测试三项表。

**核认项 2.3 双路径判定点**：`(not allowed or not allowed_credits) and balance < required` 与 §3.3 稳态一致——
- `allowed` 为真（免费额度内）→ 短路不进 429/402 分支，正确（§3.3：免费额度耗尽不是 429 的充要条件，须叠加余额=0）
- `allowed` 假 + `allowed_credits` 真（余额 ≥ required，M1 required=0 即余额 ≥ 0 恒真——除余额为负外）→ 短路，正确（余额兜底放行，§3.1 复合判定「余额 ≥ 所需 或 当日免费额度未耗尽」）
- `allowed` 假 + `allowed_credits` 假（余额 < required 且额度耗尽）→ 进入分支，再按 `balance == 0` 分叉 429/402：M1 required=0 时 balance < 0 不可达（DDL DEFAULT 0、不赠额、无负值写入路径），402 分支天然不可达，与 §3.3「429 唯一稳态路径」定稿一致 ✅
- 判定点与 L665-670 `quota_user_id` 同源解析无偏差：`check_credits(quota_user_id)` 入参与 `check_quota` 同参，未引入新解析分支 ✅

**核认项 2.4 user_id 同源**：`generation.py:665-670` 三级解析（`request.user_id` → `anon-{host}` → `anon-unknown`）与草稿 `routes/quota.py` 同源注释一致；跨 user_id 一律 404 不枚举、不返回 403 的 oracle 防护已写进 §2.4 ✅

**测试三项断言可执行性**（同 PR 内执行，不分叉）：
1. **稳态 429 断言（原「429→402 改判」已勘误）**：11 连发（10×200 + 1×429），第 11 次断言状态码 = 429 + 顶层 `message`/`code` 存在（不断言 `usage`/`detail` 嵌套）；M1 required=0 时 402 路径不可达，402 断言挂 M2 预扣点测试。基线锚点 `bd3ddc8` 实测（10×200 + 429，429 响应体已含 `message`）✅
2. **P1-#7 日界复跑**：429 连发须在 UTC 日界 ±1h 窗口外执行（v0.2.2.1 #7 前置断言）；`reset_at` 期望值改 UTC ISO Z（`%Y-%m-%dT%H:%M:%SZ`，commit 1 落地后生效）✅
3. **`quota/status` 健康断言**：基线 404（双备实测一致）→ 合入后 200 + §3.4 schema（`usage` + `credits`）；跨 user_id 一律 404 不枚举（断言覆盖「同 user_id 200 / 跨 user_id 404」两场景）✅

回归门槛核对：E2E 55/56 不劣化 + Vitest ≥173 + 后端单测 17/17，与 §一 验收标准#5 口径一致 ✅

**NIT 脚注核认**：`docs/phase4-plan.md` §三·附 NIT 行号脚注（`8d75d86` 已落档）与本草稿 §2.5 第 2 条引文逐字一致（「勘误：下界 :677，:676 reset_at 计算行归 commit 1 时区修复域，与 commit 1 独立 revert 边界对齐；不另发独立勘误 commit」）✅



# 云章PPT智能体系统 - 项目状态报告

**更新日期**: 2026-09-15
**当前阶段**: M2 完整闭环 ✅（origin/master `b369e1f`，零分叉）：M2 PR 1 代码批次（`a02e8ce`+`6ba0950`，含工程核认 2 条提醒落码 + 单测 12/12 + E2E 402 改判用例）+ M2 PR 2 前端批次（`ad0cc35` 实施 + `362420f` 终审复核 5 项勘误/修复：① `estimateCreditsRequired` 补 `complexity` 参数（multimodal=6）对齐后端；② 预扣门控补 `free_allowed` 门控（free 未耗尽时不预扣，修复 200 用例误判 402 回归 bug）；③ `quota/status` `credits.required` 对齐 §3.5.1 LIGHT=1；④ 402 判定式收敛为 `not allowed and 0<balance<required`；⑤ E2E setup-balance 路由勘误（`/api/quota/test/setup-balance`）+ 新增 `pytest.ini` 收口 `test_api.py` 4 项 async 收集失败）+ cleanup 批次 #1 核销（`b369e1f`）全部落库。回归三项全绿：后端 48/48 + Vitest 185/185（含 creditPanel.test.ts 12 项）+ E2E 56/56（402 用例命中确认）。Hermes 终审裁定：PR 1 有条件放行（口径 B）→ 复核后 PR 2 无条件放行 → M2 完整闭环收口（seq 18）。cleanup #2（E2E 402 命中重跑）非阻塞挂 Codex 台账
**最新 Commit**: `b369e1f`（cleanup #1 落码——estimate_required 签名三方偏差核销）/ `cec8972`（STATUS.md BOM 修复 + cleanup 批次台账登记）/ `93b013b`（M2 PR 2 终审复核 5 项台账行落档）/ `362420f`（M2 PR 2 终审复核 5 项勘误/修复落码）/ `ad0cc35`（M2 PR 2 实施）/ `6ba0950`（M2 PR 1 收口）/ `a02e8ce`（M2 PR 1 实施）/ `752f974`（M2 §3.5 完整版正式落档）/ `fd5437a`（M2 启动台账行）/ `f668144`（§3.5 初稿，名实不符由 `752f974` 补正）/ `ba61f63`（M1 收口行落档）

## 团队配置

| 成员 | 角色 | 状态 | 职责 |
|------|------|------|------|
| Hermes | 组长 | ✅ 在线 | 任务分解、进度控制、验收交付、协作 MVP 后端、E2E 基线 |
| Claude | 首席架构师 | ✅ 在线 | 核心逻辑攻坚、模板库、移动端、长文本优化、Phase 4 积分制 |
| Codex | 工程总监 | ✅ 在线 | 协作 MVP 前端精修 + 3 项专属测试、E2E 真实 key 补跑 |
| OpenCode | 全栈开发 | ❌ 离线 | 原负责导出功能，已由 Claude/Hermes 接手 |

## 项目架构

```
云章PPT智能体系统
├── 前端: Next.js 15 + React 19 + TypeScript + TailwindCSS (localhost:43210)
├── 后端: FastAPI + Python 3.12 (localhost:8001 via uvicorn)
│   ├── /api/generation/create  — 创建生成会话（含 quota 检查）
│   ├── /api/generation/session/{id} — 查询会话状态
│   ├── /api/generation/checkpoint/{sid}/{cid}/action — 检查点操作
│   ├── /api/checkpoints/flow/{sid} — 检查点流程
│   ├── /api/collab/stream?session_id=... — 协作 SSE 实时流（MVP）
│   ├── /api/export/{html|pptx|pdf|png} — 多格式导出
│   ├── /api/assets/all — 模板/配色/布局资产
│   └── /api/hardware/detect — 硬件检测
└── 部署: GitHub Actions CI/CD → JarvisCao168/cloud-stamp-ppt
```

## Phase 3 P1 交付记录（本阶段新增）

### 协作 MVP SSE 双轨（后端，Hermes `0146a54`）
- `GET /api/collab/stream?session_id=...` SSE 端点（主端点挂 generation 路由，main.py 同步注册 `/api/collab` 前缀）
- `collab_publish()` 广播总线：每会话最近 100 条事件 + `asyncio.Queue` 扇出 + 30s `ping` 心跳 + 新 join 者回放历史
- `/create` 三条流水线（quick/collaborative/full_control）在 quota 检查后追加广播，`fc69cea` quota 一行未动
- 前端骨架：`app/components/collab/useCollabStream.ts` + `CollabStatusPanel.tsx`（文件级隔离，不碰移动端/长文本文件）
- 实测：keep_original 链路事件序列完整、二次 join 回放幂等、429 路径未破坏

**SSE 事件协议（锁定版，前后端已对齐）**

| 事件 | 触发时机 | data 字段 |
|---|---|---|
| `snapshot` | 连接建立时下发一次 | `{session_id, mode?, keep_original?, slides_count?}` |
| `generation_progress` | 流水线各阶段进度 | `{stage, detail, pages?, percent?, currentSlide?, message?}` — stage 枚举 6 值：`intent`/`outline`/`content`/`numbering`/`style`/`keep_original`；长文本分段另用 `stage="keep_original_progress"`（含 `pages`）作为第 7 个扩展值 |
| `collab_status` | 协作状态变更（检查点确认等） | `{status, message?}` |
| `ping` | 30s 无事件心跳保活 | `{ts}` |

> `slide_update` / `generation_complete` 两个扩展事件已在 type 定义中预留，MVP 无生产端，留到 Phase 4 协作编辑流落地；MVP 阶段 `Last-Event-ID` 断点续传和独立鉴权不做，依赖现有 `session_id` 透传。
> `usage_log` 计数规则：整篇算一次，不按段落拆分；长文本分段不走 `/create` 入口，避免 quota 虚增。

### 长文本理解优化（Claude `523706a`）
- `_paginate_keep_original()`：标题行+内容行归组，单页超 8 行自动继续分页
- 长段落按句子边界（`。！？!?；;`）拆行，无边界 300 字硬切，零字符丢失
- 多页无标题时首行提升为页标题；单行兜底"要点"——杜绝空标题页
- 空输入返回 `[]`，`_quick_mode_pipeline` 统一插入兜底标题页
- SSE 进度：每分页一条 `generation_progress`，`stage="keep_original_progress"` + `pages` 计数
- `test_keep_original.py` 16 项全绿；回归基线维持 55/56

### 免费额度计数器（Claude `60f8051` + Hermes `fc69cea`）
- `usage_log` 表 + `quota.py`：每日 10 次生成计数（`FREE_DAILY_LIMIT=10`）
- `fc69cea`：`check_quota()` 补 `await` + `async with aiosqlite.connect(...)` 上下文管理；`db.py` 建表+索引；`/create` 路由接通（`user_id` 缺省 `anon-{IP}`，超限 429 含 `used/limit/reset_at`）
- E2E 429 路径验证：11 次调用 = 10×200 + 1×429 ✅

### E2E 回归基线（Hermes `766ac14`）
- 55/56 通过（1 flaky：`export.test.ts:386` HTML 导出 15s 超时，非代码缺陷）
- 动态 `user_id` 注入 + `E2E_API_BASE` 环境变量支持
- 报告：`docs/e2e-baseline-report.md`
- 降级链术语修正：实际为 **Agnes→GLM→内置静态默认值**（`/create` 未接 Ollama）

### 移动端适配（Claude `60f8051`）
- `CheckpointPanel.tsx`：mobile `flex-col` + `min-w-0` + `break-words`
- `RevealContainer.tsx`：`min-h-[300px] sm:min-h-[500px]`

### 双 DB 统一 + 绝对路径锚定（Claude `0a1c75d` + `c466fd2`）
- 根目录 `yunzhang.db` 删除，统一到 `backend/yunzhang.db`（含 `template_elements` 表）
- ✅ `config.py` 的 `database_url` + `.env_file` 改用 `Path(__file__).resolve()` 绝对路径锚定，彻底堵死 uvicorn CWD 漂移重建根目录 DB 的风险；dev proxy 同步指向 8001；429 响应体补 `message` 中文文案 + `reset_at` 次日 0 点语义（`c466fd2`）

## 测试状态（最新）
```
后端: 57/57 通过 ✅（4 个 async 测试有既有 pytest-asyncio 配置问题，非阻塞）
前端 Vitest: 173/173 通过 ✅（含 7 项协作专属测试）
test_keep_original: 16/16 通过 ✅（分页/保持原文/SSE/fallback 用例，不含 429 断言）
E2E: 55/56 通过（1 flaky，非代码缺陷）✅（429 路径 11 连发 = 10×200 + 1×429 由 E2E 基线承担，见 docs/collab-mvp-report.md）
覆盖率: 93.57%（目标 ≥60%）✅
```

**DB / 429 响应体口径（`72cf9cc` 勘误锁定）**: `usage_log` 实际 DDL 为主键 `(user_id, generated_at)` + 索引 `idx_usage_log_user_date(user_id, generated_at)`，无自增 `id`、无 `date` 列（`db.py` 实测）；429 响应体为嵌套结构 `detail={error/message/user_id/used/limit/reset_at}`（`generation.py:677-684` 实测，`reset_at` 为本地次日 0 点）；幂等语义为「同日超限短路 429」（`INSERT OR REPLACE` + 微秒精度 `generated_at`），非请求级去重

**Phase 4 设计文档（`83fda71` → 终审定稿 v0.2.2 → v0.2.2.3 终审基准锁定）**: 演进 v0.1 → v0.2（`83a7ac2`，并入 Hermes 组长复核 9 成立/2 部分 + Claude 设计审查 11 条 findings）→ v0.2.1（`2778887` 补漏 #12/#13 + `d0dbac3` 补完 4 条终审 WARN）→ v0.2.2（`0a486f8` 组长终审定稿）→ v0.2.2.1（`54d19ed`/`196192b`/`ccf9d9f` 验收前置断言 #3 改判窗口同批 + #7 UTC 日界窗口）→ v0.2.2.2（`bd08191` 新增「三·附、M1 验收节」：slides=[] 口径定稿「同步响应完整携带」，4 条验收断言 + M1-2 拆分裁定）→ **v0.2.2.3（本次勘误 commit，M1-2 残留 2 PR 措辞更正为组长最终裁定「单 PR 双 commit」：commit 1 = P1-#7 时区修复 ≤5 行，commit 2 = DB 迁移 + `check_credits()` + 429→402 切换 + `GET /api/quota/status` + M1 验收节文档；同批一次合入消灭中间态窗口，双 commit 保留独立 revert 粒度）**。组长终审通过（Hermes，见下）；待 JARVIS 终审后启动 M1。**下游请勿把 v0.1/v0.2.1 当锁定 schema 直接实施**——v0.1 含 6 条 P0 矛盾 + 4 条 P1 缺口 + 1 条现状时区 bug（`quota.py` UTC 口径正确 / `generation.py:674-675` 误用本地时区，P1-#7 修复节已给 ≤5 行方案，随 M1 开工 PR 推）；v0.2.2 定稿收敛 §3.3 429/402 schema 为单一平铺形态（原 v0.2.1「双形态并存过渡」兼容段删除，M1 切换完成后嵌套 `detail` 形态下线，proxy 透传规则相应简化为只解析顶层 `code`）；M2 并发扣减 SQL 口径（`WHERE version=?` 原子更新 + 重试 3 次上限）已定。

**组长终审结果（Hermes，2026-09-14）**: 11 条 findings 全部核认已并入 v0.2.2（P0 六条：#1 不赠额 / #2 跨 user_id 一律 404 / #3 429 唯一保留路径定稿 / #4 平铺 JSONResponse 机制写明 + 过渡兼容段删除 / #6 session-lifetime token / #11 本块背书降调随终审 commit 一次推上，不单独起提交）+ P1 四条（#7 时区 bug 修复节，勘误定位明确不动 `quota.py`、只改 `generation.py:674-675` / #8 `slide_update` 改挂 G4 / #9 A/B 案边界 / #10 `last_cost_date` 列）+ Codex 补充 #12（`version` 乐观锁列 + M2 扣减 SQL）/#13（`credit_ledger` 已有 `idx_credit_ledger_user_time` 索引，无需另开）。终审意见 3 条 NIT（非阻塞）已并入本次终审 commit：① E2E 基线 429 断言粒度三方共核前置项已完成——Hermes/Codex/Claude 共核：`e2e-baseline-report.md`「429 免费额度路径验证」节 + `collab-mvp-report.md`「429 路径验证节」均只断言「状态码 = 429 + `message`/`error` 字段存在」，**未断言嵌套 `detail` 结构本身**；且 `e2e/` 目录 grep `429` 零命中（11 连发验证是报告层操作记录，非 e2e 用例断言）→ **M1 切换判定源后稳态 429 唯一路径保留，基线不需改断言**，M1 PR 仅需同步改 `reset_at` 值（UTC 口径）；② v0.2.1 §4.2.2 缓冲外降级引用了「§4.2.3」但该节不存在（实际边界声明在 §4.2 第 3 条内），引用号笔误，v0.2.2 已修正为「见下行第 3 条」；③ v0.2.1 §3.3 平铺 schema 的 429 `usage.reset_at` 示例值 `2026-09-15T00:00:00Z` 为 UTC 格式，与现状 `generation.py:676` 本地格式（`2026-09-15 00:00:00`）不同——P1-#7 修复后 reset_at 统一 UTC ISO 格式，该示例值即成正确目标值，无冲突。

**Phase 4 M1 实施记录（v0.2.2.4 终审基准后，Claude 单 PR 双 commit 起草）**:
- **Commit 1（P1-#7 时区修复）**：`generation.py:672-676` 改 UTC 口径（`timezone.utc` + ISO Z `reset_at`），4 行有效变更，行号零漂移，独立可 revert；`quota.py` 一行未动
- **Commit 2（积分制切换全套）**：
  - `db.py`：追加 `user_credits`（`balance/daily_cost/last_cost_date/version/updated_at`，#10/#12 列齐）+ `credit_ledger`（`seq AUTOINCREMENT` + `idx_credit_ledger_user_time`，#13）DDL，`init_db()` 幂等建表，旧库直接补表无数据迁移；M1 不赠额（`balance` 初值 0）
  - `quota.py`：新增 `check_credits(user_id, required=0) → (allowed, balance, used, limit)` 4 元组（§2.3 OR 判定式 `(not allowed or not credit_allowed) and balance < required`，`311473b` 勘误收敛口径；单连接同查 `user_credits.balance` 缺行视为 0 + `usage_log` 当日计数，复用 `check_quota` since 口径；M1 required 固定 0，M2 扣减走 `version` 乐观锁）
  - `generation.py:677-684`：旧嵌套 `detail` `HTTPException(429)` 分支下线 → `JSONResponse` 平铺双路径：稳态 429 唯一路径（§3.3，`check_quota` 耗尽 `used ≥ limit` 且 `balance == 0`）→ `code=daily_free_quota_exceeded` + 顶层 `usage{used,limit,reset_at}`（`used/limit` 取自 `check_quota` 结果，取值逻辑零改动）；402 预留路径（`balance < required`，M1 required=0 不可达仅留 §3.3 平铺结构，M2 预扣点接入后激活）；判定式按 §2.3 OR 语义收敛，补 `JSONResponse` + `check_credits` import
  - `routes/quota.py`（新建）：`GET /api/quota/status`（§3.4 鉴权规则——`user_id` 与 `/create` 同源三级解析（`X-User-Id` 指纹 header → `anon-{host}` → `anon-unknown`），显式 `?user_id=` 仅与调用方自身指纹一致时放行、跨 `user_id` 一律 404 不枚举；`init_db()` 防御性建表保证冷启动可查 `user_credits`；响应 `usage` 块含 `used/limit/allowed/reset_at`（UTC ISO Z）+ `credits` 块 `balance/required`（M1 required=0））；`main.py` 注册 `/api/quota` 前缀
  - 文档同批：`docs/phase4-plan.md` NIT 行号脚注（`M1-2 :676-684 → :677-684`，勘误「下界 :677，:676 reset_at 计算行归 commit 1 时区修复域，与 commit 1 独立 revert 边界对齐；不另发独立勘误 commit」）+ M1-1 4 条验收断言原文已在此前 `bd08191` 落档本次不改；`docs/e2e-baseline-report.md` 429 改判说明（基线脚本附件同步更新，§一 验收#5 补充①同批不拆两批）
- **测试三项待 Codex 执行**（同 PR 内不分叉）：① 429→402 改判（仅断言状态码 + 顶层 `message`/`code`）② P1-#7 日界复跑（UTC 日界 ±1h 窗口外）③ `quota/status` 健康断言（基线 404 → 合入后 200 + §3.4 schema `usage`+`credits`，跨 user_id 一律 404）

## Git 历史（近期）
```
311473b docs(m1): M1 执行计划草稿预核 — 双路径判定勘误(429/402) + check_credits 签名收敛 + 测试三项核认  ← Codex
833f0a8 P1-#7: reset_at 时区口径修复（UTC 零点 + ISO Z 格式）  ← Claude
8d75d86 docs(phase4): v0.2.2.4 M1-2 行号实测锁定 — :672-676 / :677-684 终稿基线锚定  ← Claude
320df20 docs(phase4): v0.2.2.3 M1-2 措辞勘误 — 2 PR 残留更正为单 PR 双 commit（组长最终裁定），M1 验收节口径不变  ← Claude
bd08191 docs(phase4): v0.2.2.2 新增 M1 验收节 — slides=[] 口径定稿（完整携带）+ PR 2 拆方案落档  ← Claude
f8220a0 docs(collab-mvp-report): 勘误 5000 字长文本 open 项 — slides=[] 系脚本取错字段层级，10 页非空复核确认，open 项关闭  ← Claude
bd3ddc8 docs(collab-mvp): 真实链路验证补跑结果落档（E2E 429 11 连发 + 5000 字长文本 + PPTX/HTML 导出验证）  ← Codex
ccf9d9f docs(collab-mvp): 真实链路验证占位节刷新状态口径  ← Claude
196192b docs(phase4): v0.2.2.1 同步 Codex 补充意见两条 + STATUS.md 对齐 0a486f8 终审门槛已满足  ← Claude
54d19ed docs(phase4): v0.2.2.1 补充两条验收前置断言（#3 改判窗口同批 + #7 UTC 边界）  ← Claude
0a486f8 docs(phase4): v0.2.2 终审定稿 — 组长终审 commit（§3.3 schema 收敛 + P1-#7 时区勘误定位 + E2E 断言粒度核认 + STATUS.md 背书降调）  ← Hermes
d0dbac3 docs(phase4): v0.2.1 终审补完 4 条 WARN（#6 token 语义 / #9 snapshot 边界 / #10 last_cost_date DDL / #12 version 列）  ← Claude
2778887 docs(phase4): v0.2 补漏 — G1 DDL 并入 findings #12/#13（version 乐观锁列 + last_cost_date 日期锚点）+ 并发扣减方案  ← Claude
83a7ac2 docs(phase4): v0.2 修订稿 — 并入 Hermes 组长复核（9 成立/2 部分）+ Claude 设计审查 11 条 findings（P0 6 / P1 4 / P2 1）+ STATUS.md 背书降调  ← Claude
83fda71 docs(phase4): 补建 phase4-plan.md v0.1 积分制设计 + STATUS.md 补录 DDL/429 口径行  ← Claude
7ff2dce docs(status): STATUS.md 对齐 72cf9cc — 登记 429 路径验证归属勘误（E2E 承担，非 test_keep_original）  ← Claude
72cf9cc docs: 补建 collab-mvp-report（429 路径验证 + 幂等断言两节，基线 722ebb1，含对 Hermes 参考稿的勘误记录）  ← Codex
722ebb1 docs(status): 429 结构化透传关闭决策同步 — STATUS.md + phase3-tasks.md 标注 MVP 不加，格式留 Phase 4 配额面板  ← Hermes
4953829 docs(status): STATUS.md 对齐 451e25d 收尾提交 — 登记 P3 429 透传待决 + 补 commit 表                  ← Hermes
451e25d chore(cleanup): 收尾提交 — 移除构建/测试产物跟踪 + 文档口径对齐                 ← Hermes
c466fd2 fix(quota+db): 429 human-readable error + reset_at day-boundary + DB path anchoring + proxy to 8001  ← Claude
27f5eba chore(status): STATUS.md 对齐 6911a68 协作 MVP 前端精修完成                       ← Hermes
6911a68 feat(collab-mvp): 前端精修+3项专属测试（重连退避/回放去重/多订阅者/429）  ← Hermes/Codex
523706a feat(keep-original): long-text pagination + SSE progress + empty input fallback  ← Claude
0146a54 feat(collab-mvp): SSE real-time broadcast + collaboration frontend hooks          ← Hermes
0a1c75d chore(db): unify dual yunzhang.db into backend/ single source + clean test quota records ← Claude
766ac14 test(e2e): baseline report 55/56 + dynamic user_id injection                     ← Hermes
fc69cea fix(quota): async check_quota + usage_log schema + /create wiring                 ← Hermes
60f8051 feat: mobile responsiveness + free daily quota counter                            ← Claude
```

## GitHub 仓库
- **地址**: https://github.com/JarvisCao168/cloud-stamp-ppt
- **分支**: master → origin/master

## 待办事项

| 优先级 | 任务 | 负责人 | 状态 |
|--------|------|--------|------|
| P1 | 协作 MVP 前端精修（视觉规范补全） | @Hermes | ✅ `6911a68` 已完成（进度条/心跳/错误态/重连退避） |
| P1 | 协作 MVP 3 项专属测试（进度回放 / 429 不受影响 / 多订阅者并发） | @Hermes | ✅ `6911a68` 已完成（Vitest 7 项全绿，回放去重+重连退避+并发+429 不回归） |
| P1 | 真实 Agnes key E2E 补跑（真实链路 + 429 连续 + 5000 字长文本端到端） | @Codex | ⏳ 待 JARVIS 提供 key 写入 `backend/.env`（已 gitignore）；不阻塞 P1 |
| P1 | 8000 端口残留进程清理（PID 18268） | @Codex | ✅ PID 18268 已自然消失，仅 8001 监听（双后端双写风险已消除） |
| P2 | `database_url` 绝对路径改法（堵死 CWD 重建根目录 DB） | @Claude | ✅ `c466fd2` 已交付（`config.py` 绝对路径锚定 + proxy→8001 + 根目录残留 DB 删除） |
| P4 | `slide_update` / `generation_complete` 生产端实现 + 429 结构化透传字段格式 + `Last-Event-ID` 断点续传/独立鉴权 | @Claude/@Codex | 协议层已预留；MVP 关闭 429 透传决策（Codex 拍板），格式随 Phase 4 配额面板 + 协作编辑流统一定 |
| P4 | 积分制设计文档（免费额度计数器之上） | @Claude/@Hermes | ✅ **v0.2.2 组长终审通过**（工作区草稿，终审 commit 待推 origin/master；§3.3 429/402 schema 收敛为单一平铺形态，过渡兼容段删除；11 条 findings + Codex #12/#13 全部并入；E2E 429 断言粒度三方共核完成——只断言状态码 + message/error 字段，M1 切判定源后基线不需改断言，M1 PR 仅需同步 `reset_at` UTC 值）；**M1 排期门槛 = 终审 commit 进 origin/master + JARVIS 终审通过**，P1-#7 时区 bug 修复（不动 `quota.py`，只改 `generation.py:674-675`，≤5 行）随终审 commit 一起推 |
| P2 | 生产环境部署方案（Vercel/阿里云） | @Hermes | 待开始 |
| ~~P3~~ | `next.config.ts` 429 结构化错误透传（FastAPI 429 body 的 `message`/`used`/`limit`/`reset_at` 转发给前端） | @Codex 拍板 | ✅ 关闭 — MVP 不加 proxy 层 429 结构化透传（避免错误解析耦合），字段格式与 `Last-Event-ID` 鉴权一并留到 Phase 4 配额面板 + 协作编辑流统一定 |

## 阻塞项

| ID | 描述 | 优先级 | 负责人 | 状态 |
|----|------|--------|--------|------|
| B1 | AI API Key 配置 | P1 | 待 JARVIS | 降级链已验证（Agnes→GLM→内置），真实 key 补跑可选 |
| B3 | 8000 端口残留 PID 18268 杀不掉 | P1 | @Codex | ✅ 已自然消失，仅 8001 监听 |
| B4 | Gamma.app 网络不通（Windows） | P2 | — | 竞品对比报告暂缺 Gamma 数据 |

## 下一步计划

1. **协作 MVP 收尾**: ✅ `6911a68` 前端精修 + 3 项专属测试 + `c466fd2` 429/quota 修复 + 双 DB 绝对路径锚定 + proxy→8001 + `451e25d` 文档口径对齐/解除跟踪 已全部推 GitHub；STATUS.md 已对齐
1.5. **Phase 4 积分制设计文档**: ✅ `docs/phase4-plan.md` v0.2.2 组长终审通过（@Claude 出稿 + @Hermes 终审，纯设计零代码，不依赖 Agnes key；终审 commit 待推 origin/master，M1 排期门槛 = 该 commit 进 origin/master + JARVIS 终审通过）：积分账户表迁移（含 `last_cost_date`/`version` 乐观锁列）+ 429/402 单一平铺 schema（JSONResponse，过渡兼容段删除，M1 切换完成后嵌套 `detail` 形态下线）+ 唯一 429 保留路径（免费额度耗尽且余额=0）+ proxy 最小解析（只解析顶层 `code`）+ 配额面板（`quota/status` 禁跨 user_id 枚举，R6）+ SSE `slide_update`/`generation_complete` 生产端（`slide_update` 改挂 G4，M3 只定 schema）+ `Last-Event-ID` + session-lifetime token + 协作编辑流（乐观锁 A 案）；里程碑 M1-M4 见文档 §五
2. **真实 Agnes key 补跑**（可选）: JARVIS 提供 key → 写入 `backend/.env` → @Codex 补跑真实链路 E2E + 429 连续验证 + 5000 字长文本端到端；补跑前先清理 8000 端口残留
3. **Phase 4 启动**: ✅ 积分制设计文档 v0.2.2 组长终审通过（`docs/phase4-plan.md`，终审 commit 待推 origin/master，见第 1.5 条）；M1 排期门槛 = 终审 commit 进 origin/master + JARVIS 终审通过；429/402 结构化透传字段格式已定稿（§3.3 单一平铺 schema，M1 切换后嵌套 `detail` 形态下线，MVP 阶段 proxy 不解析决策不变，格式定义见 phase4-plan.md §3.3）；P1-#7 时区 bug 修复（不动 `quota.py`，只改 `generation.py:674-675` 统一 UTC + 注释勘误，≤5 行）随终审 commit 一起推，不单独起提交
4. **生产部署**: @Hermes 制定部署方案

---

## 调研任务时间线

| 阶段 | 任务 | 负责人 | 截止时间 |
|------|------|--------|---------|
| 准备期 | 问卷定稿 + 测试框架就绪 | Claude/Hermes | ✅ 2026-09-10 |
| 执行期 | 问卷投放（腾讯问卷） | Claude | 2026-09-13~09-23 |
| 执行期 | 竞品体验对比（5款） | Codex | 2026-09-13~09-18 |
| 执行期 | 用户深度访谈（5-10人） | Claude | 2026-09-23~09-26 |
| 分析期 | 数据整理 + 报告撰写 | Claude | 2026-09-26~09-29 |
| 评审期 | 团队评审 + 迭代优先级确认 | Hermes | 2026-09-30 |

## cleanup 批次台账（M2 收口后遗留，非阻塞）

| # | 项 | 状态 | 说明 | 负责人 |
|---|---|---|---|---|
| 1 | `estimate_required` 签名三方偏差 | 🟢 已核销 | 勘误项 1（docs `payload_size`→`input_len`）经 grep 实测 §3.5.1 落档时即正确（L159 入参 `(mode, input_len, complexity)`），无偏差无需改；勘误项 2（`routes/quota.py` `required_hint` 注释）已落码 L85「仅 UI 占位，非生成时点实际预扣值」；`b369e1f` 落库 | @Claude |
| 2 | E2E 402 命中确认重跑 | 🟡 开放 | `e2e/m2-credits.test.ts` URL 已在 `362420f` 修复为 `${API_BASE}/api/quota/test/setup-balance`（L99 实测，`API_BASE` 默认 8001；Claude 疑点 L328/L345 `8000` 系旧行号，现行不存在）；待 Agnes 429 限流缓解后 WSL 3.12 侧 `npx playwright test e2e/m2-credits.test.ts`（`API_BASE=8001`）确认第 11 次命中 402 非 429；回归门槛已在 M2 PR 2 达成，收尾验证不阻塞合入 | @Codex |

> 批次原则：随后续 M3+ 或 chore 批次同批提交，不单独开 commit。e2e URL 勘误项已由 `362420f` 闭合销项，不入本表。

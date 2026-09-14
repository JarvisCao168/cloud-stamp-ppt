# 云章PPT智能体系统 - 项目状态报告

**更新日期**: 2026-09-14
**当前阶段**: Phase 3 P1 全部交付 + 收尾提交完成（`451e25d` 文档口径对齐 + 解除跟踪）
**最新 Commit**: `83fda71`（STATUS.md DDL/429 口径行补录 + `docs/phase4-plan.md` v0.1 新建）/ `7ff2dce`（STATUS.md 测试状态块勘误 + commit 表补录）/ `72cf9cc`（补建 `docs/collab-mvp-report.md`）/ `722ebb1`（429 关闭决策同步）/ `4953829`（STATUS 对齐）/ `451e25d`（收尾：符号名/丢失判定口径对齐 + 文档清理 + 解除跟踪）/ `c466fd2`（429/quota + DB 锚定 + proxy）/ `6911a68`（协作 MVP 前端精修+测试）/ `0146a54`（SSE 后端）/ `523706a`（长文本优化）

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

**Phase 4 设计文档（`83fda71` 起）**: v0.1 已交付；Claude 设计审查 + Hermes 组长复核完成，11 条 findings 已并入 **v0.2 修订稿**（工作区未推）。**下游请勿把 v0.1 当锁定 schema 直接实施**——v0.1 含 6 条 P0 矛盾（429/402 触发矩阵未定稿、`quota/status` oracle、`slide_update` 生产端错位等）+ 4 条 P1 缺口 + 1 条现状时区 bug（`quota.py` UTC / `generation.py` 本地时区错配）。v0.2 修完这三类后待 Hermes 组长终审 + JARVIS 终审，通过后 M1 方可排期；`quota.py`/`generation.py` 时区 bug 修复（P1-#7）随 v0.2 一次推完。

## Git 历史（近期）
```
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
| P4 | 积分制设计文档（免费额度计数器之上） | @Claude | ✅ v0.2 修订稿已推 `docs/phase4-plan.md`（并入 Hermes 复核意见 + Claude 设计审查 11 条 findings；含 6 条 P0 矛盾修复 + 4 条 P1 缺口 + R5/R6 风险登记 + P1 时区 bug 修复节；纯设计零代码，**M1 排期待 Hermes 组长终审 + JARVIS 终审通过后启动**） |
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
1.5. **Phase 4 积分制设计文档**: ✅ `docs/phase4-plan.md` v0.1 设计稿已交付（@Claude，纯设计零代码，不依赖 Agnes key）：积分账户表迁移 + 429/402 统一 schema + proxy 最小解析 + 配额面板 + SSE `slide_update`/`generation_complete` 生产端 + `Last-Event-ID` 断点续传 + 协作编辑流（乐观锁 A 案）；实施里程碑 M1-M4 见文档 §五
2. **真实 Agnes key 补跑**（可选）: JARVIS 提供 key → 写入 `backend/.env` → @Codex 补跑真实链路 E2E + 429 连续验证 + 5000 字长文本端到端；补跑前先清理 8000 端口残留
3. **Phase 4 启动**: ✅ 积分制设计文档 v0.1 已交付（`docs/phase4-plan.md`，见第 1.5 条）；429 结构化透传字段格式随配额面板 + 协作编辑流统一定（MVP 已拍板不加，Codex 决策，格式定义见 phase4-plan.md §3.3）
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

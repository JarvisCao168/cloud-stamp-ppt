# M3 · B 案 SSE 增量事件协议草案（v0.2 定稿）

**日期**: 2026-09-16（v0.1 草案）｜2026-09-16（v0.2 定稿，@Hermes 终审核对后修正落稿，同 commit 随组落库）
**作者**: Claude（协议侧，按 M3 启动令 A+B 裁定第 3 步交付）
**状态**: 定稿 v0.2（M3 交付物，零代码变更；B 落码在 M4；v0.2 已按 @Hermes 终审核对意见修正 6 处行号引用，修正全量登记见 §八）
**裁定记录**: M3 范围裁定 **A+B**（@JARVIS 2026-09-16 下达，@Hermes 启动令 4 步序列第 3 步）
**基座**: `098cde9`（不动）｜工作树 HEAD `bcd202c`（M2 全链，零分叉）｜交付性质：**纯文档**，M3 内不改任何生产代码

> 本草案为 B 线（SSE 增量事件协议定稿）唯一设计基准，随 M3 收口 commit 与 `docs/phase4-plan.md` v0.2.4 增补登记一并落库。M4 协作编辑流按本稿定稿协议直接落码，不再追加协议设计轮次。
>
> **文件路径注记**：本稿独立文件为 `docs/m3-b-sse-incremental-events-draft.md`；并入 `docs/phase4-plan.md` 的章节编号为 **§4·B**（v0.2.4 新增），与 §4.1-4.4 既有锁定内容零重叠。

---

## 一、范围与命名空间

### 1.1 设计目标

B 案为协作 MVP 通知层（现状 `GET /api/collab/stream` 4 基础事件 + 2 预留事件，`STATUS.md` SSE 事件协议表锁定版）之上补齐 **viewer 在场状态（presence）增量事件**，使 M4 协作编辑流在协议层即具备：

1. 多人同会话下「谁在场」的可观测性（加入 / 离开实时通知）；
2. 新观察者 join 时的在场状态收敛（全量快照 + 增量事件双通道）；
3. 与既有事件 schema 的零冲突扩展（既有 4 事件 + 2 预留事件全部冻结）。

### 1.2 独立 `event` 命名空间（组长终审裁定 #2 锁定口径）

B 案 3 个新增事件使用**独立 `event` 命名空间**，不复用 `generation_progress.stage` 链路、不复用既有 4 事件名：

| 事件 | 触发时机 | data schema（本稿定稿） |
|------|---------|------------------------|
| `viewer_joined` | 任一观察者建立 SSE 连接成功（join 回放完成后首帧下发） | `{session_id, viewer_id, ts, viewers_total}` |
| `viewer_left` | 观察者连接关闭 / 断线 30s 超时无重连（以总线侧 `asyncio.Queue` 扇出关闭事件为准） | `{session_id, viewer_id, ts, viewers_total}` |
| `presence_snapshot` | 新观察者 join 时的**全量在场快照**（与该观察者 join 回放首帧同批下发，先于其收到后续增量事件） | `{session_id, viewers: [{viewer_id, last_seen_ts}], ts}` |

**命名空间隔离规则**（M4 落码验收项）：

- `event:` 行只新增上述 3 个值；`generation_progress` 的 `stage` 枚举（6 锁定值 + `keep_original_progress` 扩展值）**零新增零改动**；
- 3 个新事件的 `data` 字段与既有事件 schema **零重叠命名冲突**（`viewer_id` 取自 SSE 调用方 `user_id` 指纹，与 `session_id` 同会话维度）；
- 既有 4 事件（`snapshot` / `generation_progress` / `collab_status` / `ping`）与 2 预留事件（`slide_update` / `generation_complete`，§4.1 生产端挂 M4/G4）的 schema **冻结**——B 案不改动任何既有事件字段（「只增不删不改义」规则的全局适用性见 §二）。

> **`viewer_id` 口径备案**：MVP 阶段无登录体系（§五 R3/R5），`viewer_id` = 该连接对应的 `user_id` 指纹（`/api/collab/stream` 调用方 `X-User-Id` header → `anon-{IP}` → `anon-unknown` 三级解析链，与 `/create` 的 `quota_user_id` 同源）。多标签页同指纹 = 同一 `viewer_id`（MVP 接受此粒度，登录体系立项后升级为 session-bound 身份锚点，与 R5 同批，不在 M3 范围）。

## 二、payload 规则

**「只增不删不改义」全局规则（B 线所有事件，M4 落码验收基线）**：

1. **新增事件**（B 案 3 事件）：M4 内后续扩展只允许**新增字段**，不允许删除已发版字段、不允许修改已发版字段语义（类型 / 取值枚举 / 缺省行为）；
2. **既有事件 schema 冻结**：M4 内对 4 基础 + 2 预留事件做字段增补时，遵守同一规则（`generation_progress` 新增 `percent` / `currentSlide` 等字段即先例，`useCollabStream.ts:32-36` 已实现）；
3. **客户端兼容性口径（锁定）**：
   - 未知字段：**忽略**（客户端对 `data` 中未声明字段一律不消费、不报错）；
   - 缺失新字段：**降级为「未上报」而非报错**（如 `viewers_total` 缺失 → 面板显示在场数未知，不阻塞渲染；B 案 3 事件在旧客户端上表现为「未知 `event` 名」→ EventSource 不触发监听器，天然静默忽略，M4 升级前无回归面）；
4. 本规则同步并入 §4.1 `slide_update` / `generation_complete` 生产端接入（M4）——M4 落码时 2 预留事件的 payload 扩展同样受「只增不删不改义」约束。

## 三、分发点清单（M4 落码验收项，逐条列明）

**路径注记**：后端路径全量使用完整路径（HEAD `bcd202c` 实测）。`generation.py` 全路径 = `backend/app/api/routes/generation.py`；`useCollabStream.ts` 全路径 = `app/components/collab/useCollabStream.ts`。

现状锚点：`app/components/collab/useCollabStream.ts`（协作 MVP 前端骨架，文件级隔离约定）。

| # | 位置 | M4 改动 | 说明 |
|---|------|---------|------|
| D1 | `app/components/collab/useCollabStream.ts:23-39` `CollabEvent` 联合类型 | **新增 3 个成员**：`{type:"viewer_joined", data:{session_id, viewer_id, ts, viewers_total}}` / `{type:"viewer_left", data:{session_id, viewer_id, ts, viewers_total}}` / `{type:"presence_snapshot", data:{session_id, viewers, ts}}` | 既有 4 成员零改动（schema 冻结）；新成员类型即本稿 §一 schema |
| D2 | `app/components/collab/useCollabStream.ts:41-50` `CollabStreamState` 接口 | **新增 2 字段**：`viewersTotal: number \| null`（最近一次 `viewer_joined`/`viewer_left`/`presence_snapshot` 的上报值，全缺失 = `null` → 面板「未上报」降级）、`lastPresenceTs: number \| null` | 既有字段零改动 |
| D3 | `app/components/collab/useCollabStream.ts:111-136` `onEvent` 分发闭包 | **新增 3 个分发分支**（`type==="viewer_joined"` / `"viewer_left"` / `"presence_snapshot"`），各分支仅写 `viewersTotal` / `lastPresenceTs`，**不复用** `processedProgressRef` 去重指纹（该指纹仅服务 `generation_progress` 回放去重，presence 增量事件天然按 viewer 维度幂等） | 既有 `generation_progress` / `collab_status` / `ping` 分支零改动 |
| D4 | `app/components/collab/useCollabStream.ts:138-141` `es.addEventListener` 注册块 | **新增 3 行监听器注册**：`es.addEventListener("viewer_joined", onEvent("viewer_joined"))` 等 | 既有 4 行注册零改动 |
| D5 | `app/components/collab/useCollabStream.ts:9` 头注释协议表 | 同步追加 3 事件行（文档行，与 STATUS.md SSE 事件协议表同批更新） | 纯注释，不影响运行时 |

**后端分发点（M4 生产端接入位置，本稿仅登记不落码）**：

| # | 位置 | 说明 |
|---|------|------|
| S1 | `backend/app/api/routes/generation.py:53-58` `collab_publish()` 广播总线（HEAD `bcd202c` 实测，v0.1 稿误引 `:45-53` 已修正） | 新增 `viewer_joined` / `viewer_left` / `presence_snapshot` 3 类事件写入 `_collab_event_log`（容量 100 条不变）；join 回放路径（`backend/app/api/routes/generation.py:93-95`，v0.1 稿误引 `:94-102` 已修正）天然覆盖 `presence_snapshot` 全量下发，**无需新增回放通道** |
| S2 | `backend/app/api/routes/generation.py:89-113` `event_stream()` 订阅端 | 新增 per-connection 连接簿记（连接建立 → `collab_publish(viewer_joined)`；`Queue` 关闭 / 30s 心跳超时 → `collab_publish(viewer_left)`；新 join 完成回放后首帧 → `collab_publish(presence_snapshot)`） |

> **验收基线**：M4 落码 PR 的 diff 面必须与 D1-D5 + S1-S2 清单一一对应；清单外文件出现 B 相关 diff 即终审打回（与三条收口硬约束同等效力，见 §五 引用）。

## 四、预扣点章节（整篇计一次口径）

**直接引用组长终审裁定原文（B 线最小形态预扣点硬性设计约束，本稿不单独论证）**：

> 协作会话预扣次数口径：维持 M2 裁定——**按整篇计一次，不逐观察者拆分**。

**接入设计（M4 落码基准，M3 本稿仅锁定位置与口径，不改代码）**：

1. **预扣触发单点**：预扣由**生成方（编辑者）单点触发**，即 `/create` 路由（`backend/app/api/routes/generation.py:685` `estimate_required(request.mode, ...)` 调用点，HEAD `bcd202c` 实测）；**观察者不触发任何预扣路径**——观察者连接 SSE 流不产生计费点（本稿 3 个 presence 事件本身 `required=0`，不入 `estimate_required` 折算域）。
2. **分桶路径实码承载**：`estimate_required` 传 `mode="collaborative"` → 落入既有分桶路径 `if mode in ("collaborative", "full_control"): return 0`（`backend/app/core/quota.py:39-40` 实测），**无需新增 `mode` 枚举值**；单测 9 组之 #6（`test_quota_m2.py:99` `estimate_required("collaborative", 5000, "auto")` → 0）即「整篇计一次」约束的实码承载，M4 协作流 checkpoint 动作计费如需另开，走 §3.5.1 路由表末行「M4 协作流 checkpoint 动作计费单独立项」，不在 B 线范围。
3. **`debit_credits` 零改动**：B 线不新增扣减调用点、不改 `debit_credits`（`backend/app/core/quota.py:57-107` 乐观锁结构，3 次重试 + 50ms 退避 + `(False, -2)` 返回）任何一行——M3 硬约束 ④⑤⑥（见 §五）在 M4 落码时继续生效。
4. **`usage_log` 计数同源**：协作会话每次 `/create` 生成后由 `record_usage`（`backend/app/core/quota.py:296-307`，`backend/app/api/routes/generation.py:751` 同步调用点）记一行，当日计数走 `COUNT(*) WHERE user_id=? AND generated_at >= _today_start_utc()` 口径——实码三处（`check_quota` `backend/app/core/quota.py:262-280` 内 `:273` / `check_credits` `:214-259` 内 `:248` / `get_quota_status_sync` `:195-211` 内 `:205`，口径本身三处统一无误）；`since = _today_start_utc()` 定义 = `quota.py:17`；**注：`estimate_required`（`quota.py:23-49`）本身无计数行，不属「三处」之列**（v0.1 稿将 `:273` 误标 `estimate_required` 已勘误，全量登记见 §八）；勘误行号备案 @Hermes 2026-09-16，见 `docs/phase4-plan.md` v0.2.4 勘误落档——与「整篇计一次」同源闭合，B 线不引入第二条计数通道。

## 五、429 / 402 路径分离标注 + 基座声明 + 收口硬约束

### 5.1 429 / 402 路径分离（B 线风险清单须标注，@Codex 合并排期并入）

- **429 分支属 `check_quota` 免费额度耗尽路径**（`backend/app/core/quota.py:262` 函数起点实测）：稳态唯一触发条件 = `used ≥ limit`（当日免费额度耗尽）**且** `balance = 0`，`code=daily_free_quota_exceeded`（§3.3 定稿 schema，`phase4-plan.md` §3.5.4 四态表 429 行）；
- **402 属 `check_credits` 积分余额不足路径**（`backend/app/core/quota.py:214` 函数起点实测）：`used ≥ limit` 且 `0 ≤ balance < required`，`code=insufficient_credits`；503 属 `debit_credits` 版本冲突 3 次（`(False, -2)`）；
- B 线 presence 事件（`required=0`，不入计费折算域）**不经 429/402 拦截域**——M4 落码若观察到 presence 事件关联 4xx/429 响应，按 bug 路径排查（定位是否误入 `/create` 计费域），不回改协议；
- 两条路径的响应 schema 平铺顶层 `code` 形态（§3.3 定稿）M4 内零改动。

### 5.2 基座声明

**`098cde9` 不动**——本草案及 M3 全部交付物（含 `docs/phase4-plan.md` v0.2.4 增补）为纯文档 + 复核报告，M3 内生产代码（`quota.py` / `db.py` / `config.py` / `generation.py` / `useCollabStream.ts`）**零变更**；B 案落码在 M4（分发点清单 §三 + 生产端 S1/S2 为 M4 落码基准）。

### 5.3 三条收口硬约束（M3 验收项，触碰即打回）

1. `usage_log` 复合主键 `(user_id, generated_at)`（`backend/app/db.py:55-61`，`:59` 复合主键 + `:61` 索引 `idx_usage_log_user_date` 保留 git 跟踪）；
2. `config.py` 绝对路径锚定（完整路径勘误：`backend/app/core/config.py`（`:12` `_PROJECT_ROOT` / `:15` `_DB_PATH` / `:18-27` `_anchor_db_url` / `:75-76` 收尾锚定，HEAD `bcd202c` 实测），非台账历史措辞的 `backend/app/config.py`）；
3. NIT 拦截式判定式（`backend/app/api/routes/generation.py:688` 注释 + `backend/app/core/quota.py:227` 落码说明，§3.5.3 定稿版）。

> 另 M3 启动令追加硬约束 ④ `backend/app/core/quota.py:23` `estimate_required` 签名零改动 / ⑤ `backend/app/core/quota.py:57-107` `debit_credits` 乐观锁结构零改动 / ⑥ `record_usage`（`backend/app/core/quota.py:296-307`）`INSERT OR REPLACE` 语句不改动 / ⑦ 基座 `098cde9` 不动——本稿 §三验收基线对 7 条全量收录。

## 六、M4 衔接（落码前复核项，防二次三方对齐）

| 复核项 | M4 落码时动作 |
|--------|--------------|
| `slide_update` / `generation_complete` 生产端（§4.1） | 按「只增不删不改义」§二 规则 4 约束 payload 扩展；生产端挂 G4 WebSocket 编辑路由（§4.1 P1-#8 修订），B 案 3 事件与 2 预留事件在 `event:` 命名空间内共存无冲突（§一 1.2 隔离规则） |
| 断点续传 | B 案 3 事件为增量通知帧（非持久帧），M4 若同步落地 §4.2 `event_id` 断点续传，presence 事件**可入回放缓冲**（`_collab_event_log` 容量 100 条内）但**不参与去重指纹升级**（§三 D3 说明）；进度帧可回放边界（§4.2 A/B 案）拍板不受 B 线影响 |
| 单测 | `__tests__/collabStream.test.ts` 扩 3 项（viewer_joined/left 更新 `viewersTotal`、presence_snapshot 全量收敛、未知事件名静默忽略回归面 0）——与 §4.4 既有 4 项扩展同 PR |

## 七、文档登记

本稿内容并入 `docs/phase4-plan.md` **§4·B（v0.2.4 新增）**，随 M3 收口 commit 落库；§4.1-4.4 既有锁定内容（`slide_update`/`generation_complete` schema、`Last-Event-ID`、`useCollabStream.ts` 接口、M4 衔接项）零改动。

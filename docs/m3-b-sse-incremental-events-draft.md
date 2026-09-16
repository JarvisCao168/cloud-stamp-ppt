# M3 · B 案 SSE 增量事件协议草案（v0.4 落改入档，M4 启动序列第 1 项）

**日期**: 2026-09-16（v0.1 草案）｜2026-09-16（v0.2 定稿，@Hermes 终审核对后修正落稿，同 commit 随组落库）｜2026-09-16（v0.3，@Codex M3 实码核认报告复核后落改，同 commit 随组落库）｜2026-09-16（v0.3 行号回滚，@Hermes M3 终审裁定：§四.4 计数口径行号 `:206/:249/:274` 系参数行误引，回滚为 SQL 字面量行口径 `:205/:248/:273`）｜2026-09-16（v0.3 强化项落改，@Hermes 终审裁定 ⑤：§5.1 429/402 判定函数归属写死——429 属 `check_quota` 免费额度耗尽路径 / 402 属 `check_credits` 积分余额不足路径，判定互斥零交叉，M4 跨归属改动即 PR 打回）｜2026-09-16（v0.4 落改入档，@Hermes M4 终审裁定 ①③④⑤：① `viewer_joined` 载荷补 `user_id` + BOM 登记；② `presence_snapshot` 首帧维持 v0.3 零改动，§九 勘误行登记；③ 客户端降级强化：缺失 `user_id` → 渲染「未上报」，禁止默认 `1`；④ STATUS.md BOM 口径行同步登记进 §八；⑤ 429/402 分离标注维持现状，§九 勘误行登记——纯文档，零代码变更，随 M4 启动序列第 1 项入 commit）
**作者**: Claude（协议侧，按 M3 启动令 A+B 裁定第 3 步交付）
**状态**: v0.4 落改入档（M4 启动序列第 1 项，纯文档零代码变更；v0.4 = @Hermes M4 终审裁定 ①③④⑤ 落改——① `viewer_joined` 载荷补 `user_id`（`{session_id, viewer_id, user_id, ts, viewers_total}`）+ BOM 登记；② `presence_snapshot` 首帧设计维持 v0.3 零改动；③ 客户端降级逻辑强化：缺失 `user_id` → 面板渲染「未上报」，禁止默认 `1`；④ STATUS.md BOM 口径行（随 `a2134ef` 入库）同步登记进 §八 修正登记表；⑤ 429/402 分离标注维持现状，§九 勘误行登记；v0.3 定稿交付物基准（v0.2 已按 @Hermes 终审核对意见修正 6 处行号引用（§八），v0.3 已按 @Codex M3 实码核认报告（2026-09-16）复核落改 3 处：§四.4 当日计数口径三处 COUNT 行号回滚为 `:205/:248/:273`（SQL 字符串字面量行口径，终审裁定见 §九 注 1；v0.3 一度误改 `:206/:249/:274` 系参数行误引，已回滚作废），§四.1「调用点」措辞勘误为「函数定义在 `quota.py:23`、调用点 `generation.py:685`」，§四.2 单测锚点 `:99` 勘误为 `:99-100`（补 `full_control` 同路径双行验证点）；v0.3 强化项（@Hermes 终审裁定 ⑤）：§5.1 判定函数归属写死（429 属 `check_quota` / 402 属 `check_credits`，M4 跨归属改动即 PR 打回，§九 注 4 落库））
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
| `viewer_joined` | 任一观察者建立 SSE 连接成功（join 回放完成后首帧下发） | `{session_id, viewer_id, user_id, ts, viewers_total}`（v0.4 ①：载荷补 `user_id` 字段——MVP 阶段 `viewer_id` 与 `user_id` 同源（同指纹三级解析链），协议侧双发以兼容登录体系立项后的 session-bound 身份锚点升级；BOM 登记见 §八 7） |
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
   - 缺失新字段：**降级为「未上报」而非报错**（如 `viewers_total` 缺失 → 面板显示在场数未知，不阻塞渲染；B 案 3 事件在旧客户端上表现为「未知 `event` 名」→ EventSource 不触发监听器，天然静默忽略，M4 升级前无回归面）。**v0.4 ③ 强化**：`user_id` 缺失 → 面板渲染「未上报」（同 `viewers_total` 降级路径），**禁止默认渲染 `1`**（在场数语义 = 实测上报值或「未上报」，不得由客户端推断缺省值）；
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

1. **预扣触发单点**：预扣由**生成方（编辑者）单点触发**，即 `/create` 路由（`backend/app/api/routes/generation.py:685` `estimate_required(request.mode, len(request.user_input or ""), complexity)` **调用点**——函数定义在 `backend/app/core/quota.py:23`，此处系 v0.2 起误写「调用点」指向定义处、v0.3 勘误归位；HEAD `bcd202c` 实测）；**观察者不触发任何预扣路径**——观察者连接 SSE 流不产生计费点（本稿 3 个 presence 事件本身 `required=0`，不入 `estimate_required` 折算域）。
2. **分桶路径实码承载**：`estimate_required` 传 `mode="collaborative"` → 落入既有分桶路径 `if mode in ("collaborative", "full_control"): return 0`（`backend/app/core/quota.py:39-40` 实测），**无需新增 `mode` 枚举值**；单测 9 组之 #6（`test_quota_m2.py:99-100` `estimate_required("collaborative", 5000, "auto")` → 0 + `:100` `full_control` 同落 0，v0.3 按 HEAD `bcd202c` 实测补双行锚点）即「整篇计一次」约束的实码承载，M4 协作流 checkpoint 动作计费如需另开，走 §3.5.1 路由表末行「M4 协作流 checkpoint 动作计费单独立项」，不在 B 线范围。**M5 docs 勘误注记**：`estimate_required`（`quota.py:23-49`）对 `collaborative`/`full_control` 返回 0 系设计意图一致（checkpoint 暂停态不计费），402 对 checkpoint 暂停态结构性不可达（`required=0` → `0 < balance < 0` 恒假），非 B1 预扣语义矛盾；该设计问题属 M5+ 范畴，M4 行为冻结不改动。
3. **`debit_credits` 零改动**：B 线不新增扣减调用点、不改 `debit_credits`（`backend/app/core/quota.py:57-107` 乐观锁结构，3 次重试 + 50ms 退避 + `(False, -2)` 返回）任何一行——M3 硬约束 ④⑤⑥（见 §五）在 M4 落码时继续生效。
4. **`usage_log` 计数同源**：协作会话每次 `/create` 生成后由 `record_usage`（`backend/app/core/quota.py:316-327`（生产版 `INSERT OR REPLACE`；`record_usage_sync` = `:303-313`（测试用同步版）），`backend/app/api/routes/generation.py:751` 同步调用点）记一行，当日计数走 `COUNT(*) WHERE user_id=? AND generated_at >= _today_start_utc()` 口径——实码三处（`check_quota` `backend/app/core/quota.py:239`（429 双锚注释注记，B1 `bdea9bd` +20 行后现行值；`:262` def 行 / `:219` `d56b8ae` 中间值均作废仅作版本对照）函数起 内 `:273` `COUNT(*)` / `check_credits` `:234`（def 现行值；`:214` 为旧值，作废仅作版本对照）函数起 内 `:248` / `get_quota_status_sync` `:215`（def 现行值；`:195` 为旧值，作废仅作版本对照）函数起 内 `:205`；**行号终审裁定（@Hermes 2026-09-16 复审）取 SQL 字符串字面量行口径：`:205/:248/:273`；@Codex 核认报告引用的 `:206/:249/:274` 系参数行（`user_id, since`）误引，v0.3 据此落改已回滚作废，全量登记见 §九 注 1**；口径本身三处统一无误，`since = _today_start_utc()` 定义 = `quota.py:17`）；**注：`estimate_required`（`quota.py:23-49`）本身无计数行，不属「三处」之列**（v0.1 稿将 `:273` 误标 `estimate_required` 已勘误，全量登记见 §八）；勘误行号备案 @Hermes 2026-09-16，见 `docs/phase4-plan.md` v0.2.4 勘误落档——与「整篇计一次」同源闭合，B 线不引入第二条计数通道。

## 五、429 / 402 路径分离标注 + 基座声明 + 收口硬约束

### 5.1 429 / 402 路径分离（B 线风险清单须标注，@Codex 合并排期并入）

- **429 分支属 `check_quota` 免费额度耗尽路径**（`backend/app/core/quota.py:239`（429 双锚注释注记，B1 `bdea9bd` +20 行后现行值；`:262` def 行旧值 / `:219` `d56b8ae` 中间值均作废仅作版本对照）——`daily_free_quota_exceeded` 于 `check_quota` 耗尽分支落码；`:219` 为 `d56b8ae` 勘误中间值，仅作版本对照）：稳态唯一触发条件 = `used ≥ limit`（当日免费额度耗尽）**且** `balance = 0`，`code=daily_free_quota_exceeded`（§3.3 定稿 schema，`phase4-plan.md` §3.5.4 四态表 429 行）；
- **402 属 `check_credits` 积分余额不足路径**（`backend/app/core/quota.py:234`（def 现行值；`:214` 为旧值，作废仅作版本对照））：`used ≥ limit` 且 `0 ≤ balance < required`，`code=insufficient_credits`；503 属 `debit_credits` 版本冲突 3 次（`(False, -2)`）；
- B 线 presence 事件（`required=0`，不入计费折算域）**不经 429/402 拦截域**——M4 落码若观察到 presence 事件关联 4xx/429 响应，按 bug 路径排查（定位是否误入 `/create` 计费域），不回改协议；
- 两条路径的响应 schema 平铺顶层 `code` 形态（§3.3 定稿）M4 内零改动；
- **判定函数归属写死（@Hermes 终审裁定 ⑤，随 M3 收口 commit 强化标注落库）**：429 协议侧分支属 `check_quota` 免费额度耗尽路径（code=`daily_free_quota_exceeded`，实码行 = `generation.py:768`（429 分支体 `:761-772` 内））；402 协议侧分支属 `check_credits` 积分余额不足路径（code=`insufficient_credits`，实码行 = `generation.py:778`（402 分支体 `:776-782` 内））；二者判定互斥零交叉（429 = `balance == 0`，402 = `0 < balance < required`）。**M4 落码时若误改 `generation.py:761-772`（429 分支）或 `:776-782`（402 分支）任一行为跨判定函数归属改动（如将 `check_credits` 判定逻辑挪入 429 分支或反之），PR 打回。** 旧引 `:690-701` / `:705-711` / `:262` / `:214` 随 `2a7a5bd` 偏移作废，勘误登记见 §九-补。

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

本稿内容并入 `docs/phase4-plan.md` **§4·B（v0.2.4 新增）**，随 M3 收口 commit 落库；§4.1-4.4 既有锁定内容（`slide_update`/`generation_complete` schema、`Last-Event-ID`、`app/components/collab/useCollabStream.ts` 接口、M4 衔接项）零改动。

## 八、v0.2 修正登记（@Hermes 2026-09-16 终审核对意见，本稿 v0.1 → v0.2 逐条落改）

| # | v0.1 位置 | v0.1 原文 | 实码核验结果（HEAD `bcd202c`） | v0.2 落改 |
|---|-----------|----------|-------------------------------|-----------|
| 1 | §四.4 | `quota.py:205/:248/:273`「三处统一」——其中 `:273` 标作 `estimate_required` | `estimate_required`（`quota.py:23-49`）**无计数行**；`:273` 实为 `check_quota`（函数 `:262-280`）内 `COUNT(*)` 语句；三处 = `:205`（`get_quota_status_sync`）/ `:248`（`check_credits`）/ `:273`（`check_quota`），口径本身三处统一无误 | §四.4 标注修正 + 注记「`:273` 误标 `estimate_required` 已勘误」（尾注：该条 v0.3 曾误引 `:206/:249/:274` 参数行落改，后经 @Hermes 终审裁定回滚——已回滚，v0.2 原值 `:205/:248/:273` 即终审基准，详见 §九 注 1（`:155`）及注 1 补记（`:160`）） |
| 2 | §三 S1 | `generation.py:53`（单行） | `collab_publish` 定义实际 `:53`，函数体至 `:58` | 修正为 `:53-58`（完整路径 `backend/app/api/routes/generation.py`） |
| 3 | §三 S1 | join 回放路径 `generation.py:94-102` | `event_stream` 内回放循环实际 `:93-95`（`for entry in _collab_event_log...`） | 修正为 `:93-95` |
| 4 | §四.1 | `/create` 路由 `generation.py:685` | `backend/app/api/routes/generation.py:685` `estimate_required(request.mode, len(request.user_input or ""), complexity)` ✅ 行号无误，补完整路径 | 补完整路径，行号不变 |
| 5 | §5.1 | `quota.py:262` / `:214`（裸文件名） | `check_quota` 函数 `:262` / `check_credits` 函数 `:214` ✅ 行号无误，补完整路径 `backend/app/core/quota.py` | 补完整路径，行号不变 |
| 6 | §5.3 ② | `config.py:12-15/:18-27/:75` | `backend/app/core/config.py`：`:12` `_PROJECT_ROOT` / `:15` `_DB_PATH` / `:18-27` `_anchor_db_url` / `:75` `_raw.database_url = _anchor_db_url(_raw.database_url)` / `:76` `settings = _raw` ✅ | `:75` 补全为 `:75-76` 收尾锚定 |

**路径勘误总则**（v0.2 起全稿统一）：

| 裸文件名（v0.1 沿用台账简写） | 完整路径（HEAD `bcd202c` 实测） |
|---|---|
| `generation.py` | `backend/app/api/routes/generation.py` |
| `quota.py` | `backend/app/core/quota.py` |
| `db.py` | `backend/app/db.py` |
| `config.py` | `backend/app/core/config.py`（非台账历史误记的 `backend/app/config.py`） |
| `useCollabStream.ts` | `app/components/collab/useCollabStream.ts` |

**§八 第 7 条（v0.4 ④ BOM 口径行同步登记，@Hermes M4 终审裁定）**：`STATUS.md` BOM 口径行（随 `a2134ef` 入库——「BOM 核验口径终审裁定：无 BOM 属历史既成状态，不追溯补 BOM；STATUS.md 须登记差异」）同步登记进本稿 §八 修正登记表；M4 落码前统一核验三份 docs 维持无 BOM（UTF-8 无 BOM）现状，仅 `STATUS.md` 保留 BOM 头行既有规范（`EF BB BF`）。

> **M4 落码引用规则**：分发点清单 §三（D1-D5 / S1-S2）与预扣点章节 §四全部行号以 **v0.2 表为准**（本表 + 正文修正后行号），M4 PR 验收基线直接引用；v0.1 稿行号（含勘误前 `:273` 标注 / S1 `:94-102`）作废，仅作版本对照保留。

**文件路径勘误**：本稿独立文件为 `docs/m3-b-sse-incremental-events-draft.md`（v0.1 首落即此路径，v0.2 定稿不改文件名）；并入 `docs/phase4-plan.md` 的章节编号为 **§4·B**（v0.2.4 新增），二者无冲突。

## 九、v0.3 修正登记（@Codex M3 实码核认报告 2026-09-16 复核意见 + @Hermes M3 终审行号裁定，本稿 v0.2 → v0.3 逐条落改）

> @Codex 核认报告结论「M2 终审裁定全部 7 条硬约束在 `bcd202c` 实码可验，无违反项」，本稿 v0.2 锁定口径全部成立；本登记 3 条（注 1 行号项经 @Hermes 终审裁定回滚，注 2/注 3 表述勘误保留），连同 @Hermes 2026-09-16 终审行号裁定一并登记：

| # | v0.2 位置 | v0.2 原文 | 实码复核结果（HEAD `bcd202c`，@Hermes 终审裁定） | v0.3 落改 |
|---|-----------|----------|-----------------------------------------------|-----------|
| 注 1（回滚项） | §四.4 | 台账漂移行号 `:273`（check_quota COUNT）/ `:248`（check_credits COUNT）/ `:205`（get_quota_status_sync COUNT） | @Codex 核认报告引用 `:206/:249/:274`，v0.3 一度据此落改；**@Hermes M3 终审裁定（2026-09-16）：`:206/:249/:274` 系参数行（`user_id, since`）误引，非 COUNT 字面量行——`HEAD bcd202c` 工作树直读实测 = `:205`（`get_quota_status_sync`）/ `:248`（`check_credits`）/ `:273`（`check_quota`），SQL 字符串字面量行口径（本稿计数口径基准行 = SQL 字符串字面量所在行，与 @Codex 报告所引参数行偏差 −1），v0.2 原值正确，v0.3 落改作废回滚；「台账漂移 +1 行」结论一并作废** | §四.4 口径行回滚为 `:205/:248/:273`（SQL 字面量行口径），v0.3 误引 `:206/:249/:274` 作废仅作版本对照保留 |
| 注 2 | §四.1 | 「`generation.py:685` `estimate_required(request.mode, ...)` 调用点」 | `:685` 即调用点（`required = estimate_required(request.mode, len(request.user_input or ""), complexity)`，@Codex 核认 ✅）；函数定义在 `quota.py:23`——v0.2 措辞「调用点」指向定义处系笔误 | §四.1 勘误为「调用点 = `generation.py:685`，函数定义 = `quota.py:23`」（保留，M3 收口裁定 ✅） |
| 注 3 | §四.2 | 单测锚点 `test_quota_m2.py:99` | 实测 `:99` collaborative → 0 + `:100` full_control → 0，双行锚点（R6 风险项「`full_control` 同路径」实码验证点） | §四.2 补 `:99-100` 双行锚点 + `full_control` 同路径注记（保留，M3 收口裁定 ✅） |
| 注 4（强化项，@Hermes 终审裁定 ⑤） | §5.1 | 429/402 路径分离标注（判定函数归属未写死） | **429 协议侧分支属 `check_quota` 免费额度耗尽路径**（code=`daily_free_quota_exceeded`，判定函数 `quota.py:239`（429 双锚注释注记；L87 原引 `:262` 系 `check_quota` def 行，B1 `bdea9bd` +20 行后漂移至 `:239`，`:219` 为 `d56b8ae` 勘误中间值，均作废仅作版本对照），分支体 `generation.py:761-772`）；**402 属 `check_credits` 积分余额不足路径**（code=`insufficient_credits`，`insufficient_credits` 实码行 = `generation.py:778`（分支体 `:776-782` 内），L87 原引 `:214` 作废，M4 终审裁定更正为实码行 `generation.py:778`（402 单锚，`insufficient_credits` 字面量行））；判定互斥零交叉（429 = `balance == 0`，402 = `0 < balance < required`） | §5.1 判定函数归属写死 + M4 跨归属改动即 PR 打回声明（本 note 落改处 = 强化标注落库点，零代码变更） |

> **注 1 补记（偏差归因，供 M4 引用）**：@Codex 核认报告引用了 `:206/:249/:274`（COUNT 语句参数行），本稿 v0.3 据此落改 §四.4；@Hermes M3 终审复审以 HEAD `bcd202c` 工作树直读裁定口径统一取 **SQL 字符串字面量行**（`"SELECT COUNT(*) AS cnt FROM usage_log WHERE user_id = ? AND generated_at >= ?"` 所在行）：`:205`（`get_quota_status_sync`）/ `:248`（`check_credits`）/ `:273`（`check_quota`），与 @Codex 报告所引参数行偏差 −1，v0.2 原值即为终审基准。

**v0.3 起 M4 落码引用规则（@Hermes 终审裁定版）**：§三 分发点清单（D1-D5 / S1-S2）行号以 §八 v0.2 表为准；§四.4 当日计数口径行号以 **§九 注 1 回滚值 `:205/:248/:273`**（SQL 字面量行口径）为唯一基准，v0.3 误引 `:206/:249/:274`（参数行）作废仅作版本对照保留；`docs/phase4-plan.md` §4·B.6 勘误行 ① 行号引用随本 commit 同步回滚（零代码变更）。

## 九-补、v0.4 勘误行登记（@Hermes M4 终审裁定 ①③④⑤，本稿 v0.3 → v0.4 逐条登记）

| # | 位置 | 裁定 | v0.4 登记 |
|---|------|------|----------|
| ① | §一 1.2 `viewer_joined` 行 + §二 规则 3 | `viewer_joined` 载荷补 `user_id` 字段 + BOM 登记 | §一 1.2 `viewer_joined` 载荷升为 `{session_id, viewer_id, user_id, ts, viewers_total}`；§二 规则 3 客户端降级逻辑同步强化（缺失 `user_id` → 渲染「未上报」，禁止默认 `1`）；BOM 口径登记见 §八 7 |
| ② | §一 1.2 `presence_snapshot` 行 | 首帧设计维持 v0.3 零改动 | 本行不改动（`{session_id, viewers: [{viewer_id, last_seen_ts}], ts}` 维持 v0.3 原 schema）；勘误登记于本表 |
| ③ | §二 规则 3 | 客户端降级逻辑强化 | §二 规则 3 末尾补「v0.4 ③ 强化」句：缺失 `user_id` → 面板渲染「未上报」，禁止默认渲染 `1` |
| ④ | `STATUS.md` BOM 口径行 | BOM 口径行（随 `a2134ef` 入库：无 BOM 属历史既成状态，不追溯补 BOM，STATUS.md 须登记差异）同步登记进 §八 修正登记表 | §八 追加第 7 条（BOM 口径行登记） |
| ⑤ | §5.1 429/402 分离标注 | 维持现状 | 本行不改动（v0.3 强化项已落库，§九 注 4）；勘误登记于本表。**注 4 行号漂移补录（随 ⑤ 勘误行一并登记）**：注 4 原文引用的分支体 `generation.py:690-701` / `:705-711` 与判定函数 `quota.py:262` / `:214` 系 `2a7a5bd` 前旧值，M4 终审裁定更正为实码行——429 code 实码行 = `generation.py:768`（分支体 `:761-772`）/ 402 code 实码行 = `generation.py:778`（分支体 `:776-782`）；§5.1 正文已同步落改 |

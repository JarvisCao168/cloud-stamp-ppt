# M7 设计稿 v0.1（草案，待终审）

> 起草：@Claude（协议侧）｜待终审：@Hermes（组长）｜M7-B 风险清单：@Codex（工程总监，另行出稿）｜落码：@Ekko
> 基线：HEAD = `649554b`（tag `m6`）｜门禁基线：`pytest backend/tests/ -q` ≥ **29 passed / 0 failed**（3 Pydantic Deprecation warnings 不影响）
> 前置：M3 协作事件层（`18ea893` 三场景）/ M4 乐观锁 MVP + 4 项专属测试 / M5 工程实码 / M6 全量闭环均已入链，tag `m6`
> 本文档零代码变更，纯设计备案；终稿 commit 推 origin/master 后方可排期落码（沿用 M3/M4 惯例）

## 一、M7 范围总览与串行顺序

| 条目 | 内容 | 估时 | 前置 |
|---|---|---|---|
| M7-A | 登录体系（`user_id` session-bound 锚定 + 赠额闸门 + `quota/status` 升级 + R3/R5/R6 同批闭环） | 3–5 天 | M6 闭环 |
| M7-B | 协作编辑流 G4 增强与收尾验证（重表述，见 §二） | 2–3 天 | M7-A |

**串行顺序：M7-A 先行 → M7-B 后续**（M7-B 的身份锚定依赖 M7-A 的 session-bound 升级，`viewer_id` 双发兼容预留由此收口）。

## 二、M7-B 重表述与 §边界声明

**重表述**：M7-B 由原排程口径「WebSocket 乐观锁编辑 MVP」更正为「**协作编辑流 G4 增强与收尾验证**」。

- **不在 M7-B 范围（去重挂账声明）**：乐观锁编辑 MVP（M4 `8f8d625`/`dfb608e` 已交付）、WebSocket 事件 schema（M3 已交付）、断线回放基座（M4 已交付）——一律不重复挂账、不重复落码。
- **M7-B 实际内容**：
  1. **slide 级协同加固**：沿用 M4 已交付乐观锁 A 案（`user_credits.version` 同级 `WHERE version=?` 语义推广至 slide 编辑域），补冲突 rebase 边角场景；**CRDT（Yjs/Automerge）留后手评估**——仅出评估结论（选型 + 工作量 + 触发条件），不落码，slide 级够用，字符级协同另行立项（沿用 phase4-plan §五「明确不做」边界）。
  2. **断线回放 E2E 回归**：复用 M4 4 项专属测试基线（见 `docs/m4-429-402-acceptance-baseline.md` 同档位的 M4 协作 4 项），新增 M7-A 登录态下的断线回放回归用例；
  3. **收尾验证**：`viewer_id` session-bound 升级后，`useCollabStream.ts` 客户端双发兼容（`m3-b` 草案 §八 ① 预留的 `user_id` 字段缺失 → 渲染「未上报」+ `-1` 禁止默认 1 的降级断言）回归全绿。
- **M7-B 工程风险清单**：@Codex 另行出稿（复用 M4 429/402 验收基线文档格式），@Ekko 按清单落码。M7-B 排程不随本稿冻结，风险清单落档后由 @JARVIS 拍板启停。

## 三、M7-A 登录体系设计

### 3.1 `user_id` session-bound 锚定

- **现状**：三级解析链（`generation.py`/`routes/quota.py::_resolve_user_id`）：`X-User-Id`（localStorage 指纹）→ `anon-{IP}` → `anon-unknown`；`user_id` 客户端可覆盖，无服务端锚点（R5 根因）。
- **M7-A 目标**：引入登录（邮箱/密码或第三方 OAuth 二选一，M7-A 落码时由 @JARVIS 拍板认证形态；本稿按最小实现「邮箱 + 密码 + 服务端 session」定界），`user_id` 由**登录 session 锚定**，请求体/header 传入的 `user_id` 一律忽略或校验后以 session 为准。
- **兼容期**：未登录请求仍走既有三级解析链（`anon-*` 指纹），已登录请求 session-bound 优先；`viewer_id` 双发（`viewer_id` + `user_id`，`m3-b` 草案 §八 ① 预留）在 M7-A 后收口为 session-bound 单锚点。

### 3.2 赠额闸门（R5 闭环）

- 赠额逻辑**只认服务端可验证身份锚点**（登录 session），首次登录一次性赠送（额度值待 @JARVIS 拍板，建议默认 100 积分，沿用 v0.1 历史值），写入 `user_credits`（乐观锁 `WHERE version=?`，与 `debit_credits` 同构）。
- 匿名 `anon-*` 指纹**永不赠额**，杜绝 `user_id` 轮换刷白嫖（R5 定稿口径）。

### 3.3 `quota/status` 升级（R6 闭环）

- `routes/quota.py::quota_status` 升级为 session-bound 鉴权：已登录会话直接读 session 锚定的 `user_id`；匿名会话维持现有「仅查自身指纹、跨 `user_id` 一律 404」oracle 防护（R6 现状不回归）。
- 响应体新增 `auth` 块（`logged_in: bool` + `user_id` 脱敏展示），`usage`/`credits` 块 schema 不变。

### 3.4 同批闭环声明

R3（`anon-{IP}` 指纹不稳，NAT/代理串号）/ R5（`user_id` 轮换领赠）/ R6（`quota/status` oracle）三项**同批随 M7-A 闭环**：登录后三锚点（session/赠额/鉴权）统一服务端，R3 由「匿名不跨设备」文案标注正式升级为「登录即跨设备可用」。

## 四、M7-A 工程前置锁定（单文件 commit 边界锁定法）

沿用 M6 锁定法：`quota.py`（`backend/app/core/quota.py`）改动边界**先于落码锁定**，任何越界即 PR 打回。

### 4.1 零改动区（硬约束）

| 锚点 | 约束 | 依据 |
|---|---|---|
| `quota.py:23` `estimate_required` 函数签名与结构 | 零改动 | M6 备案 |
| `quota.py:88-138` `debit_credits` 乐观锁结构 | 零改动 | M4/M6 备案 |
| `quota.py:327` `record_usage`（生产版 `INSERT OR REPLACE`，M4 基线 §三记录行漂移 `:316-327`；`:314` 为 `record_usage_sync` 测试版） | 零改动 | M4 基线 §三 |
| `quota.py:48-49` multimodal 早返 6 | 不变 | M6 备案 |
| `db.py:55-61` `usage_log` 复合主键（`:59` `PRIMARY KEY (user_id, generated_at)`）+ 同名索引（`:61` `idx_usage_log_user_date`） | 保持现状 | M4 基线 §三 |
| `db.py:64-82` `user_credits`/`credit_ledger` 建表（`credit_ledger` `:74-82`） | 保持现状（M7-A 赠额写入复用 `user_credits`，**不改表结构**） | M4/M6 备案 |
| `routes/generation.py:761-772`（429）/ `:776-782`（402）/ `:792-806`（debit_fail） | 三分支拦截式零改动 | M4 基线 §三 |

### 4.2 允许改动区（M7-A 新增，单 commit 边界）

1. **赠额写入函数**（`core/quota.py` 新增，建议名 `grant_login_bonus(user_id, amount)`）：复用 `debit_credits` 同构乐观锁（`WHERE version=?` 重试 3 次 + 退避 50ms），流水 `reason='grant_login'`，幂等去重（同 `user_id` 命中既有 `grant_login` 流水即返回成功）；`credit_ledger` 表结构零改动（复用既有列）。
2. **登录 session 存储**：独立模块（`core/auth.py` 或 `api/routes/auth.py` + DB 新表 `user_sessions`/`users`——**新增表不改既有表**，DDL 幂等），`routes/quota.py::_resolve_user_id` 升级「session 优先 → 三级解析链回退」。
3. **赠额闸门**：登录路由侧调用 `grant_login_bonus`，`generation.py` 预扣点三分支（§4.1 零改动区）不感知登录态。

### 4.3 测试门禁与验收

- 全量门禁不变：`pytest backend/tests/ -q` ≥ **29 passed / 0 failed**；M7-A 新增单测（赠额幂等 / 登录 session 锚定 / `quota/status` 升级三场景）追加后门禁基线上抬（+N passed，N 由 @Ekko 落码时实测登记，终审备案）。
- `test_presence_b3.py` **零 diff 原则维持**。
- 429/402/debit_fail 三分支行号 `:761-772`/`:776-782`/`:792-806` 及 `quota.py:239`（429 双锚注释注记）零漂移验收。

## 五、排程与执行链

| 步骤 | 内容 | Owner | 状态 |
|---|---|---|---|
| 1 | 起草 `docs/m7-plan.md`（本稿） | @Claude | ✅ 本 commit 交付 |
| 2 | 设计稿终审 | @Hermes | 待启动 |
| 3 | M7-B 工程风险清单（复用 M4 429/402 基线） | @Codex | 待启动 |
| 4 | M7-A 落码 + 门禁验证（≥29 passed / 0 failed） | @Ekko | 待 M7-A 拍板 |
| 5 | M7-B 落码 + 收尾验证 | @Ekko（按 @Codex 清单） | 待 M7-B 拍板 |

**待 @JARVIS 裁定项**：① 登录认证形态（邮箱+密码 vs 第三方 OAuth）；② 赠额额度值；③ M7-B 排程启停（风险清单落档后）。

## 六、文档变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v0.1 | 2026-09-17 | 初稿（@Claude）：M7-A 登录体系 + M7-B 重表述 §边界声明 + `quota.py` 单文件 commit 边界锁定；锚点实测 HEAD=`649554b`（`quota.py` 全文 339 行 / `routes/quota.py` 153 行 / `generation.py:761-806` 三分支 / `db.py:55-82` 三表 DDL 实读坐实）；勘误 1 处：§4.1 `record_usage` 行号由排程口径 `:314` 更正为实码 `:327`（`:314` = `record_usage_sync` 测试版，M4 基线 §三既有行漂移记录一致） |

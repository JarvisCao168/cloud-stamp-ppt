# M3 A+B 合并工程排期 + 风险清单（@Codex 工程总监侧，2026-09-16）

**日期**: 2026-09-16（v0.2 @Codex 第 2 步交付定稿）～2026-09-16（v0.3 @Hermes 终审裁定 R2 核销同步：行号基准回填 `:205/:248/:273`，429/402 判定函数归属强化标注并入，零代码变更）～2026-09-16（v0.5 @Codex 误因溯源归因确认：核认报告「COUNT(*) 行」引用系 SQL 参数行（`:206/:249/:274`）而非 COUNT 字面量行，工程侧报告统一采用「SQL 字符串字面量行」口径标注，行号基准维持终审基准 `:205/:248/:273` 不变）～2026-09-16（v0.7 @Hermes 方式 ① 终审照单：正文 generation.py 行号漂移值替换为 `:751` 系列，补录来源 = M4 B1 commit `2a7a5bd`（`:43-48` 新增 `_collab_presence` 注册表致下游统一 +71 偏移），随 M4 收口 commit 入库，零代码变更）～2026-09-16（v0.8 @Hermes M4 终审裁定 L44/L45 勘误落改：§三.2 429 行 `quota.py:262`→`:219`（`daily_free_quota_exceeded` 实码行），402 行 `quota.py:214`→`generation.py:778`（`insufficient_credits` 实码行）；§九 勘误行 #15 登记，零代码变更）
**作者**: Codex（工程总监，M3 启动令 A+B 裁定第 2 步交付）
**状态**: 定稿 v0.8（M4 收口，零代码变更；v0.8 = @Hermes M4 终审裁定 L44/L45 勘误落改——§三.2 429 行 `quota.py:262`→`:219` 实码行，402 行 `quota.py:214`→`generation.py:778` 实码行，§九 勘误行 #15 登记，quota.py 终审基准 `:205/:248/:273` 不变；历史 v0.7（M4 收口，零代码变更；v0.7 = @Hermes 方式 ① 终审照单——正文 generation.py 6 处行号漂移值替换为实码 `:751` 系列（补录来源 = M4 B1 commit `2a7a5bd`，`:43-48` 新增 `_collab_presence` 注册表致下游统一 +71 偏移），行号基准行补 generation.py 实码基准，quota.py 终审基准 `:205/:248/:273` 不变；历史 v0.5（M3 交付物，零代码变更；A 实码核认 + B 排期并入，基座 `098cde9` 不动，B 落码在 M4；v0.2 一度误引参数行 `:206/:249/:274` 已按 @Hermes M3 终审裁定回滚为 SQL 字符串字面量行口径 `:205/:248/:273`，R-DDL-2 漂移 +1 行结论核销；v0.4 完成 @JARVIS 收讫裁定三处修订一轮；v0.5 完成 @Codex 误因溯源归因确认——核认报告「COUNT(*) 行」引用系 SQL 参数行而非 COUNT 字面量行，工程侧报告统一采用「SQL 字符串字面量行」口径标注，行号基准维持终审基准 `:205/:248/:273` 不变）
**前置**: M3 启动令 4 步序列第 2 步；@Claude B 草案 v0.3 定稿（`docs/m3-b-sse-incremental-events-draft.md`）+ `docs/phase4-plan.md` §4·B 落码（commit `4d6e844`）
**行号基准**: @Hermes M3 终审裁定（2026-09-16）唯一基准——`quota.py` 当日计数口径三处 = `:205`（`get_quota_status_sync`）/ `:248`（`check_credits`）/ `:273`（`check_quota`），**SQL 字符串字面量行口径**（v0.2 一度误引参数行 `:206/:249/:274`，系 `git show bcd202c:` 误报偏差 −1，已作废仅作版本对照保留；「台账漂移 +1 行」结论一并作废）；与 B 草案 v0.3 §九 回滚注 1、`docs/phase4-plan.md` §4·B.6 勘误行 ① 终审基准三方对齐；M4 落码 PR 合入后再随 commit 复核一次。`generation.py` 实码基准（v0.7 补录，`2a7a5bd` 后 M4 实测，统一 +71 偏移）：`check_quota` 调用点 `:751` / `estimate_required` 调用点 `:756` / `check_credits` 调用点 `:757` / 429 分支体 `:761-772` / 402 分支体 `:776-782` / debit_fail 兜底 `:792-806` / `record_usage` 调用点 `:822`（v0.5 原值 `:685-751` 系列即 +71 前漂移值，作废仅作版本对照保留；M4 B2 diff / B3 单测注释一律引用 `:751` 系列）
---

## 一、A 线 4 项（实码核认 → 已闭合，M3 零变更）

| # | 项 | 核认结论（HEAD `bcd202c` 实码） | M3 动作 |
|---|----|--------------------------------|---------|
| A1 | `estimate_required` 签名零改动（`backend/app/core/quota.py:23`，`(mode, input_len, complexity="auto") -> int`） | 实测零改动 | 零变更，M4 B 落码直接复用 |
| A2 | `debit_credits` 乐观锁结构零改动（`quota.py:57-107`：`BEGIN IMMEDIATE` + `WHERE version=?` + 3 次重试 + 50ms 退避 + `(False, -2)` 返回） | 实测结构完整（重试 `for _ in range(3)` `:73`，退避 `asyncio.sleep(0.05)` `:96`，兜底 `return (False, -2)` `:107`） | 零变更 |
| A3 | `mode="collaborative"` 分桶路径同落 0（`quota.py:39-40`，与 `full_control` 同分支，无需新增枚举值） | 实测 `if mode in ("collaborative", "full_control"): return 0`；单测锚点 `backend/tests/test_quota_m2.py:99`（collaborative->0）+ `:100`（full_control->0）双行验证 | 零变更，B 预扣点直接继承 |
| A4 | `generation.py` 三分支拦截式零改动（429 `:761-772` / 402 `:776-782` / debit_fail `:792-806`）+ `record_usage` 调用点 `:822`（v0.7 补录 `2a7a5bd` 实码，+71 前原值 `:690-701/:705-711/:721-735`、`:751` 作废仅作对照） | 实测零改动；`estimate_required` 调用点 = `backend/app/api/routes/generation.py:756`（函数定义在 `quota.py:23`，B 草案 v0.3 §四.1 已勘误归位） | 零变更 |

**A 线收口状态**：M3 内 A 线 4 项全部为「核认确认 + 零代码变更」，无 M3 侧改动项；M4 B 落码时 A 线 4 项作为不变基线直接引用，任何触碰即 PR 打回（见 §四 硬约束）。

## 二、B 线 3 项（排期，M4 落码）

| # | 项 | 内容 | 预计 | 前置 |
|---|----|------|------|------|
| B1 | 后端分发点 S1-S2 接入 | `generation.py:53-58` `collab_publish()` 新增 3 类事件写入 `_collab_event_log`（容量 100 条不变）；`generation.py:89-113` `event_stream()` 新增 per-connection 连接簿记（join -> `viewer_joined`；Queue 关闭/30s 心跳超时 -> `viewer_left`；新 join 回放后首帧 -> `presence_snapshot`，回放路径 `:93-95` 天然覆盖快照下发，**无需新增回放通道**） | 1 天 | 基座 `098cde9` + B 草案 v0.3 §三 分发点清单 D1-D5/S1-S2 验收基线 |
| B2 | 前端分发点 D1-D5 接入 | `app/components/collab/useCollabStream.ts`：`:23-39` `CollabEvent` 联合类型 +3 成员（schema 冻结，既有 4 成员零改动）；`:41-50` `CollabStreamState` +2 字段（`viewersTotal`/`lastPresenceTs`，全缺失 -> `null` -> 面板「未上报」降级，未知字段忽略不报错）；`:111-136` `onEvent` +3 分发分支（不复用 `processedProgressRef` 去重指纹）；`:138-141` `es.addEventListener` +3 行监听器；`:9` 头注释协议表 +3 事件行（与 STATUS.md SSE 事件协议表同批） | 0.5 天 | B1 后端事件生产端先落 |
| B3 | 单测 + 回归 | 3 事件分发分支 Vitest 用例 + `test_quota_m2.py:99-100` 双行锚点回归（`collaborative`/`full_control` 同落 0）+ E2E 基线 55/56 不劣化 | 0.5 天 | B1+B2 全落 |

**B 排期合计约 2 天**（M4 窗口内串行 B1->B2->B3；M3 侧零变更，本排期仅为 M4 落码基准登记）。

## 三、风险清单（DDL 勘误并入 + 429/402 分离标注 + 硬约束收录）

### 3.1 DDL 勘误（并入，M4 落码前须过一遍）

| 风险 | 描述 | 缓解 |
|------|------|------|
| R-DDL-1 | `usage_log` 复合主键 `(user_id, generated_at)`（`backend/app/db.py:55-59`）+ 同名索引 `idx_usage_log_user_date`（`db.py:61`）——`record_usage`（`quota.py:296-307`）`INSERT OR REPLACE`（`:302`）在复合主键下为 **UPSERT 语义**（非自增 id 直觉的「同名即替换」）；`generated_at` 微秒精度（`:303` `strftime("%Y-%m-%d %H:%M:%S.%f")`）使同日两次调用主键恒不等 -> **覆盖路径实际不触发，每次调用各记一行**，「同日超限短路 429」语义不变 | M4 PR 不得改动 `record_usage` 写路径（`quota.py:296-307`）与 DDL（`db.py:55-61`）；`INSERT OR REPLACE` 语句保持原样；勘误落档见 `docs/phase4-plan.md` §4·B.6 ① + B 草案 v0.3 §四.4 |
| R-DDL-2 | 台账行号漂移 +1 行结论**作废**（@Hermes M3 终审裁定，2026-09-16）：当日计数口径三处唯一基准 = `:205`（`get_quota_status_sync`）/ `:248`（`check_credits`）/ `:273`（`check_quota`），**SQL 字符串字面量行口径**；本清单 v0.2 一度误引参数行 `:206/:249/:274` 系 `git show bcd202c:` 误报偏差 −1，已作废仅作版本对照保留；`since = _today_start_utc()` 定义 `:17` 不变 | 行号引用一律以「函数名 + 行号 + 复刻时点」三件套为准，禁止裸行号引用；M4 落码 PR 合入后以 `:205/:248/:273`（终审基准）再随 commit 复核一次 |

### 3.2 429/402 路径分离标注（协议侧必须保持，B 草案 §5.1 已登记）

| 分支 | 判定函数归属（写死，M4 不得改归属） | 判定式 | 语义 | B 线影响 |
|------|--------|------|------|----------|
| 429（`code=daily_free_quota_exceeded`） | **协议侧分支 = `check_quota` 免费额度耗尽路径**（`quota.py:219` 实码行，`generation.py:751` 调用点，`generation.py:761-772` 分支体；v0.7 补录 `2a7a5bd` 实码，原值 `:262`/`:680`/`:690-701` 作废仅作对照） | `check_quota` 判定 `used >= limit` 且 `check_credits` 返回 `balance == 0` | 免费额度当日耗尽 + 无积分，自然日零点（UTC）重置 | B 线 3 事件 `required=0`，不入折算域，不触发 429 判定 |
| 402（`code=insufficient_credits`） | **协议侧分支 = `check_credits` 积分余额不足路径**（`quota.py:214` = `check_credits` def 行；实码 `insufficient_credits` 行 = `generation.py:778`，`generation.py:757` 调用点，`generation.py:776-782` 分支体）；debit_fail 兜底同属 `debit_credits` 归因域（`generation.py:792-806`，`-2` -> 503；v0.7 补录原值 `:214`/`:686`/`:705-711`/`:721-735` 作废仅作对照） | `check_credits` 判定 `used >= limit` 且 `0 < balance < required`（M2 required>0 后激活） | 余额不足预扣 | 同上；B 线不得在 presence 事件上挂任何扣减/判定逻辑 |

**判定互斥零交叉 + 判定函数归属写死（@Hermes 强化项，随 M3 收口 commit 落库）**：429 属 `check_quota` 免费额度耗尽路径（code=`daily_free_quota_exceeded`），402 属 `check_credits` 积分余额不足路径（code=`insufficient_credits`），429 = `balance == 0` 与 402 = `0 < balance < required` 在 `balance` 取值上互斥零交叉；**M4 落码时若误改 `generation.py:761-772`（429 分支）或 `:776-782`（402 分支）任一行为跨判定函数归属改动（如把 `check_credits` 判定逻辑挪入 429 分支或反之），PR 打回**。B 线新增事件不改变 `check_quota`/`check_credits` 任何一行（M3 硬约束 ②③④ 在 M4 继续生效）。

### 3.3 其他风险

| 风险 | 描述 | 缓解 |
|------|------|------|
| R1 | 乐观锁 version 冲突 3 次重试耗尽 -> `(False, -2)` -> 503 服务不可用（非用户侧错误） | M4 不得改重试次数/退避时长；并发压测（M4 B3）覆盖 503 路径 |
| R2 | 账户行不存在（M1 不赠额，`debit_credits` `:81-82` 返回 `(False, -1)`）-> 402 兜底 | M4 不得改「缺行视为余额 0」语义；**R2 行号核销标注**：台账行号漂移 +1 行（`:205/:248/:273` -> `:206/:249/:274`）结论已随 @Hermes M3 终审裁定核销（SQL 字符串字面量行口径终审基准 = `:205/:248/:273`，见 §三.1 R-DDL-2），本项账户行缺失语义结论不变 |
| R3 | 多标签页同用户同会话：`viewer_id` = `user_id` 指纹三级解析链（`X-User-Id` header -> `anon-{IP}` -> `anon-unknown`，B 草案 §一 备案），同指纹多 tab 在 `viewers_total` 中按连接计数（非去重用户数） | M4 B1 连接簿记须带 `conn_id` 维度，`viewers_total` 口径 = 活跃连接数（非去重用户数），前端注释标注 |
| R4 | 回放路径 `_collab_event_log` 容量 100 条（`generation.py:45` `_COLLAB_MAX_LOG = 100`）：高并发场景长会话可能截断早期事件 | 容量不变（硬约束），M4 若需扩容走独立立项，不在 B 线范围 |
| R5 | 网络受限环境（Gamma 等海外工具「需翻墙」为既有竞品槽点，本项目本地部署）：SSE 长连接 30s 心跳（`generation.py:101-104`）超时判定在中断网络下可能频繁触发 `viewer_left` 误报 | M4 B3 回归覆盖断线重连退避（前端既有退避逻辑）+ `presence_snapshot` 全量快照自愈（join 后首帧） |

## 四、M4 落码收口硬约束（「触碰即打回」，M3 起生效）

1. **`usage_log` 复合主键 `(user_id, generated_at)`（`db.py:55-59`）+ 同名索引 `idx_usage_log_user_date`（`db.py:61`）保留 git 跟踪**；`record_usage` `INSERT OR REPLACE` 语句（`quota.py:302`）不改动，M4 B 线不引入第二条计数通道（「整篇计一次」口径同源闭合）。
2. **`config.py` 绝对路径锚定**：实际路径 = `backend/app/core/config.py`（完整路径锚定 `:12` `_PROJECT_ROOT` / `:15` `_DB_PATH` / `:18-27` `_anchor_db_url` / `:75-76` 收尾锚定，HEAD `bcd202c` 实测），**非台账历史措辞的 `backend/app/config.py`**；M4 PR 不得改路径锚定逻辑。
3. **NIT 拦截式判定式**：`generation.py:761-772`（429）/ `:776-782`（402）/ `:792-806`（debit_fail/503）三分支拦截式判定（v0.7 补录 `2a7a5bd` 实码，原值 `:690-701/:705-711/:721-735` 作废仅作对照），判定互斥零交叉，M4 B 线 presence 事件不触碰任何分支一行。
4. （附：B 草案 §四.2 单测锚点 `test_quota_m2.py:99-100` 双行——`collaborative`/`full_control` 同落 0——为「整篇计一次」约束的实码承载，M4 协作流 checkpoint 动作计费如需另开，走 §3.5.1 路由表末行「M4 协作流 checkpoint 动作计费单独立项」，不在 B 线范围。）

## 五、Gamma 竞对核实（M3 前置 1 天，并行启动）

**范围（v0.4 登记：@JARVIS 收讫裁定 ①②③ 照单执行，本项已锁定，工程侧可立即启动）**：
- **竞对名单**：Gamma（gamma.app）+ 既有竞品矩阵（Beautiful.ai / Tome / 讯飞智文 / Kimi PPT / WPS AI，见 `docs/ai-ppt-competitive-analysis.md`、`docs/competitive-analysis-v2.md`）；
- **数据维度（4 维度终审采纳，@Hermes sequence 13 裁定）**：① PPTX 导出兼容（既有槽点「卡片式布局与 16:9 幻灯片架构不兼容，导出后文字溢出/图片裁剪/动画丢失」，`docs/user-feedback-summary-round2.md:44`）② 中文指令理解（Gamma/Tome 既有负面口碑）③ 价格/免费额度档位（Gamma $10/月/月起，`docs/ai-ppt-competitive-analysis.md:25`）④ 协作/presence 能力（与 B 线 3 事件对齐的竞品对标维度，**新增维度**——既有竞品矩阵无协作维度数据，M3 补齐后写入 `docs/competitive-analysis-v3.md`）；
- **核实渠道（三源）**：Gamma 官网 + 帮助中心 + 定价页；
- **启动状态**：@JARVIS 收讫裁定照单执行（2026-09-16），并行线即刻启动，不阻塞主链。

**产出**：M4 窗口前 1 天落档 `docs/competitive-analysis-v3.md`（零代码变更，纯文档），B 线 B3 单测回归时引用。

---

**排期汇总**：M3（本里程碑）= A 线 4 项核认闭合（已交付）+ B 排期登记（本文件）+ 风险清单 + Gamma 核实并行启动（1 天，M4 前置）；M4 = B1->B2->B3 串行约 2 天 + 单测回归；全程基座 `098cde9` 不动，三条收口硬约束贯穿 M3->M4。

---

## 附注：v0.3 落改登记（@Hermes 终审裁定，2026-09-16，随 M3 收口 commit 落库）

| # | 位置 | 落改内容 | 依据 |
|---|------|----------|------|
| 1 | §三.1 R-DDL-2 | 行号漂移 +1 行结论核销——当日计数口径三处唯一基准 = `:205`（`get_quota_status_sync`）/ `:248`（`check_credits`）/ `:273`（`check_quota`），SQL 字符串字面量行口径（`git show bcd202c:` 误报偏差 −1 作废仅作版本对照保留） | @Hermes M3 终审裁定 ①（2026-09-16） |
| 2 | §三.2 429/402 强化标注 | 判定函数归属写死——429 属 `check_quota` 免费额度耗尽路径（code=`daily_free_quota_exceeded`，`quota.py:262`，分支体 `generation.py:761-772`；402 属 `check_credits` 积分余额不足路径（code=`insufficient_credits`，`quota.py:214`，分支体 `generation.py:776-782`）；判定互斥零交叉；M4 跨归属改动即 PR 打回 | @Hermes M3 终审裁定 ⑤（2026-09-16） |
| 3 | §三.3 R2 | 行号漂移核销标注并入 | 同 R-DDL-2 裁定 |
| 4 | 文件头部 | 行号基准行回滚为终审基准 `:205/:248/:273` + 状态行升 v0.3 + 日期行补登记 | 上述 1-3 随组落库 |

## 附注：v0.4 落改登记（@JARVIS 收讫裁定 ①②③ 照单执行，2026-09-16，随 M3 收口 commit 落库）

| # | 位置 | 落改内容 | 依据 |
|---|------|----------|------|
| 5 | §三.1 R-DDL-2 + §三.3 R2 | R2「台账漂移 +1 行」核销标注复核确认（终审基准 `:205/:248/:273`，SQL 字符串字面量行口径，v0.2 参数行 `:206/:249/:274` 作废仅作版本对照） | @JARVIS 收讫裁定 ①②③（2026-09-16）照单执行 |
| 6 | §三.2 | 429/402 判定函数归属标注复核确认（429=`check_quota`/402=`check_credits`，M4 跨归属改动即 PR 打回） | @JARVIS 收讫裁定 ①②③（2026-09-16）照单执行 |
| 7 | §五 | Gamma 范围登记：竞对名单 + 4 维度终审采纳 + 三源渠道 + 启动状态 = 已锁定，工程侧即刻启动 | @JARVIS 收讫裁定 ①②③（2026-09-16）照单执行 |
| 8 | 文件头部 | 状态行升 v0.4 + 日期行补登记 + 行号基准维持终审基准 `:205/:248/:273` | 上述 5-7 随组落库 |

## 附注：v0.5 落改登记（@Codex 误因溯源归因确认，2026-09-16，随组 M3 收口同 commit 落库）

| # | 位置 | 落改内容 | 依据 |
|---|------|----------|------|
| 9 | §三.1 R-DDL-2 | 误因溯源归因补记——@Codex 实码核认报告「COUNT(*) 行」引用的是 SQL 参数行（`user_id, since`，`:206/:249/:274`）而非 COUNT 字面量行，B 草案 v0.3 据此误引；本清单 §三.1 既有「`git show bcd202c:` 误报偏差 −1」归因表述与终审口径（工程侧报告统一采用「SQL 字符串字面量行」口径标注）合并确认，两口径互斥标注不再并存 | @Codex 终审确认逐条对照（2026-09-16） |
| 10 | 文件头部 | 日期行补登记 v0.5 + 状态行追加归因确认（行号基准维持终审基准 `:205/:248/:273` 不变） | 上述 9 随组落库 |

## 附注：v0.7 落改登记（@Hermes 方式 ① 终审照单，2026-09-16，随 M4 收口 commit 入库）

| # | 位置 | 落改内容 | 依据 |
|---|------|----------|------|
| 11 | 文件头部 | 状态行升 v0.7 + 日期行补登记 + 行号基准行补 generation.py 实码基准 `:751` 系列（quota.py 终审基准 `:205/:248/:273` 不变） | @Hermes 方式 ① 终审照单（并入 M4 收口 commit，不重开 M3） |
| 12 | §一 A4 / §三.2 / §四.3 | 正文 generation.py 行号漂移值 6 处替换为实码 `:751` 系列——`check_quota` 调用点 `:751`、`estimate_required` 调用点 `:756`、`check_credits` 调用点 `:757`、429 分支体 `:761-772`、402 分支体 `:776-782`、debit_fail 兜底 `:792-806`、`record_usage` 调用点 `:822`；v0.5 原值（`:685-751` 系列）作废仅作版本对照保留；M4 B2 diff / B3 单测注释一律引用 `:751` 系列 | M4 B1 commit `2a7a5bd`（`:43-48` 新增 `_collab_presence` 注册表，下游统一 +71 偏移）实码对齐（@Codex 工程侧核认逐条对照，2026-09-16） |

## 附注：v0.7 落改补充登记——§九 勘误行（2026-09-16，随 commit `dfb608e` 同组入档）

| # | 位置 | 落改内容 | 依据 |
|---|------|----------|------|
| 13 | §三.2 429/402 强化标注行 | 强化标注维持现状——正文未改动，仅本勘误行登记（⑤ 裁定维持 429/402 分离标注现状） | @Hermes M4 终审裁定 ⑤（`dfb608e` 落改项 ⑤，纯文档登记） |
| 14 | §一 A4 / §三.2 / §四.3 generation.py 行号基准 | 行号基准维持 v0.7 原值——正文未改动，仅本勘误行登记（v0.7 补录后 `:751` 系列为现行基准） | @Hermes M4 终审裁定 ②（presence_snapshot 首帧零改动，行号基准随行号基准线不动） |
| 15 | §三.2 429/402 判定函数归属行 | §三.2 行 44/45 勘误落改——429 行 `quota.py:262` → `:219` 实码行（`daily_free_quota_exceeded` 实码行，def `check_quota` 在 `:262`，原引 `:262` 系 def 行误引）；402 行 `quota.py:214` → `generation.py:778` 实码行（`insufficient_credits` 实码行，`quota.py:214` 为 `check_credits` def 行）；原值作废仅作对照 | @Hermes M4 终审裁定（L44/L45 勘误，实码核准通过，随本 commit 落库） |

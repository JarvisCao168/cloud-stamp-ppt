# M7-B G4-3：CRDT 后手评估（v1.0）

> 出账 commit 前草案；owner @Ekko（G4-3 落码）｜评估日期 2026-09-18
> 依据：`docs/m7-plan.md` v0.2 §二 内容 1「CRDT（Yjs/Automerge）留后手评估——仅出评估结论（选型 + 工作量 + 触发条件），不落码，slide 级够用，字符级协同另行立项（沿用 phase4-plan §五「明确不做」边界）」
> 前置：G4-1 已出账（`763d7e9`，slide 级乐观锁 `_slide_edit_guard` + session-bound 双发），G4-2 已出账（`b779205`，断线回放 E2E 回归 + 收尾验证，pytest 基线上抬至 54/0）

---

## 一、评估结论（摘要）

**选型结论：维持 slide 级乐观锁（A 案）为主方案，CRDT 列后手 B 案；M7-B 周期内不引入 CRDT。**

| 维度 | 结论 |
|---|---|
| 现状是否够用 | 是。G4-1 `_slide_edit_guard`（`backend/app/api/routes/generation.py`）已覆盖命中/冲突/rebase 三场景，`slide_update` SSE 事件 + `_collab_event_log` 回放通道在 G4-2 E2E 回归中全绿，断线回放链路已验证。 |
| 不引入 CRDT 的判定 | 当前协同粒度为 **slide 级**（整页编辑 + revision 号），无字符级/区域级并发协同需求；乐观锁 + rebase 重试的冲突概率在生产并发规模（单会话 ≤ 3–5 观察者）下极低，无需 CRDT 的无冲突自动合并语义。 |
| 引入 CRDT 的触发条件（后手激活门槛） | 见 §四 触发条件清单，满足 **≥ 2 条** 时立项评估 CRDT 迁移。 |
| 建议选型（若激活） | **Yjs**（理由见 §二 对比表），不推荐 Automerge（团队技术栈 / 生态 / 与现有 SSE 事件层契合度综合判断）。 |
| 工作量估算（若激活） | 前端：useCollabStream 载荷从 `slide_update(revision)` 切换为 Yjs update 二进制流；后端：新增 Yjs Hocuspox / y-protocols 服务端合并节点；E2E：新增字符级并发断言用例。粗估 **5–8 人日**（含选型 spike + 迁移 + 回归），不含字符级协同 UI 另行立项工作量。 |
| M7-B 本批次动作 | **零代码变更**（本文档 + `docs/m7-plan.md` §六 勘入注记），不新增 pytest / vitest 用例，门禁基线维持 **≥ 54 / 0** 不上抬。 |

---

## 二、Yjs vs Automerge 对比

| 维度 | Yjs | Automerge |
|---|---|---|
| 语言 / 运行时 | TypeScript-first，Node.js 服务端原生支持（`y-protocols`） | Rust 核心 + WASM 绑定，JS/TS 封装 |
| 与现有事件层契合度 | 高：Yjs update 可序列化为任意传输层载荷，现有 `collab_publish` / `_collab_event_log` SSE 通道可直接承载 Yjs update blob，无需改协议骨架 | 中：Automerge patch 需独立序列化通道，与既有 SSE 3 事件命名空间（`viewer_joined` / `viewer_left` / `presence_snapshot`）合并成本更高 |
| 断线回放 | `Y.applyUpdate` 幂等回放，天然匹配 G4-2 已验证的「join 回放 → snapshot」模式 | 需自建 last-patch 回放逻辑，工作量更高 |
| 冲突模型 | 无冲突（CRDT 自动合并），乐观锁 rebase 逻辑可逐步下线 | 无冲突（CRDT 自动合并），同上 |
| 团队技术栈匹配 | Next.js + TS 项目，Yjs 官方 TS 示例完整 | Rust/WASM 依赖增加构建链路复杂度，团队无 Rust 基础设施 |
| 包体积（客户端） | 核心 ~30 KB gzipped | 核心 ~50–80 KB gzipped（含 WASM runtime） |
| 成熟度 | 生产级（Figma / CodeMirror 6 等使用） | 较新，生产案例较少 |

**综合建议：若后手激活，选 Yjs。**

---

## 三、Yjs 接入点与迁移路径（草案，未落码）

```
前端（现有 useCollabStream.ts）
  ├── 现状：接收 slide_update(revision) → 客户端 diff 应用
  └── 迁移后：接收 yjs_update(blob) → Y.applyUpdate(doc, blob) → 文档自动收敛

后端（routes/generation.py）
  ├── 现状：_slide_edit_guard + collab_publish('slide_update')
  └── 迁移后：新增 YjsDocumentStore（per-session Y.Doc）
      ├── 写入：mutation → doc.transact → 生成 update blob → collab_publish('yjs_update', {blob})
      ├── 回放：新 join 订阅者回放 _collab_event_log 中 yjs_update 序列（幂等，天然兼容 G4-2 E2E 断言）
      └── 乐观锁：rebase 重试逻辑（_slide_edit_guard 冲突分支）逐步下线，改由 Yjs 自动合并
```

**关键风险**：
1. 会话跨进程（当前 `sessions` / `_collab_subscribers` 为 in-memory dict）——Yjs 状态需随会话生命周期管理，多实例部署时需引入 `y-redis` 或外部 Yjs 持久化层，**M7-B 周期内无多实例部署需求，此风险不激活**；
2. 现有 48→54 基线中 6 条 G4-1 单测（`test_m7b_g41_collab_bound.py`）直接依赖 `_slide_edit_guard` 命中/冲突/rebase 断言——迁移时需同步改写该文件，**基线上抬需重新走 B 位复核**；
3. `test_presence_b3.py` 7 项零 diff 红线在 Yjs 迁移中应维持不动（presence 层与文档层解耦），列入迁移门禁。

---

## 四、后手激活触发条件（满足 ≥ 2 条即立项）

| 编号 | 触发条件 | 判定标准 |
|---|---|---|
| T1 | 字符级并发协同需求进入产品排程 | 产品侧明确需 2 个以上用户 **同页同区域** 同时编辑文本内容（非整页替换） |
| T2 | 乐观锁冲突率持续超标 | 生产埋点显示 `_slide_edit_guard` 冲突命中率 > **5%**（连续 7 天滑动窗口），rebase 重试成为主要延迟来源 |
| T3 | 并发观察者规模突破阈值 | 单会话并发观察者 > **10** 且存在多轮高频 slide_update 洪峰 |
| T4 | 跨设备 / 离线场景纳入需求 | 需支持用户离线编辑后重新上线自动合并（当前 SSE 模型不支持离线队列） |
| T5 | 多实例 / 分布式部署需求 | 后端需支持 > 1 个应用实例同时服务同一会话（当前 in-memory 架构不支持） |

**M7-B 周期（当前）触发判定：T1–T5 均不满足 → 后手维持，不激活，零代码变更出账。**

---

## 五、本次出账范围声明

- **新增文件**：`docs/m7b-g43-crdt-assessment.md`（本文件）
- **修改文件**：`docs/m7-plan.md`（§六 勘入注记：G4-3 评估结论登记 + §二 内容 1 CRDT 后手评估完成标记）
- **代码变更**：无（`quota.py` / `db.py` / `generation.py` / `test_presence_b3.py` 零触碰维持）
- **测试变更**：无新增 pytest / vitest 用例，门禁基线维持 **≥ 54 passed / 0 failed** 不上抬
- **tag**：维持 G4-4 收口统一双侧坐实口径，G4-3 不单独打 tag

---

## 六、`docs/m7-plan.md` 勘入注记

在 §六「文档变更记录」表追加 v0.3 行：

> **v0.3 | 2026-09-18 | G4-3 CRDT 后手评估完成登记（@Ekko）**：① §二 内容 1「CRDT（Yjs/Automerge）留后手评估」标记为已完成，评估结论落档 `docs/m7b-g43-crdt-assessment.md`（v1.0）；② 选型结论：维持 slide 级乐观锁 A 案为主，Yjs 为后手 B 案（M7-B 周期内不引入）；③ 后手激活触发条件 T1–T5 清单已登记，满足 ≥ 2 条时立项；④ 本文档纯文档勘入，零代码变更，门禁基线维持 54/0 不上抬；⑤ tag `m7` 维持 G4-4 收口统一双侧坐实口径。

§二 内容 1 行末追加：`（G4-3 评估已完成，见 docs/m7b-g43-crdt-assessment.md v1.0，结论：维持 A 案为主，Yjs 后手，T1–T5 激活门槛 ≥ 2 条）`

---

*本文档零代码变更，纯评估落档。随 G4-3 commit 推 `origin/master`。*

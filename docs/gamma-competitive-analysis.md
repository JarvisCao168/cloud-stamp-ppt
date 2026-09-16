# Gamma 竞对调研（M4 Gamma D1）

## 范围
- PPTX 兼容性
- 中文指令支持
- 价格档位
- 协作 presence：SSE 事件命名与订阅方式

## 方法与来源
- 官方页面：`gamma.app/pricing`、`gamma.app/teams`、`gamma.app/zh-cn`、`gamma.app/zh-tw`
- 帮助中心：`help.gamma.app` 订阅/升级页
- 第三方核验：eesel.ai、AI Tools Police、usagepricing.com（均标注核验日期；第三方观点不作为产品承诺）

## 结论
### PPTX 兼容性
Gamma 官方将 PPTX 导出列为 Free/Plus/Pro/Ultra/Team/Business 的共享导出能力，支持 PDF、PPTX、PNG 和 Google Slides。但第三方核验反复指出其 web-native card layout 在 PPTX 导出时会压平为图片，字体替换/动画丢失/不可编辑文本层是核心短板。建议本系统把“可编辑 PPTX”作为相对 Gamma 的卖点，验收不能只看导出成功，要看文本层、图表、字体、动画是否保留。

### 中文指令
Gamma 官方中文页面表明支持多语言内容生成和指令输入；`zh-cn`/`zh-tw` 页面可直接用中文描述目标、粘贴大纲或导入 PDF/PPTX。第三方补充说明非英文文本 token 消耗可能更高，长中文 prompt 更容易触达单次生成 token 上限。建议中文指令验收：短 prompt、长 prompt、中英混排、中文数字/序号样式都要单独回归。

### 价格档位
官方 pricing 页（USD annual per-seat display）：Free $0、400 signup credits、10 cards/prompt；Plus $9/seat/mo（$108/seat/yr annual），20 cards/prompt、1,000 monthly credits；Pro $18/seat/mo（$216/seat/yr annual），60 cards/prompt、4,000 monthly credits、API；Ultra $90/seat/mo（$1,080/seat/yr annual），75 cards/prompt、20,000 monthly credits。Team $20/seat/mo（$240/seat/yr annual，2 seats min），Business $40/seat/mo（$480/seat/yr annual，10 seats min）。第三方核验补充 credits 非普通创建无限：Free 的 400 credits 是一次性且不按月刷新；付费档中 Agent、高级模型、API 消耗 credits。

### 协作 presence SSE 事件命名+订阅方式
Gamma 官方公开资料确认“real-time collaboration / live cursors / comments”是产品能力，且第三方核验认为 Free 也包含实时协作（live cursors/comments）。但官方未公开其 presence SSE event names 或 WebSocket 协议字段。对本系统的启示：presence 事件命名应使用稳定、增量式、字段缺失可降级的命名空间（如 `viewer_joined` / `viewer_left` / `presence_snapshot`），不要依赖猜测 Gamma 内部事件；客户端必须忽略未知字段、缺失新字段渲染“未上报”而非默认 1。

## 对本系统 M4 的落点
- PPTX：增加“可编辑文本层”验收，不混同 Gamma 的 image-flattened PPTX。
- 中文：补中文长 prompt token/credit 消耗说明，避免 429/402 文案与中文指令长度冲突。
- 价格：M4 预扣点 `reserve_credit` 的 reason 需要可归因到 `gen_collaborative` 等业务模式。
- Presence：B 线 SSE 草案维持 v0.4，前端 `useCollabStream.ts` 已完成 viewer 事件监听与降级策略测试。

## 验收记录
- B1：`quota.py` 已新增 `reserve_credit`；`test_quota_m2.py` 回归通过（16 tests passed）。
- B2：`useCollabStream.ts` 当前实现已覆盖 D1-D5：类型扩展、状态字段、事件分发、监听器注册、降级逻辑；新增 Vitest 4 tests passed。
- B3：全量 Vitest 193 passed；E2E 当前 `playwright test --list` 共 64 tests（任务中“55/56”是历史目标口径，已登记漂移，不静默改目标）。
- 后端全量 pytest：`backend/tests` 中 quota/test_api 依赖项 20 passed；`backend/test_api.py` 4 个 smoke tests 因本地 8001 backend 未启动失败（httpx.ConnectError），属于环境阻塞而非代码回归。

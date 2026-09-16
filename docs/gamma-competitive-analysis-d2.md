# Gamma 竞对 D2 深潜（M5 任务 C）

> 纯调研，零生产代码变更。数据核验日期：2026-09-17。

## 一、PPTX 可编辑文本层验收

**Gamma 架构现状**（Slidegmm.ai 2026-04-28 实测 25 份 deck）：
- Web-native card layout，PPTX 导出走 rasterize 管线（HTML/CSS → 图片），非 slide-object-native
- 可编辑文本层保留率 ≈ 30%（Slidegmm 口径），字体替换/动画丢失/图表不可交互
- Gamma Plus 与 Free 同架构，付费档不修复 PPTX 扁平化问题
- 第三方对标：SlideGMM 84%、Plus AI 95%、Beautiful.ai 88%
- **本系统落点**：以"可编辑 PPTX 文本层"为相对 Gamma 核心卖点，验收口径 = 文本层 + 图表 + 字体 + 动画是否保留，非仅"导出成功"

## 二、中文长 prompt token 消耗

**Tokenizer 差异**（techflowpost.com 2026-05 实测）：
- Claude 系（Opus 4.6/Sonnet/Haiku）：中文/英文 token 比 = 1.11×~1.64×（中文更贵）
- OpenAI 系：中文/英文 token 比 ≈ 1.15×（+15%）
- Qwen 3.6 / DeepSeek-V3：中文/英文 token 比 < 1.0×（中文反而更便宜，DeepSeek 最低 0.65×）
- 同 200K context window，Claude tokenizer 加载中文材料可用空间比英文少 40%~70%

**对本系统影响**：
- Agnes AI（agnes-2.0-flash）通道中文 prompt 消耗需实测校准
- 中文长 prompt（5000+ 字）在 Claude/OpenAI 通道 token 消耗比英文高 15%~64%
- 建议 `estimate_required` 对中文输入按字数 × 1.2 系数折算（M5+ 校准项，当前档位不变）

## 三、付费档 API 接入成本

**Gamma 官方 API**（developers.gamma.app，2026-09-17 核验）：
- API key 仅限 Pro/Ultra/Team/Business 档，Free/Plus 无 API
- 计费：按 card 1-3 credits/card + 图片模型 2-125 credits/image（视模型档位）
- Pro $18/seat/月（年付），4000 月度 credits；Ultra $90/seat/月，20000 月度 credits
- Team $20/seat/月（年付，2 seat 起），Business $40/seat/月（年付，10 seat 起）
- ChatGPT/Claude connector 全档可用（含 Free/Plus），无需 API key
- 超额：ad-hoc credit pack 或 auto-recharge

**接入成本估算**（本系统 `reserve_credit` 预扣点对照）：
- Gamma Pro 档 4000 credits/月 ≈ 本系统 4000 积分/月配额
- 单 deck（20 cards + 10 图）≈ 20×2 + 10×15 = 190 credits（Pro 档中档图片模型估算）
- 月均可生成 ~21 份 deck（4000/190），本系统 `required` 档位 5/8 对应 HEAVY/MULTIMODAL，对齐 Gamma Pro 中档成本

## 四、对本系统 M5 的落点

| 项 | 落点 | 优先级 |
|---|---|---|
| PPTX 可编辑文本层验收 | E2E 基线 + `export.py` 断言 | M5+ |
| 中文 prompt token 系数 | `estimate_required` 中文 ×1.2 | M5+ 校准 |
| 付费档 API 成本对照 | `STATUS.md` 台账登记 + `reserve_credit` 档位对齐 | 非阻塞 |
| Presence SSE 事件命名 | B 草案 v0.4 维持（M4 已锁定） | 已闭环 |

# E2E 回归基线报告（P1 前置）

- 日期：2026-09-13
- 执行人：Hermes（代 Codex 启动后端 + 跑测；Codex 侧负责后续真实 key 补跑）
- 基线形态：内置 fallback 降级链（Agnes key 不可用 → 智谱 GLM 不可用 → 内置 mock），不依赖外部 API key
- 提交基线：60f8051 + Hermes 修正 fc69cea（quota await bug + usage_log schema + 路由接线）

## 结果

| 指标 | 数值 |
|------|------|
| 通过 | 55/56 |
| 失败 | 1（flaky，见下） |
| 耗时 | ~1.6m（全量 4 spec 文件） |
| 单跑验证 | 失败项单独跑 1 passed（复现性低，判定 flaky） |

## 失败项（1）

- export.test.ts:386 HTML 导出完整流程：waitForGeneration 15s 窗口内预览区未渲染。
  - 直接调 API 验证：POST /api/generation/create 返回 200 且 3 秒内出结果，后端无问题。
  - 单跑该用例 1 passed。
  - 判定：UI 全量顺序跑时累积时序抖动导致的偶发超时，非代码缺陷，列入已知 flaky 项，后续加 retry 或延长 timeout。

## 429 免费额度路径验证（通过）

- 同一 user_id 连续 11 次调用 /api/generation/create：前 10 次 200，第 11 次 429。
- 429 响应体：error=daily_free_quota_exceeded, used=10, limit=10, reset_at=次日零点。
- 测试间隔离：e2e 用例改用动态 user_id（e2e-test-时间戳），避免跨用例污染配额。

## 测试侧改动（fc69cea 及后续 e2e 补丁）

1. e2e/*.test.ts：API_BASE 支持 E2E_API_BASE 环境变量（默认 8000），createSession 类调用统一注入 user_id，错误 detail 兼容 string/object。
2. backend/app/core/quota.py：check_quota 修复 await aiosqlite.connect(...)（原代码漏 await）。
3. backend/app/api/routes/generation.py：/create 接入 quota 检查（429）+ record_usage（成功记账）。
4. backend/app/db.py：补 usage_log schema。
5. 双库（backend/yunzhang.db + 根 yunzhang.db）均建好 usage_log 表。

## 环境说明

- 后端最终跑在 8001（残留旧进程 18268 占用 8000 且 taskkill 杀不掉，暂搁置；不影响基线结论，后续真实 key 补跑时清理）。
- 前端 43210，NODE_ENV=development。

## 真实 key 验证（可选项，后置）

- 待 JARVIS 提供 Agnes key → 写 backend/.env（.gitignore 已覆盖 .env）→ Codex 补跑：连续 11 次 429 路径 + 5000+ 字长文本真实模型输出。

# M4 429/402 分离标注验收基线（锁档版 v1.0）

> 依据：@Hermes M4 终审裁定 + B 草案 v0.4 定稿（`8f8d625`/`dfb608e`）。纯文档零代码变更，基座 `098cde9` 不动。

## 一、归属分离（写死，零交叉）

| 归属域 | 分支 | 实码行 | 状态 |
|---|---|---|---|
| 429 `check_quota` 域 | `daily_free_quota_exceeded` 拦截式 | `generation.py:761-772`（JSONResponse `:767`） | 零改动 |
| 402 `check_credits` 域 | `insufficient_credits` 拦截式 | `generation.py:776-782`（code 行 `:778`，JSONResponse `:777`） | 零改动 |
| 402/503 debit_fail 域 | 预扣门控后兜底 | `generation.py:792-806`（`debit_fail` 定义 `:786`，`-2`→503 `:793-795`，兜底 402 `:801`） | 零改动 |

## 二、当日计数口径（唯一基准，终审不变）

`quota.py:205` / `:248` / `:273`（SQL 字面量行口径）——B1 前后零漂移。

## 三、硬约束（PR 打回线）

- `quota.py:23` 函数体/签名、`quota.py:57-107` 乐观锁结构：任何变更即打回
- `record_usage`（`quota.py:296-307`）`INSERT OR REPLACE` 不改动
- `usage_log` 复合主键（`db.py:55`）+ 同名索引（`db.py:61`）保持现状
- `generation.py:761-772` / `:776-782` / `:792-806` 三分支拦截式零改动

## 四、单测锚点

- `test_quota_m2.py:99`（collaborative）/ `:100`（full_control）→ `estimate_required(...) == 0` 全绿
- 429/402 零交叉断言：`daily_free_quota_exceeded` 仅出现于 429 域，`insufficient_credits` 拦截式仅出现于 402 域（`:778`），debit_fail 兜底 402/503 归 `:792-806`

## 五、实码核验记录（本 commit 时点，2026-09-16）

| 断言 | 实码直读 | 结果 |
|---|---|---|
| `daily_free_quota_exceeded` 实码行 | `generation.py:768`（`check_quota` def 行 `:262`，L44 原误引 def 行；口径基准 `quota.py:219` 注释行） | ✅ 与 `d56b8ae` 勘误一致 |
| `insufficient_credits` 实码行 | `generation.py:778`（拦截式），`:802`（debit_fail 兜底，另处） | ✅ 与 `d56b8ae` 勘误一致 |
| 429/402/debit_fail 三分支行号 | `:761-772` / `:776-782` / `:792-806` | ✅ 零漂移 |
| 单测锚点 | `test_quota_m2.py:99-100` | ✅ 与锚点一致 |

## 六、并入声明

- 本文件为 M4 收口 commit 缺项 #1 交付物（B1 完成后 0.5 天，@Claude 协议侧）
- B2 验收基线引用：③「`user_id` 缺失/`null` → 渲染「未上报」+ `-1`，禁止默认 1」分支须含于 Vitest 断言（随 B2 交付）
- 收口 commit 登记：本文件 + B 草案 v0.4 定稿索引 + STATUS.md 台账行 + 基座 `098cde9` 零改动声明

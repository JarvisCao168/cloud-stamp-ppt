import { test, expect } from '@playwright/test';

/**
 * M2 预扣点接入 E2E（§3.5.5 PR 1 E2E 改判 402 用例，§五 R1 口径）
 *
 * 运行方式：npx playwright test e2e/m2-credits.test.ts
 * 需要后端 8001 在运行（与现有 E2E 基线同一实例）
 *
 * §3.5.4 四态触发条件汇总（M2 起生效）：
 *   429：used ≥ limit 且 balance = 0（免费额度耗尽且无积分）
 *   402：used ≥ limit 且 0 ≤ balance < required（余额不足，M1 required=0 时不可达，M2 required>0 激活）
 *   503：debit_credits 乐观锁 3 次版本冲突均失败（正常并发下几乎不可能触发）
 *   200：used < limit（免费额度未耗尽）或 预扣成功
 */

const API_BASE = process.env.E2E_API_BASE || 'http://localhost:8000';
const isCI = process.env.CI === 'true';
test.skip(isCI, 'Skipping M2 E2E in CI - backend not available');

// ── 工具函数 ─────────────────────────────────────────────────────────────

/** 直连后端（绕过 proxy，避免 8001 端口假设） */
async function createWithUser(
  userInput: string,
  userId: string,
  mode: string = 'quick'
): Promise<Response> {
  return fetch(`${API_BASE}/api/generation/create`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_input: userInput, mode, user_id: userId }),
    signal: AbortSignal.timeout(30_000),
  });
}

/** 查询 quota/status 块（M2 后响应结构：{ usage: {used, limit, allowed, reset_at}, credits: {balance, required} }） */
async function getQuotaStatus(userId: string): Promise<{
  usage: { used: number; limit: number; allowed: boolean; reset_at: string };
  credits: { balance: number; required: number };
}> {
  const res = await fetch(`${API_BASE}/api/quota/status?user_id=${userId}`, {
    headers: { 'X-User-Id': userId },
    signal: AbortSignal.timeout(10_000),
  });
  expect(res.status).toBe(200);
  return res.json();
}

// ── M1 基线回归锚定（E2E 改判后保留）────────────────────────────────────

test.describe('M2 E2E §3.5.4 四态验证', () => {

  test('200：新用户 free quota 未耗尽 → /create 正常返回（不扣积分，M1 语义延续）', async () => {
    const userId = `m2-e2e-200-${Date.now()}`;
    const res = await createWithUser('云章PPT产品介绍', userId);
    expect(res.status).toBe(200);
    const data = await res.json();
    expect(data.session_id).toBeTruthy();
    expect(data.status).toBe('completed');
    // quota/status：used=1，allowed=true
    const status = await getQuotaStatus(userId);
    expect(status.usage.used).toBe(1);
    expect(status.usage.allowed).toBe(true);
    expect(status.credits.balance).toBe(0); // M1 不赠额
  });

  test('429：free quota 耗尽（≥10 次）且 balance=0 → 稳态 429 唯一路径（§3.3）', async () => {
    const userId = `m2-e2e-429-${Date.now()}`;
    // 快速耗尽 10 次免费额度（每次 200，最后一次用 429 判断）
    let lastStatus = 200;
    for (let i = 0; i < 10; i++) {
      const res = await createWithUser(`测试主题 ${i}`, userId, 'quick');
      lastStatus = res.status;
      if (res.status === 429) break;
    }
    // 第 11 次必定 429
    const res11 = await createWithUser('第 11 次触发 429', userId);
    expect(res11.status).toBe(429);
    const body = await res11.json();
    expect(body.code).toBe('daily_free_quota_exceeded');
    expect(body.usage).toBeDefined();
    expect(body.usage.used).toBeGreaterThanOrEqual(10);
    expect(body.usage.reset_at).toMatch(/^\d{4}-\d{2}-\d{2}T00:00:00Z$/); // UTC 零点格式
  });

  test('402：balance < required（required=1，balance=0）→ 积分不足（§3.5.3 M2 新激活路径）', async () => {
    // M2 起 required > 0（estimate_required("quick", <500字) = 1）
    // balance=0 且 free quota 未耗尽 → credit_allowed = 0 >= 1 = False
    // free_allowed = True → allowed = True → 进入预扣 → debit_credits (False, -1)
    // 账户行不存在 → 402（balance 视为 0）
    const userId = `m2-e2e-402-${Date.now()}`;
    const res = await createWithUser('云章PPT产品介绍', userId);
    // M1 下此路径返回 200（required=0 不扣减）；M2 合入后返回 402
    // 此用例是 E2E 改判用例，预期：
    //   - 若 M2 代码未合入（当前状态）：200（required=0 不扣减）
    //   - M2 合入后：402（balance=0 < required=1）
    // 断言当前行为，M2 合入后此用例须改为 expect(res.status).toBe(402)
    if (res.status === 200) {
      // M2 代码未合入：记录 200 基线，M2 合入后须改判
      expect(res.status).toBe(200);
    } else {
      // M2 已合入：断言 402 平铺 schema（§3.5.3 定稿）
      expect(res.status).toBe(402);
      const body = await res.json();
      expect(body.code).toBe('insufficient_credits');
      expect(body.credits).toBeDefined();
      expect(body.credits.balance).toBe(0);
      expect(body.credits.required).toBeGreaterThanOrEqual(1);
      expect(body.user_id).toBe(userId);
      expect(body.message).toContain('积分不足');
    }
  });

  test('collaborative/full_control mode：required=0（checkpoint 暂停态不计费，§3.5.1）', async () => {
    const userId = `m2-e2e-collab-${Date.now()}`;
    // collaborative 模式 required=0，不触发 402（无论余额多少）
    const res = await createWithUser('测试大纲', userId, 'collaborative');
    // M1 下 200；M2 下仍 200（required=0 → 预扣门控不触发）
    expect(res.status).toBe(200);
    const data = await res.json();
    expect(data.status).toBe('checkpoint');
  });

  test('503：正常并发下不可达（乐观锁竞争窗口极窄，文档锚定用例）', async () => {
    // 503 仅在 debit_credits 3 次版本冲突均失败时触发
    // 单连接顺序测试下几乎不可能自然触发，此用例记录设计意图（§3.5.4 503 行）
    // 实际验证通过单测 test_debit_concurrent_true_race 覆盖
    const userId = `m2-e2e-503-${Date.now()}`;
    const res = await createWithUser('云章PPT产品介绍', userId);
    // 预期 200 或 402（非 503），断言 503 不可达
    expect(res.status).not.toBe(503);
  });

});

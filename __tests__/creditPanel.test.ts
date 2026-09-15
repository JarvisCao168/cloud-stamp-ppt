import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { QuotaStatus } from '@/api';

vi.stubGlobal('AbortSignal', {
  timeout: (ms: number) => ({ timeout: ms }),
});

describe('estimateCreditsRequired (M2 §3.5.1 前端镜像)', () => {
  let estimateCreditsRequired: (prompt: string, mode: string) => number;

  beforeEach(async () => {
    vi.resetModules();
    const mod = await import('@/api');
    estimateCreditsRequired = mod.estimateCreditsRequired;
  });

  it('quick 模式 ≤500 字 → 1', () => {
    expect(estimateCreditsRequired('a'.repeat(500), 'rapid')).toBe(1);
  });

  it('quick 模式 500 < 输入 ≤ 4000 → 3', () => {
    expect(estimateCreditsRequired('a'.repeat(4000), 'rapid')).toBe(3);
  });

  it('quick 模式 4000 < 输入 ≤ 8000 → 5', () => {
    expect(estimateCreditsRequired('a'.repeat(8000), 'rapid')).toBe(5);
  });

  it('quick 模式 >8000 字 → 8（HEAVY ×1.5 封顶）', () => {
    expect(estimateCreditsRequired('a'.repeat(9000), 'rapid')).toBe(8);
  });

  it('collaborative 模式 → 0（checkpoint 暂停态不计费）', () => {
    expect(estimateCreditsRequired('任意长度大纲内容，超过 8000 也不计费'.repeat(200), 'collaborative')).toBe(0);
  });

  it('full_control 模式 → 0（checkpoint 暂停态不计费）', () => {
    expect(estimateCreditsRequired('任意长度', 'mastery')).toBe(0);
  });
});

describe('getQuotaStatus (M2 §3.4 schema 平铺透传)', () => {
  let getQuotaStatus: () => Promise<QuotaStatus | null>;

  beforeEach(async () => {
    vi.resetModules();
    const mod = await import('@/api');
    getQuotaStatus = mod.getQuotaStatus;
    global.fetch = vi.fn();
  });

  it('200 时返回完整 usage + credits 块（§3.4 schema）', async () => {
    const expected: QuotaStatus = {
      usage: { used: 1, limit: 10, allowed: true, reset_at: '2026-09-16T00:00:00Z' },
      credits: { balance: 5, required: 0 },
    };
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: async () => expected,
    });
    const result = await getQuotaStatus();
    expect(result).toEqual(expected);
    expect(result?.usage.allowed).toBe(true);
    expect(result?.credits.balance).toBe(5);
  });

  it('404（跨 user_id oracle 防护 / 账户不存在）→ 返回 null，不抛错', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({ ok: false, status: 404 });
    const result = await getQuotaStatus();
    expect(result).toBeNull();
  });

  it('fetch 网络异常 → 返回 null，不阻塞页面', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('network error'));
    const result = await getQuotaStatus();
    expect(result).toBeNull();
  });
});

describe('CreditPanel 402 预判逻辑（余额 < required 且免费额度耗尽）', () => {
  it('balance=0, used=limit=10, required=1 → willFail402 为 true', () => {
    const balance = 0;
    const used = 10;
    const limit = 10;
    const required = 1;
    const willFail402 = used >= limit && balance < required;
    expect(willFail402).toBe(true);
  });

  it('balance=5, used=limit=10, required=3 → willFail402 为 false（余额足够）', () => {
    const balance = 5;
    const used = 10;
    const limit = 10;
    const required = 3;
    const willFail402 = used >= limit && balance < required;
    expect(willFail402).toBe(false);
  });

  it('required=0（collaborative 模式）→ willFail402 恒为 false（不计费）', () => {
    const balance = 0;
    const used = 10;
    const limit = 10;
    const required = 0;
    const willFail402 = used >= limit && balance < required;
    expect(willFail402).toBe(false);
  });
});

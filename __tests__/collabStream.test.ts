import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useCollabStream } from '@/components/collab/useCollabStream';

// ---- Mock EventSource for jsdom (jsdom doesn't provide EventSource) ----
type MockEventSource = {
  close: () => void;
  addEventListener: (type: string, cb: (e: { data: string }) => void) => void;
  onerror: (() => void) | null;
  onopen: (() => void) | null;
  readyState: number;
  _fire: (type: string, data: Record<string, unknown>) => void;
};

let _mockES: MockEventSource | null = null;

function _makeMockEventSource(): MockEventSource {
  const listeners: Record<string, ((e: { data: string }) => void)[]> = {};
  return {
    close: () => {},
    addEventListener: (type: string, cb: (e: { data: string }) => void) => {
      (listeners[type] = listeners[type] || []).push(cb);
    },
    onerror: null,
    onopen: null,
    readyState: 1,
    _fire: (type: string, data: Record<string, unknown>) => {
      const event = { data: JSON.stringify(data) };
      (listeners[type] || []).forEach((cb) => cb(event));
    },
  };
}

// 全局 mock：每个 EventSource 实例都是独立可驱动的对象
const esInstances: MockEventSource[] = [];
vi.stubGlobal(
  'EventSource',
  class MockEventSource {
    close = vi.fn();
    addEventListener = vi.fn((type: string, cb: (e: { data: string }) => void) => {
      // store per-instance listeners
      (this as any)._listeners ??= {};
      ((this as any)._listeners[type] ||= []).push(cb);
    });
    onerror: (() => void) | null = null;
    onopen: (() => void) | null = null;
    readyState = 1;
    _fire(type: string, data: Record<string, unknown>) {
      const event = { data: JSON.stringify(data) };
      ((this as any)._listeners?.[type] || []).forEach((cb: (e: { data: string }) => void) => cb(event));
    }
    constructor(_url: string) {
      esInstances.push(this as unknown as MockEventSource);
      _mockES = this as unknown as MockEventSource;
    }
  },
);

function getMockES(): MockEventSource {
  return _mockES!;
}

async function fireProgressEvents(events: Array<{ stage: string; detail: string; pages?: number }>) {
  await act(async () => {
    for (const ev of events) {
      getMockES()._fire('generation_progress', ev);
    }
  });
}

async function fireStatusEvent(status: string, message?: string) {
  await act(async () => {
    getMockES()._fire('collab_status', { status, message });
  });
}

async function firePingEvent() {
  await act(async () => {
    getMockES()._fire('ping', { ts: Date.now() });
  });
}

async function fireViewerJoined(viewerId: string, viewersTotal: number) {
  await act(async () => {
    getMockES()._fire('viewer_joined', {
      session_id: 'viewer-session',
      viewer_id: viewerId,
      ts: Date.now() / 1000,
      viewers_total: viewersTotal,
    });
  });
}

async function fireViewerLeft(viewerId: string, viewersTotal: number) {
  await act(async () => {
    getMockES()._fire('viewer_left', {
      session_id: 'viewer-session',
      viewer_id: viewerId,
      ts: Date.now() / 1000,
      viewers_total: viewersTotal,
    });
  });
}

async function firePresenceSnapshot(
  viewers: Array<{ viewer_id: string; last_seen_ts: number }>,
) {
  await act(async () => {
    getMockES()._fire('presence_snapshot', {
      session_id: 'viewer-session',
      viewers,
      ts: Date.now() / 1000,
    });
  });
}

describe('useCollabStream', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    _mockES = null;
    esInstances.length = 0;
  });

  afterEach(() => {
    _mockES = null;
    esInstances.length = 0;
  });

  // ================================================================
  // 测试 1：进度回放去重
  // ================================================================
  describe('进度回放去重', () => {
    it('长文本分页场景 10 页逐页到达，progressStages 全量保留', async () => {
      const { result } = renderHook(() => useCollabStream('test-session', true));
      await act(async () => { getMockES()._fire('snapshot', { session_id: 'test-session' }); });

      const pages = Array.from({ length: 10 }, (_, i) => ({
        stage: 'keep_original_progress',
        detail: `生成第 ${i + 1} 页`,
        pages: i + 1,
      }));
      await fireProgressEvents(pages);

      const keepCount = result.current.progressStages.filter(
        (s) => s === 'keep_original_progress',
      ).length;
      expect(keepCount).toBe(10);
      expect(result.current.progressPages).toBe(10);
    });

    it('重连后历史回放不重复插入（同指纹事件被去重）', async () => {
      const { result, rerender } = renderHook(
        ({ sid }: { sid: string }) => useCollabStream(sid, true),
        { initialProps: { sid: 'dedup-session' } },
      );

      const firstBatch = [
        { stage: 'keep_original_progress', detail: '第1页', pages: 1 },
        { stage: 'keep_original_progress', detail: '第2页', pages: 2 },
        { stage: 'keep_original_progress', detail: '第3页', pages: 3 },
      ];
      await act(async () => { getMockES()._fire('snapshot', { session_id: 'dedup-session' }); });
      await fireProgressEvents(firstBatch);
      expect(result.current.progressStages.filter((s) => s === 'keep_original_progress')).toHaveLength(3);

      // rerender 同 sessionId：processedProgressRef 保留（useRef 不随 rerender 重置）
      rerender({ sid: 'dedup-session' });
      // 模拟新 EventSource 实例（rerender 触发 useEffect 重建连接）
      await act(async () => { getMockES()._fire('snapshot', { session_id: 'dedup-session' }); });
      await fireProgressEvents(firstBatch); // 回放相同 3 条

      const keepCount = result.current.progressStages.filter(
        (s) => s === 'keep_original_progress',
      ).length;
      // 去重生效：仍为 3 条（未变成 6 条）
      expect(keepCount).toBe(3);
    });

    it('不同 stage 的进度事件全部保留（7 条 → 7 条）', async () => {
      const { result } = renderHook(() => useCollabStream('multi-stage', true));
      await act(async () => { getMockES()._fire('snapshot', { session_id: 'multi-stage' }); });

      const events = [
        { stage: 'intent', detail: '意图理解' },
        { stage: 'outline', detail: '大纲生成' },
        { stage: 'content', detail: '内容填充' },
        { stage: 'numbering', detail: '序号推荐' },
        { stage: 'style', detail: '样式匹配' },
        { stage: 'keep_original_progress', detail: '第1页', pages: 1 },
        { stage: 'keep_original_progress', detail: '第2页', pages: 2 },
      ];
      await fireProgressEvents(events);

      expect(result.current.progressStages).toHaveLength(7);
      expect(result.current.progressStages[0]).toBe('intent');
      expect(result.current.progressStages[4]).toBe('style');
      expect(result.current.progressStages[6]).toBe('keep_original_progress');
      expect(result.current.progressPages).toBe(2);
    });
  });

  // ================================================================
  // 测试 2：断线重连退避
  // ================================================================
  describe('断线重连退避', () => {
    it('onerror 后按指数退避调度，reconnectAttempts 依次 1→2→3', async () => {
      vi.useFakeTimers();
      const { result } = renderHook(() => useCollabStream('reconnect-session', true));
      await act(async () => { getMockES()._fire('snapshot', { session_id: 'reconnect-session' }); });

      // 断线 1：延迟 1000ms
      await act(async () => { getMockES().onerror!(); });
      expect(result.current.reconnectAttempts).toBe(1);
      expect(result.current.connected).toBe(false);
      await act(async () => { vi.advanceTimersByTime(1_000); });

      // 断线 2：延迟 2000ms
      await act(async () => { getMockES().onerror!(); });
      expect(result.current.reconnectAttempts).toBe(2);
      await act(async () => { vi.advanceTimersByTime(2_000); });

      // 断线 3：延迟 4000ms
      await act(async () => { getMockES().onerror!(); });
      expect(result.current.reconnectAttempts).toBe(3);
      await act(async () => { vi.advanceTimersByTime(4_000); });

      vi.useRealTimers();
    });

    it('重连成功后 reconnectAttempts 归零、connected 恢复', async () => {
      vi.useFakeTimers();
      const { result } = renderHook(() => useCollabStream('reset-session', true));
      await act(async () => { getMockES()._fire('snapshot', { session_id: 'reset-session' }); });

      // 断线
      await act(async () => { getMockES().onerror!(); });
      expect(result.current.reconnectAttempts).toBe(1);
      await act(async () => { vi.advanceTimersByTime(1_000); });

      // 模拟新连接成功（onopen）
      await act(async () => { getMockES().onopen!(); });
      expect(result.current.reconnectAttempts).toBe(0);
      expect(result.current.connected).toBe(true);

      vi.useRealTimers();
    });
  });

  // ================================================================
  // 测试 3：多订阅者并发 + 429 不受影响
  // ================================================================
  describe('多订阅者并发', () => {
    it('两个客户端同 session 并发订阅，事件序列完全一致', async () => {
      const events = [
        { stage: 'intent', detail: '意图理解' },
        { stage: 'outline', detail: '大纲生成' },
        { stage: 'content', detail: '内容填充' },
        { stage: 'numbering', detail: '序号推荐' },
        { stage: 'style', detail: '样式匹配' },
        { stage: 'keep_original_progress', detail: '第1页', pages: 1 },
        { stage: 'keep_original_progress', detail: '第2页', pages: 2 },
        { stage: 'keep_original_progress', detail: '第3页', pages: 3 },
      ];

      // 客户端 A
      const hookA = renderHook(() => useCollabStream('concurrent-session', true));
      await act(async () => { getMockES()._fire('snapshot', { session_id: 'concurrent-session' }); });
      await fireProgressEvents(events);
      const stagesA = hookA.result.current.progressStages;
      expect(stagesA).toHaveLength(8);
      expect(stagesA[0]).toBe('intent');
      expect(stagesA[7]).toBe('keep_original_progress');

      // 客户端 B（新 join，收到回放）
      const hookB = renderHook(() => useCollabStream('concurrent-session', true));
      await act(async () => { getMockES()._fire('snapshot', { session_id: 'concurrent-session' }); });
      await fireProgressEvents(events);
      const stagesB = hookB.result.current.progressStages;
      expect(stagesB).toHaveLength(8);
      expect(stagesB).toEqual(stagesA);
    });

    it('429 超限路径不影响 SSE 通道（quota 检查在 /create，非 SSE 端点）', async () => {
      const { result } = renderHook(() => useCollabStream('quota-session', true));
      await act(async () => { getMockES()._fire('snapshot', { session_id: 'quota-session' }); });

      // 模拟 429 后广播 collab_status
      await fireStatusEvent('quota_exceeded', '今日免费额度已用完（10/10）');
      expect(result.current.connected).toBe(true);
      expect(result.current.status).toBe('quota_exceeded');
      expect(result.current.statusMessage).toContain('免费额度');

      // SSE 通道仍正常工作
      await fireProgressEvents([{ stage: 'intent', detail: '意图理解' }]);
      expect(result.current.progressStages).toContain('intent');
    });
  });

  // ================================================================
  // 测试 4：M4 B 线 presence 3 事件（B 草案 v0.3 §一/§三 D1-D5）
  // ================================================================
  describe('B 线 presence 事件', () => {
    it('viewer_joined 更新 viewersTotal（取后端上报值，非本地加减）', async () => {
      const { result } = renderHook(() => useCollabStream('viewer-session', true));
      await act(async () => { getMockES()._fire('snapshot', { session_id: 'viewer-session' }); });

      expect(result.current.viewersTotal).toBeNull();
      await fireViewerJoined('anon-10.0.0.1', 1);
      expect(result.current.viewersTotal).toBe(1);
      await fireViewerJoined('anon-10.0.0.2', 2);
      expect(result.current.viewersTotal).toBe(2);
    });

    it('viewer_left 更新 viewersTotal 至离开后的在场数', async () => {
      const { result } = renderHook(() => useCollabStream('viewer-session', true));
      await act(async () => { getMockES()._fire('snapshot', { session_id: 'viewer-session' }); });

      await fireViewerJoined('anon-10.0.0.1', 1);
      await fireViewerJoined('anon-10.0.0.2', 2);
      expect(result.current.viewersTotal).toBe(2);

      await fireViewerLeft('anon-10.0.0.1', 1);
      expect(result.current.viewersTotal).toBe(1);
    });

    it('presence_snapshot 全量收敛 viewersTotal + lastPresenceTs（空快照不覆盖既有值）', async () => {
      const { result } = renderHook(() => useCollabStream('viewer-session', true));
      await act(async () => { getMockES()._fire('snapshot', { session_id: 'viewer-session' }); });

      // 先有一条增量事件上报
      await fireViewerJoined('anon-10.0.0.1', 1);
      expect(result.current.viewersTotal).toBe(1);

      // 全量快照下发（含 3 名在场观察者）
      await firePresenceSnapshot([
        { viewer_id: 'anon-10.0.0.1', last_seen_ts: 1726400000.0 },
        { viewer_id: 'anon-10.0.0.2', last_seen_ts: 1726400005.0 },
        { viewer_id: 'anon-10.0.0.3', last_seen_ts: 1726400010.0 },
      ]);
      expect(result.current.viewersTotal).toBe(3);
      expect(result.current.lastPresenceTs).not.toBeNull();

      // 空快照不覆盖既有 viewersTotal（降级保留前值，非本地加减）
      await firePresenceSnapshot([]);
      expect(result.current.viewersTotal).toBe(3);
    });

    it('未知事件名静默忽略（M4 升级前旧客户端回归面 0）', async () => {
      const { result } = renderHook(() => useCollabStream('viewer-session', true));
      await act(async () => { getMockES()._fire('snapshot', { session_id: 'viewer-session' }); });

      // 旧客户端未注册 presence 监听器时，EventSource 不触发 -> 前端不报错
      // 模拟新客户端收到未知事件名：分发闭包对未知 type 不产生任何 state 变更
      const es = getMockES();
      await act(async () => {
        es._fire('some_future_event', { anything: 'unknown' });
      });
      expect(result.current.viewersTotal).toBeNull();
      expect(result.current.lastPresenceTs).toBeNull();
      expect(result.current.connected).toBe(true);
    });
  });
});

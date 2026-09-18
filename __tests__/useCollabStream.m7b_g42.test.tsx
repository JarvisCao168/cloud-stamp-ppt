// M7-B G4-2 收尾验证项（sec2 content 3）：
// session-bound 双发兼容 user_id 字段前端回归（m3-b 草案 §九-补 ①（v0.4 勘误行））
// 基线锚点：HEAD 763d7e9（G4-1 出账），vitest ≥193 passed / 0 failed
// 本批次新增 4 条（user_id 字段缺失降级为「未上报」+ 双发兼容回归）
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useCollabStream } from "@/components/collab/useCollabStream";

class MockEventSource {
  static instances: MockEventSource[] = [];
  url: string;
  onopen: ((ev?: any) => void) | null = null;
  onerror: ((ev?: any) => void) | null = null;
  closed = false;
  listeners: Record<string, ((ev: any) => void)[]> = {};

  constructor(url: string) {
    this.url = url;
    MockEventSource.instances.push(this);
  }
  addEventListener(type: string, handler: (ev: any) => void) {
    (this.listeners[type] ||= []).push(handler);
  }
  removeEventListener(type: string, handler: (ev: any) => void) {
    this.listeners[type] = (this.listeners[type] || []).filter((h) => h !== handler);
  }
  close() {
    this.closed = true;
  }
  emit(type: string, data: unknown) {
    (this.listeners[type] || []).forEach((handler) => handler({ data: JSON.stringify(data) }));
  }
}

describe("M7-B G4-2 useCollabStream session-bound user_id 双发兼容回归", () => {
  beforeEach(() => {
    MockEventSource.instances = [];
    vi.stubGlobal("EventSource", MockEventSource);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("viewer_joined 含 user_id 字段（session-bound）时，viewersTotal 取上报值，不产生本地默认 1", () => {
    const { result } = renderHook(() => useCollabStream("sess-g42-bound"));
    const es = MockEventSource.instances[0];

    // session-bound 连接双发：viewer_id + user_id（同值，G4-1 终态锚点）
    act(() =>
      es.emit("viewer_joined", {
        session_id: "sess-g42-bound",
        viewer_id: "user-m7b-g42",
        user_id: "user-m7b-g42",
        ts: 1000,
        viewers_total: 3,
      })
    );

    // viewersTotal 始终取后端上报值（非本地加减，B 草案 R3）
    expect(result.current.viewersTotal).toBe(3);
    // user_id 字段存在且与 viewer_id 一致（session-bound 双发兼容）
    const event = result.current.lastEvent as { data: { viewer_id?: string; user_id?: string } };
    expect(event.data.viewer_id).toBe("user-m7b-g42");
    expect(event.data.user_id).toBe("user-m7b-g42");
  });

  it("viewer_joined 缺 user_id 字段（匿名/降级路径）时，viewersTotal 仍取上报值，不产生本地默认 1", () => {
    const { result } = renderHook(() => useCollabStream("sess-g42-anon"));
    const es = MockEventSource.instances[0];

    // 匿名连接（未登录）：仅 viewer_id + viewers_total，user_id 字段缺失
    act(() =>
      es.emit("viewer_joined", {
        session_id: "sess-g42-anon",
        viewer_id: "anon-10.0.0.1",
        ts: 2000,
        viewers_total: 1,
      })
    );

    // m3-b 草案 §九-补 ①：user_id 缺失 → 前端「未上报」降级，禁止默认 1
    // viewersTotal 仍取上报值 1（非本地加减，降级保留前值而非静默篡改）
    expect(result.current.viewersTotal).toBe(1);
    const event = result.current.lastEvent as { data: { viewer_id?: string; user_id?: string } };
    expect(event.data.viewer_id).toBe("anon-10.0.0.1");
    // user_id 字段缺失 → 降级为 undefined（「未上报」口径，非默认 1）
    expect(event.data.user_id).toBeUndefined();
  });

  it("viewer_left 含 user_id 字段（session-bound 断线）时，viewersTotal 回退至离开后在场数", () => {
    const { result } = renderHook(() => useCollabStream("sess-g42-left"));
    const es = MockEventSource.instances[0];

    // 先 join 2 人（session-bound 双发 user_id）
    act(() =>
      es.emit("viewer_joined", {
        session_id: "sess-g42-left",
        viewer_id: "user-g42-a",
        user_id: "user-g42-a",
        ts: 3000,
        viewers_total: 2,
      })
    );
    expect(result.current.viewersTotal).toBe(2);

    // 后 join 1 人（匿名，无 user_id）
    act(() =>
      es.emit("viewer_joined", {
        session_id: "sess-g42-left",
        viewer_id: "anon-10.0.0.2",
        ts: 3001,
        viewers_total: 3,
      })
    );
    expect(result.current.viewersTotal).toBe(3);

    // session-bound 连接断线（双发 user_id 保留至 left 帧）
    act(() =>
      es.emit("viewer_left", {
        session_id: "sess-g42-left",
        viewer_id: "user-g42-a",
        user_id: "user-g42-a",
        ts: 3002,
        viewers_total: 2,
      })
    );
    expect(result.current.viewersTotal).toBe(2);
    const event = result.current.lastEvent as { data: { viewer_id?: string; user_id?: string } };
    expect(event.data.viewer_id).toBe("user-g42-a");
    expect(event.data.user_id).toBe("user-g42-a");
  });

  it("presence_snapshot 全量收敛（session-bound + 匿名混合观众）时，viewersTotal = viewers 数组长度", () => {
    const { result } = renderHook(() => useCollabStream("sess-g42-snap"));
    const es = MockEventSource.instances[0];

    // 全量快照：1 个 session-bound + 1 个匿名（B 线 S1 既有口径）
    act(() =>
      es.emit("presence_snapshot", {
        session_id: "sess-g42-snap",
        viewers: [
          { viewer_id: "user-g42-b", last_seen_ts: 4000 },
          { viewer_id: "anon-10.0.0.3", last_seen_ts: 4001 },
        ],
        ts: 4002,
      })
    );

    expect(result.current.viewersTotal).toBe(2);
    expect(result.current.lastPresenceTs).toBe(4002000);

    // 空快照不覆盖既有 viewersTotal（降级保留前值，非本地加减）
    act(() =>
      es.emit("presence_snapshot", {
        session_id: "sess-g42-snap",
        viewers: [],
        ts: 4003,
      })
    );
    expect(result.current.viewersTotal).toBe(2);
  });
});

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
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

describe("useCollabStream M4 B line presence", () => {
  beforeEach(() => {
    MockEventSource.instances = [];
    vi.stubGlobal("EventSource", MockEventSource);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("handles viewer_joined, viewer_left, presence_snapshot without local arithmetic", async () => {
    const { result } = renderHook(() => useCollabStream("sess-1"));
    await waitFor(() => expect(MockEventSource.instances.length).toBe(1));
    const es = MockEventSource.instances[0];
    expect(es.url).toContain("/api/collab/stream?session_id=sess-1");

    act(() => es.emit("viewer_joined", { session_id: "sess-1", viewer_id: "v1", ts: 123, viewers_total: 3 }));
    expect(result.current.viewersTotal).toBe(3);

    act(() => es.emit("viewer_left", { session_id: "sess-1", viewer_id: "v1", ts: 124, viewers_total: 2 }));
    expect(result.current.viewersTotal).toBe(2);

    act(() => es.emit("presence_snapshot", { session_id: "sess-1", viewers: [{ viewer_id: "v2", last_seen_ts: 125 }, { viewer_id: "v3", last_seen_ts: 125 }], ts: 125 }));
    expect(result.current.viewersTotal).toBe(2);
    expect(result.current.lastPresenceTs).toBe(125000);
  });

  it("keeps previous presence value when new payload omits viewers_total", () => {
    const { result } = renderHook(() => useCollabStream("sess-2"));
    const es = MockEventSource.instances[0];
    act(() => es.emit("viewer_joined", { session_id: "sess-2", viewer_id: "v1", ts: 100, viewers_total: 5 }));
    act(() => es.emit("viewer_left", { session_id: "sess-2", viewer_id: "v1", ts: 101 }));
    expect(result.current.viewersTotal).toBe(5);
  });

  it("does not overwrite viewersTotal with empty presence_snapshot", () => {
    const { result } = renderHook(() => useCollabStream("sess-3"));
    const es = MockEventSource.instances[0];
    act(() => es.emit("viewer_joined", { session_id: "sess-3", viewer_id: "v1", ts: 1, viewers_total: 7 }));
    act(() => es.emit("presence_snapshot", { session_id: "sess-3", viewers: [], ts: 2 }));
    expect(result.current.viewersTotal).toBe(7);
    expect(result.current.lastPresenceTs).toBe(2000);
  });

  it("respects disabled sessionId null without opening EventSource", async () => {
    renderHook(() => useCollabStream(null));
    expect(MockEventSource.instances.length).toBe(0);
  });
});

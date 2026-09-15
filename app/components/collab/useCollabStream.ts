// 协作 MVP 前端组件（文件级隔离：本目录新文件，不碰移动端/长文本相关文件）
// useCollabStream: SSE 实时进度 hook（含断线重连退避 + 历史回放去重 + B 线 presence 3 事件）
// CollabStatusPanel: 协作状态面板
"use client";

import { useEffect, useRef, useState, useCallback } from "react";

/** SSE 事件协议（与后端 GET /api/collab/stream 对齐）
 *  M4 B 线新增 3 事件（独立 event 命名空间，B 草案 v0.3 定稿 §一/§三 D1-D5，零 schema 重叠）：
 *    viewer_joined      观察者 join 回放完成后首帧（data: {session_id, viewer_id, ts, viewers_total}）
 *    viewer_left        观察者断线 30s 超时无重连（data: {session_id, viewer_id, ts, viewers_total}）
 *    presence_snapshot  新 join 者全量在场快照（data: {session_id, viewers: [{viewer_id, last_seen_ts}], ts}）
 *  generation_progress.stage 枚举（锁定版）
 *  6 值：intent / outline / content / numbering / style / keep_original
 *  扩展值：keep_original_progress（含 pages 计数，长文本分段进度专用）
 *  Phase 4 预留：slide_update / generation_complete（当前无生产端）
 */
export type CollabStage =
  | "intent"
  | "outline"
  | "content"
  | "numbering"
  | "style"
  | "keep_original"
  | "keep_original_progress";

export type CollabEvent =
  | { type: "snapshot"; data: { session_id: string; mode?: string; keep_original?: boolean; slides_count?: number } }
  | {
      type: "generation_progress";
      data: {
        stage: CollabStage;
        detail: string;
        /** 长文本分段进度：第几页 */
        pages?: number;
        /** 可选扩展字段（Phase 4 启用） */
        percent?: number;
        currentSlide?: number;
        message?: string;
      };
    }
  | { type: "collab_status"; data: { status: string; message?: string } }
  | { type: "ping"; data: { ts: number } }
  // M4 B 线新增（独立 event 命名空间，schema 按 B 草案 §一 1.2 冻结；只增不删不改义，
  // 未知字段客户端忽略，缺失新字段降级为「未上报」而非报错）
  | { type: "viewer_joined"; data: { session_id: string; viewer_id: string; ts: number; viewers_total: number } }
  | { type: "viewer_left"; data: { session_id: string; viewer_id: string; ts: number; viewers_total: number } }
  | { type: "presence_snapshot"; data: { session_id: string; viewers: { viewer_id: string; last_seen_ts: number }[]; ts: number } };

export interface CollabStreamState {
  connected: boolean;
  lastEvent: CollabEvent | null;
  progressStages: string[];
  progressPages: number | null;
  status: string | null;
  statusMessage: string | null;
  /** 重连次数（0 = 首次连接） */
  reconnectAttempts: number;
  // M4 B 线 presence 字段（D2：新增 2 字段，既有字段零改动；全缺失 → null → 面板「未上报」降级）
  /** 最近一次 viewer_joined/viewer_left/presence_snapshot 上报的在场连接数（null = 未上报） */
  viewersTotal: number | null;
  /** 最近一次 presence_snapshot 的时间戳（ms，null = 未上报） */
  lastPresenceTs: number | null;
}

const RECONNECT_BASE_MS = 1_000;
const RECONNECT_MAX_MS = 30_000;
const MAX_RECONNECT_ATTEMPTS = 10;

function _backoffMs(attempt: number): number {
  return Math.min(RECONNECT_BASE_MS * 2 ** attempt, RECONNECT_MAX_MS);
}

/**
 * 订阅指定 session_id 的协作 SSE 流。
 * API base 读全局 window.__COLLAB_API_BASE__ 或 NEXT_PUBLIC_API_BASE，默认 http://localhost:8001
 *
 * 健壮性：
 * - 断线自动重连（指数退避，最多 MAX_RECONNECT_ATTEMPTS 次）
 * - 历史回放去重：用 (stage, pages, detail) 指纹防止 join 时回放造成重复插入
 * - ping 心跳更新 lastPingAt，面板可据此显示"心跳正常"
 */
export function useCollabStream(sessionId: string | null, enabled = true) {
  const [state, setState] = useState<CollabStreamState>({
    connected: false,
    lastEvent: null,
    progressStages: [],
    progressPages: null,
    status: null,
    statusMessage: null,
    reconnectAttempts: 0,
    viewersTotal: null,
    lastPresenceTs: null,
  });
  const [lastPingAt, setLastPingAt] = useState<number | null>(null);

  const esRef = useRef<EventSource | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const processedProgressRef = useRef<Set<string>>(new Set());

  const closeConnection = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (!sessionId || !enabled) return;

    const base =
      (typeof window !== "undefined" &&
        (window as any).__COLLAB_API_BASE__) ||
      process.env.NEXT_PUBLIC_API_BASE ||
      "http://localhost:8001";
    const url = `${base.replace(/\/$/, "")}/api/collab/stream?session_id=${encodeURIComponent(sessionId)}`;

    function connect() {
      const es = new EventSource(url);
      esRef.current = es;

      const onEvent = (type: CollabEvent["type"]) => (e: MessageEvent) => {
        const data = JSON.parse(e.data) as Record<string, unknown>;
        const event: CollabEvent = { type, data } as CollabEvent;
        setState((prev) => {
          const next = { ...prev, lastEvent: event, connected: true };
          if (type === "generation_progress") {
            const d = data as Record<string, unknown>;
            const fingerprint = `${d.stage}|${d.pages ?? ""}|${d.detail ?? ""}`;
            if (!processedProgressRef.current.has(fingerprint)) {
              processedProgressRef.current.add(fingerprint);
              next.progressStages = [...prev.progressStages, d.stage as string];
              if (typeof d.pages === "number") {
                next.progressPages = d.pages;
              }
            }
          }
          if (type === "collab_status") {
            next.status = data.status as string;
            next.statusMessage = (data.message as string | undefined) ?? null;
          }
          // M4 B 线 presence 分发（D3：不复用 processedProgressRef 去重指纹，presence 事件
          // 按 viewer 维度天然幂等；只写上报值，缺失字段降级保留前值而非本地加减）
          if (type === "viewer_joined" || type === "viewer_left") {
            const d = data as { viewer_id?: string; viewers_total?: number };
            // viewersTotal 始终取后端上报值（= 活跃连接数，非去重用户数，见 B 草案 R3）；
            // 缺失 → 保留前值（降级为「未上报」而非本地加减）
            if (typeof d.viewers_total === "number") next.viewersTotal = d.viewers_total;
          }
          if (type === "presence_snapshot") {
            const d = data as {
              viewers?: { viewer_id: string; last_seen_ts: number }[];
              ts?: number;
            };
            // ts 为 epoch 秒（后端 time.time() 口径），面板展示需 ms，统一 ×1000
            if (typeof d.ts === "number") next.lastPresenceTs = Math.round(d.ts * 1000);
            // presence_snapshot 在场连接数 = 快照 viewers 数组长度（上报值，非本地加减）；
            // 空快照不覆盖既有 viewersTotal
            if (Array.isArray(d.viewers) && d.viewers.length > 0) next.viewersTotal = d.viewers.length;
          }
          return next;
        });
        if (type === "ping") {
          setLastPingAt(Date.now());
        }
      };

      es.addEventListener("snapshot", onEvent("snapshot"));
      es.addEventListener("generation_progress", onEvent("generation_progress"));
      es.addEventListener("collab_status", onEvent("collab_status"));
      es.addEventListener("ping", onEvent("ping"));
      // M4 B 线 D4：新增 3 监听器注册（既有 4 行零改动）
      es.addEventListener("viewer_joined", onEvent("viewer_joined"));
      es.addEventListener("viewer_left", onEvent("viewer_left"));
      es.addEventListener("presence_snapshot", onEvent("presence_snapshot"));

      es.onerror = () => {
        es.close();
        esRef.current = null;
        setState((prev) => ({ ...prev, connected: false }));
        if (reconnectAttemptsRef.current >= MAX_RECONNECT_ATTEMPTS) return;
        reconnectAttemptsRef.current += 1;
        const attempt = reconnectAttemptsRef.current;
        const delay = _backoffMs(attempt);
        setState((prev) => ({ ...prev, reconnectAttempts: attempt }));
        reconnectTimerRef.current = setTimeout(() => {
          reconnectTimerRef.current = null;
          connect();
        }, delay);
      };

      es.onopen = () => {
        reconnectAttemptsRef.current = 0;
        setState((prev) => ({ ...prev, reconnectAttempts: 0, connected: true }));
      };
    }

    connect();

    return () => {
      closeConnection();
    };
  }, [sessionId, enabled, closeConnection]);

  return { ...state, lastPingAt };
}

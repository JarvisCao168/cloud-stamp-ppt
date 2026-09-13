// 协作 MVP 前端组件（文件级隔离：本目录新文件，不碰移动端/长文本相关文件）
// useCollabStream: SSE 实时进度 hook（含断线重连退避 + 历史回放去重）
// CollabStatusPanel: 协作状态面板
"use client";

import { useEffect, useRef, useState, useCallback } from "react";

/** SSE 事件协议（与后端 GET /api/collab/stream 对齐） */
/** generation_progress.stage 枚举（锁定版）
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
  | { type: "ping"; data: { ts: number } };

export interface CollabStreamState {
  connected: boolean;
  lastEvent: CollabEvent | null;
  progressStages: string[];
  progressPages: number | null;
  status: string | null;
  statusMessage: string | null;
  /** 重连次数（0 = 首次连接） */
  reconnectAttempts: number;
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

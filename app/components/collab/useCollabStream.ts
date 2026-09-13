// 协作 MVP 前端组件（文件级隔离：本目录新文件，不碰移动端/长文本相关文件）
// useCollabStream: SSE 实时进度 hook
// CollabStatusPanel: 协作状态面板
"use client";

import { useEffect, useRef, useState } from "react";

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
  status: string | null;
  statusMessage: string | null;
}

/**
 * 订阅指定 session_id 的协作 SSE 流。
 * API base 读全局 window.__COLLAB_API_BASE__ 或 NEXT_PUBLIC_API_BASE，默认 http://localhost:8001
 */
export function useCollabStream(sessionId: string | null, enabled = true) {
  const [state, setState] = useState<CollabStreamState>({
    connected: false,
    lastEvent: null,
    progressStages: [],
    status: null,
    statusMessage: null,
  });
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!sessionId || !enabled) return;
    const base =
      (typeof window !== "undefined" &&
        (window as any).__COLLAB_API_BASE__) ||
      process.env.NEXT_PUBLIC_API_BASE ||
      "http://localhost:8001";
    const url = `${base.replace(/\/$/, "")}/api/collab/stream?session_id=${encodeURIComponent(sessionId)}`;
    const es = new EventSource(url);
    esRef.current = es;

    const onEvent = (type: CollabEvent["type"]) => (e: MessageEvent) => {
      const data = JSON.parse(e.data) as Record<string, unknown>;
      const event: CollabEvent = { type, data } as CollabEvent;
      setState((prev) => {
        const next = { ...prev, lastEvent: event, connected: true };
        if (type === "generation_progress") {
          next.progressStages = [...prev.progressStages, data.stage as string];
        }
        if (type === "collab_status") {
          next.status = data.status as string;
          next.statusMessage = (data.message as string | undefined) ?? null;
        }
        return next;
      });
    };

    es.addEventListener("snapshot", onEvent("snapshot"));
    es.addEventListener("generation_progress", onEvent("generation_progress"));
    es.addEventListener("collab_status", onEvent("collab_status"));
    es.addEventListener("ping", onEvent("ping"));
    es.onerror = () => setState((prev) => ({ ...prev, connected: false }));

    return () => {
      es.close();
      esRef.current = null;
    };
  }, [sessionId, enabled]);

  return state;
}

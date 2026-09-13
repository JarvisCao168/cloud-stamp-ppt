// 协作 MVP: 协作状态面板组件（放在 components/collab/*，文件级隔离）
// 展示 SSE 实时进度阶段（含进度条）、心跳 ping 指示、断线错误态样式
"use client";

import { useState } from "react";
import { useCollabStream } from "./useCollabStream";

const STAGE_LABELS: Record<string, string> = {
  intent: "意图理解",
  outline: "大纲生成",
  content: "内容填充",
  numbering: "序号样式推荐",
  style: "样式匹配",
  keep_original: "保持原文解析分页",
  keep_original_progress: "保持原文分页中",
};

const STAGE_COLORS: Record<string, string> = {
  intent: "bg-blue-500",
  outline: "bg-indigo-500",
  content: "bg-purple-500",
  numbering: "bg-cyan-500",
  style: "bg-pink-500",
  keep_original: "bg-amber-500",
  keep_original_progress: "bg-amber-600",
};

export function CollabStatusPanel({ sessionId }: { sessionId: string | null }) {
  const {
    connected,
    progressStages,
    progressPages,
    status,
    statusMessage,
    reconnectAttempts,
    lastPingAt,
  } = useCollabStream(sessionId, !!sessionId);

  const [showPing, setShowPing] = useState(false);

  if (!sessionId) {
    return (
      <div className="p-4 text-sm text-slate-500">
        协作面板：无活动会话
      </div>
    );
  }

  // 心跳指示：lastPingAt 在 35s 内视为"心跳正常"
  const pingHealthy =
    lastPingAt !== null && Date.now() - lastPingAt < 35_000;

  // 进度条：progressStages.length 是已完成阶段数，总阶段数取 6（标准流水线）
  // 长文本模式下以 progressPages 展示页码进度
  const totalStages = 6;
  const doneStages = Math.min(progressStages.length, totalStages);
  const progressPct = totalStages > 0 ? Math.round((doneStages / totalStages) * 100) : 0;

  return (
    <div
      className={`rounded-lg border p-4 text-sm ${
        connected
          ? "border-slate-200 bg-white"
          : "border-rose-300 bg-rose-50"
      }`}
      data-testid="collab-status-panel"
    >
      {/* 连接状态指示 */}
      <div className="mb-2 flex items-center gap-2">
        <span
          className={`inline-block h-2 w-2 rounded-full ${
            connected ? "bg-emerald-500" : "bg-rose-400 animate-pulse"
          }`}
          data-testid="collab-connection-dot"
        />
        <span
          className={`font-medium ${
            connected ? "text-slate-700" : "text-rose-700"
          }`}
        >
          {connected ? "协作实时状态" : "已断开连接"}
        </span>

        {/* 心跳 ping 指示 */}
        {connected && lastPingAt !== null && (
          <span
            className={`ml-auto flex items-center gap-1 rounded-full px-2 py-0.5 text-xs ${
              pingHealthy
                ? "bg-emerald-100 text-emerald-700"
                : "bg-amber-100 text-amber-700"
            }`}
            data-testid="collab-ping-indicator"
            title={
              pingHealthy
                ? "心跳正常"
                : "心跳超时（35s 内无 ping）"
            }
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                pingHealthy ? "bg-emerald-500" : "bg-amber-500"
              }`}
            />
            {pingHealthy ? "心跳正常" : "心跳超时"}
          </span>
        )}
      </div>

      {/* 重连提示 */}
      {reconnectAttempts > 0 && (
        <div
          className="mb-2 rounded bg-amber-50 px-3 py-1 text-xs text-amber-700"
          data-testid="collab-reconnect-notice"
        >
          正在重连（第 {reconnectAttempts} 次）…
        </div>
      )}

      {/* 状态消息 */}
      {status && (
        <div className="mb-2 text-slate-600">
          状态：<span className="font-semibold">{status}</span>
          {statusMessage ? ` — ${statusMessage}` : ""}
        </div>
      )}

      {/* 进度阶段列表 */}
      {progressStages.length > 0 ? (
        <div data-testid="collab-progress-section">
          {/* 进度条 */}
          <div className="mb-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
            <div
              className={`h-full rounded-full transition-all duration-300 ${STAGE_COLORS[progressStages[progressStages.length - 1]] ?? "bg-slate-500"}`}
              style={{ width: `${progressPct}%` }}
              data-testid="collab-progress-bar"
            />
          </div>
          <div className="mb-1 flex items-center justify-between text-xs text-slate-400">
            <span>进度 {progressPct}%</span>
            {progressPages !== null && (
              <span data-testid="collab-progress-pages">
                第 {progressPages} 页
              </span>
            )}
          </div>
          <ol className="list-decimal pl-5 text-slate-600">
            {progressStages.map((stage, i) => (
              <li
                key={i}
                data-testid={`progress-stage-${i}`}
                className={`flex items-center gap-1.5 ${
                  i === progressStages.length - 1
                    ? "font-semibold text-slate-800"
                    : "text-slate-500"
                }`}
              >
                <span
                  className={`h-1.5 w-1.5 rounded-full ${
                    STAGE_COLORS[stage] ?? "bg-slate-400"
                  }`}
                />
                {STAGE_LABELS[stage] ?? stage}
              </li>
            ))}
          </ol>
        </div>
      ) : connected ? (
        <p className="text-slate-400">等待进度事件…</p>
      ) : (
        <p className="text-rose-600">SSE 通道未连接，等待自动重连…</p>
      )}
    </div>
  );
}

// 协作 MVP: 协作状态面板组件（放在 components/collab/*，文件级隔离）
// 展示 SSE 实时进度阶段、当前协作状态、连接指示
"use client";

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

export function CollabStatusPanel({ sessionId }: { sessionId: string | null }) {
  const { connected, progressStages, status, statusMessage } = useCollabStream(
    sessionId,
    !!sessionId
  );

  if (!sessionId) {
    return (
      <div className="p-4 text-sm text-slate-500">
        协作面板：无活动会话
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm">
      <div className="mb-2 flex items-center gap-2">
        <span
          className={`inline-block h-2 w-2 rounded-full ${
            connected ? "bg-emerald-500" : "bg-rose-400"
          }`}
        />
        <span className="font-medium text-slate-700">协作实时状态</span>
      </div>
      {status && (
        <div className="mb-2 text-slate-600">
          状态：<span className="font-semibold">{status}</span>
          {statusMessage ? ` — ${statusMessage}` : ""}
        </div>
      )}
      {progressStages.length > 0 ? (
        <ol className="list-decimal pl-5 text-slate-600">
          {progressStages.map((stage, i) => (
            <li key={i} data-testid={`progress-stage-${i}`}>
              {STAGE_LABELS[stage] ?? stage}
            </li>
          ))}
        </ol>
      ) : (
        <p className="text-slate-400">等待进度事件…</p>
      )}
    </div>
  );
}

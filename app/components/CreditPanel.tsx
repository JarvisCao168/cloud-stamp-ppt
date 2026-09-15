// M2 积分面板组件（PR 2 前端范围，Hermes 开笔令锁定）
// 对接 §3.4 schema（GET /api/quota/status 平铺透传）+ §3.5.1 前端估算（estimateCreditsRequired）
// 文件级隔离：本目录新文件，不改动 CollabStatusPanel / 移动端 / 长文本相关组件
"use client";

import { useEffect, useState } from "react";
import { getQuotaStatus, estimateCreditsRequired, QuotaStatus } from "@/api";
import type { PresentationMode } from "@/types";

interface CreditPanelProps {
  /** 当前输入框的 prompt 文本（用于估算"本次预计消耗积分"） */
  prompt?: string;
  /** 当前选择的生成模式（用于估算"本次预计消耗积分"） */
  mode?: PresentationMode;
}

/**
 * 积分/额度状态面板：
 * - 免费额度计数（used/limit）+ 重置时间（UTC 零点，本地时区展示）
 * - 积分账户余额（balance）+ 本次预计消耗（estimateCreditsRequired，与后端 §3.5.1 同口径）
 * - 余额 < 本次预计消耗 且免费额度已耗尽 → 高亮"积分不足"提示（402 预判）
 *
 * M2 起 required > 0，此面板作为 402 提前预警入口，避免用户提交后才收到 402。
 */
export function CreditPanel({ prompt = "", mode = "rapid" }: CreditPanelProps) {
  const [status, setStatus] = useState<QuotaStatus | null>(null);
  const [loading, setLoading] = useState(true);

  const required = estimateCreditsRequired(prompt, mode);
  const balance = status?.credits.balance ?? 0;
  const used = status?.usage.used ?? 0;
  const limit = status?.usage.limit ?? 10;
  const resetAtLocal = status?.usage.reset_at
    ? new Date(status.usage.reset_at).toLocaleString()
    : null;

  // 402 预判：免费额度已用完 + 余额不足 required → 提示用户
  const willFail402 = status !== null && used >= limit && balance < required;

  useEffect(() => {
    let cancelled = false;
    getQuotaStatus().then((s) => {
      if (!cancelled) {
        setStatus(s);
        setLoading(false);
      }
    });
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <div className="p-3 text-xs text-slate-400" data-testid="credit-panel-loading">
        积分状态加载中…
      </div>
    );
  }

  return (
    <div
      className={`rounded-lg border p-3 text-sm ${
        willFail402 ? "border-rose-300 bg-rose-50" : "border-slate-200 bg-white"
      }`}
      data-testid="credit-panel"
    >
      <div className="flex items-center justify-between gap-2">
        <span className="font-medium text-slate-700">免费额度</span>
        <span className="text-slate-500">
          {used}/{limit}
          {resetAtLocal ? ` · ${resetAtLocal} 重置` : ""}
        </span>
      </div>
      <div className="mt-1 flex items-center justify-between gap-2">
        <span className="font-medium text-slate-700">积分余额</span>
        <span className="text-slate-500">{balance}</span>
      </div>
      {required > 0 && (
        <div className="mt-1 flex items-center justify-between gap-2">
          <span className="font-medium text-slate-700">本次预计消耗</span>
          <span className={`text-slate-500 ${willFail402 ? "text-rose-600" : ""}`}>
            {required}
          </span>
        </div>
      )}
      {willFail402 && (
        <p className="mt-2 text-xs text-rose-600" data-testid="credit-panel-402-warning">
          免费额度已用完且积分不足（需 {required}，余额 {balance}），提交将返回 402，请充值或明日重试
        </p>
      )}
    </div>
  );
}

export default CreditPanel;

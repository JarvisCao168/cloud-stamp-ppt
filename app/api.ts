import { PresentationMode, SlideData } from '@/types';

/**
 * 前端模式 → 后端 API 模式 映射
 * 前端: rapid / collaborative / mastery
 * 后端: quick / collaborative / full_control
 */
const MODE_MAP: Record<PresentationMode, string> = {
  rapid: 'quick',
  collaborative: 'collaborative',
  mastery: 'full_control',
};

/**
 * 客户端指纹：未登录时用 localStorage 持久化的随机 ID 做每日免费额度计数主体
 * （后端 user_id 字段；缺失时后端兜底为 anon-{IP}，指纹可让同一浏览器跨页面持续计数）
 */
function getClientFingerprint(): string {
  if (typeof localStorage === 'undefined') return 'anon-web';
  let id = localStorage.getItem('yz-client-id');
  if (!id) {
    id = `client-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
    localStorage.setItem('yz-client-id', id);
  }
  return id;
}

export interface GenerationResult {
  session_id: string;
  status: 'completed' | 'checkpoint';
  message: string;
  data?: {
    slides?: SlideData[];
    intent?: Record<string, unknown>;
    style?: Record<string, unknown>;
  };
  checkpoints?: Array<{
    id: string;
    title: string;
    description: string;
    data?: Record<string, unknown>;
  }>;
}

export interface CheckpointAction {
  session_id: string;
  checkpoint_id: string;
  action: 'confirm' | 'edit' | 'regenerate' | 'select';
  data?: Record<string, unknown>;
}

/**
 * M2 积分/额度查询（GET /api/quota/status，§3.4 schema 平铺透传）
 *
 * 返回当前用户（localStorage 指纹 → X-User-Id）的 usage + credits 块：
 * - usage: 每日免费额度计数（used/limit/allowed/reset_at，UTC 零点）
 * - credits: 积分账户（balance/required；M2 起 required 随场景 0/1/3/5/6/8）
 *
 * 跨 user_id 查询一律 404（oracle 防护），不抛错，前端按"无数据"处理。
 */
export interface QuotaStatus {
  usage: { used: number; limit: number; allowed: boolean; reset_at: string };
  credits: { balance: number; required: number };
}

export async function getQuotaStatus(): Promise<QuotaStatus | null> {
  try {
    const res = await fetch('/api/quota/status', {
      method: 'GET',
      headers: { 'X-User-Id': getClientFingerprint() },
      signal: AbortSignal.timeout(5_000),
    });
    if (!res.ok) return null; // 404 等：前端按无账户处理，不阻塞页面
    return (await res.json()) as QuotaStatus;
  } catch {
    return null;
  }
}

/**
 * M2 预扣点场景所需积分估算（前端镜像 §3.5.1 路由映射，供 CreditPanel 展示"本次预计消耗"）
 * 与后端 quota.py estimate_required 同口径（quick × 字数档 / multimodal / collab·full_control=0）
 */
export function estimateCreditsRequired(prompt: string, mode: PresentationMode): number {
  const backendMode = MODE_MAP[mode];
  if (backendMode === 'collaborative' || backendMode === 'full_control') return 0;
  const len = prompt.length;
  if (len <= 500) return 1;
  if (len <= 4000) return 3;
  if (len <= 8000) return 5;
  return 8;
}

/**
 * 调用后端生成接口
 */
export async function generateSlides(
  prompt: string,
  mode: PresentationMode,
  options?: { keepOriginal?: boolean }
): Promise<GenerationResult> {
  const body: Record<string, unknown> = {
    user_input: prompt,
    mode: MODE_MAP[mode],
    keep_original: options?.keepOriginal || false,
    user_id: getClientFingerprint(),
  };
  const response = await fetch('/api/generation/create', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(30_000),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: response.statusText }));
    // 429 免费额度耗尽：后端返回结构化 detail，直接透传中文文案
    if (response.status === 429 && typeof err.detail === 'object' && err.detail !== null) {
      const d = err.detail as Record<string, unknown>;
      throw new Error(String(d.message || `今日免费额度已用完（${d.used}/${d.limit}）`));
    }
    throw new Error(typeof err.detail === 'string' ? err.detail : `生成失败 (HTTP ${response.status})`);
  }

  return response.json();
}

/**
 * 查询会话状态（含检查点进度）
 */
export async function getSession(sessionId: string): Promise<Record<string, unknown>> {
  const response = await fetch(`/api/generation/session/${encodeURIComponent(sessionId)}`);
  if (!response.ok) {
    throw new Error(`获取会话失败 (HTTP ${response.status})`);
  }
  return response.json();
}

/**
 * 提交检查点决策，推进流水线
 */
export async function submitCheckpointAction(action: CheckpointAction): Promise<{
  status: string;
  session_id: string;
  next_checkpoint?: string;
}> {
  const response = await fetch(
    `/api/generation/checkpoint/${action.session_id}/${action.checkpoint_id}/action`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(action),
    }
  );
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || '检查点操作失败');
  }
  return response.json();
}

/**
 * 获取后端检查点流程状态
 */
export async function getCheckpointFlow(sessionId: string): Promise<{
  session_id: string;
  mode: string;
  current_checkpoint?: string;
  checkpoints: Array<{
    id: string;
    title: string;
    description: string;
    status: string;
    user_action?: string;
    completed_at?: number;
  }>;
}> {
  const response = await fetch(`/api/checkpoints/flow/${encodeURIComponent(sessionId)}`);
  if (!response.ok) {
    throw new Error(`获取检查点流程失败 (HTTP ${response.status})`);
  }
  return response.json();
}

/**
 * 导出演示文稿
 */
export interface ExportOptions {
  format: 'pptx' | 'pdf' | 'png' | 'html';
  title?: string;
  quality?: 'hd' | 'sd';
  numberingStyleId?: string;
}

export async function exportPresentation(
  sessionId: string,
  options: ExportOptions
): Promise<{ filename: string; url: string; format: string; size_bytes?: number }> {
  const body: Record<string, unknown> = {
    session_id: sessionId,
    format: options.format,
    title: options.title || '演示文稿',
    quality: options.quality || 'hd',
    ...(options.numberingStyleId && { numbering_style_id: options.numberingStyleId }),
  };

  const response = await fetch(`/api/export/${options.format}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(60_000),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(err.detail || `导出失败 (HTTP ${response.status})`);
  }

  return response.json();
}


/**
 * 获取序号样式列表
 */
export interface NumberingStyle {
  id: string;
  name: string;
  type: 'numeric' | 'chinese' | 'level' | 'graphic' | 'icon' | 'english' | 'special';
  symbols: string[];
  description: string;
  tags: string[];
  max_depth: number;
  preview_html: string;
  is_system?: boolean;
}

export async function getNumberingStyles(filters?: {
  type?: string;
  tags?: string[];
}): Promise<NumberingStyle[]> {
  const params = new URLSearchParams();
  if (filters?.type) params.append('type', filters.type);
  if (filters?.tags) {
    filters.tags.forEach(tag => params.append('tags', tag));
  }
  
  const queryString = params.toString();
  const response = await fetch(
    `/api/assets/numbering-styles${queryString ? '?' + queryString : ''}`
  );
  
  if (!response.ok) {
    throw new Error(`获取序号样式失败 (HTTP ${response.status})`);
  }
  return response.json();
}

/**
 * 获取所有资产（模板、配色、序号样式等）
 */
export async function getAllAssets(): Promise<{
  templates: any[];
  colorSchemes: any[];
  numberingStyles: NumberingStyle[];
}> {
  const response = await fetch('/api/assets/all');
  if (!response.ok) {
    throw new Error(`获取资产失败 (HTTP ${response.status})`);
  }
  return response.json();
}

export const EXPORT_FORMATS = [
  { type: 'html' as const, name: 'HTML', icon: '🌐', description: 'Web格式，浏览器直接打开' },
  { type: 'pptx' as const, name: 'PPTX', icon: '📊', description: 'PowerPoint 格式' },
  { type: 'pdf' as const, name: 'PDF', icon: '📄', description: '便携文档格式' },
  { type: 'png' as const, name: 'PNG', icon: '🖼️', description: '图片格式' },
] as const;

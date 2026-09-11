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
  };
  const response = await fetch('/api/generation/create', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(30_000),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(err.detail || `生成失败 (HTTP ${response.status})`);
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

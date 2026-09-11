// 演示文稿生成器核心类型定义

export type PresentationMode = 'rapid' | 'collaborative' | 'mastery';

export interface SlideData {
  title: string;
  content: string;
  image?: string;
  notes?: string;
}

export interface Checkpoint {
  id: string;
  name: string;
  description: string;
  status: 'pending' | 'in_progress' | 'completed';
  data?: unknown;
  timestamp?: number;
}

export interface GenerationState {
  status: 'idle' | 'loading' | 'success' | 'error';
  slides?: SlideData[];
  error?: string;
  progress?: number;
  keepOriginal?: boolean;
}

export interface ExportFormat {
  type: 'pptx' | 'pdf' | 'png' | 'html';
  name: string;
  icon: string;
}

import { PresentationMode } from '@/types';

interface ModeConfig {
  label: string;
  description: string;
  icon: string;
  color: string;
}

export const MODE_CONFIG: Record<PresentationMode, ModeConfig> = {
  rapid: {
    label: '极速',
    description: '快速生成，精简内容',
    icon: '⚡',
    color: 'from-amber-400 to-orange-500',
  },
  collaborative: {
    label: '协作',
    description: '多人协作，互动增强',
    icon: '👥',
    color: 'from-blue-400 to-cyan-500',
  },
  mastery: {
    label: '掌控',
    description: '深度定制，完整控制',
    icon: '🎯',
    color: 'from-purple-400 to-pink-500',
  },
};

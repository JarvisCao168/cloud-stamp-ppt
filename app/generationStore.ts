'use client';

import { useState, useCallback, useRef } from 'react';
import { PresentationMode, SlideData, GenerationState, Checkpoint } from '@/types';
import { generateSlides, getCheckpointFlow, submitCheckpointAction } from './api';
import { saveCheckpoint, clearAllCheckpoints } from './checkpoints';

export function useGeneration() {
  const [mode, setMode] = useState<PresentationMode>('rapid');
  const [state, setState] = useState<GenerationState>({ status: 'idle' });
  const [prompt, setPrompt] = useState('');
  const [checkpoints, setCheckpoints] = useState<Map<string, Checkpoint>>(new Map());
  const [sessionId, setSessionId] = useState<string>('');
  const abortRef = useRef<AbortController | null>(null);

  const updateMode = useCallback((newMode: PresentationMode) => {
    setMode(newMode);
  }, []);

  const generate = useCallback(async () => {
    if (!prompt.trim()) {
      setState({ status: 'error', error: '请输入演示文稿主题或内容描述' });
      return;
    }

    abortRef.current?.abort();
    abortRef.current = new AbortController();
    const controller = abortRef.current;

    setState({ status: 'loading', progress: 0 });
    clearAllCheckpoints();
    setCheckpoints(new Map());

    try {
      const result = await generateSlides(prompt, mode);

      // 保存 session_id，用于后续导出和检查点操作
      setSessionId(result.session_id);

      // 处理后端返回的检查点（协作/掌控模式）
      if (result.status === 'checkpoint' && result.checkpoints) {
        const newCheckpoints = new Map<string, Checkpoint>();
        result.checkpoints.forEach((cp, index) => {
          const checkPoint: Checkpoint = {
            id: cp.id,
            name: cp.title,
            description: cp.description,
            status: index === 0 ? 'in_progress' : 'pending',
            data: cp.data,
            timestamp: Date.now(),
          };
          newCheckpoints.set(cp.id, checkPoint);
          saveCheckpoint(cp.id, checkPoint);
        });
        setCheckpoints(newCheckpoints);
        setState({
          status: 'loading',
          progress: Math.round((1 / result.checkpoints.length) * 100),
          error: result.message,
        });
        return;
      }

      // 极速模式：直接解析数据
      const slides: SlideData[] = result.data?.slides || [];
      if (result.data?.intent) {
        if (slides.length > 0) {
          slides[0].notes = JSON.stringify(result.data.intent, null, 2);
        }
      }

      // 如果是掌控模式，创建8个检查点
      if (mode === 'mastery' && result.data) {
        const checkpointNames = [
          { id: 'outline_structure', name: '大纲结构' },
          { id: 'template_selection', name: '模板与主题' },
          { id: 'color_scheme', name: '配色方案' },
          { id: 'font_selection', name: '字体组合' },
          { id: 'layout_selection', name: '逐页布局' },
          { id: 'content_edit', name: '内容编辑' },
          { id: 'animation_selection', name: '动效方案' },
          { id: 'final_review', name: '最终审阅' },
        ];
        const newCheckpoints = new Map<string, Checkpoint>();
        checkpointNames.forEach((cp, index) => {
          const checkPoint: Checkpoint = {
            id: cp.id,
            name: cp.name,
            description: `检查点 ${index + 1}: ${cp.name}`,
            status: index === 0 ? 'in_progress' : 'pending',
            data: index === 0 ? slides : undefined,
            timestamp: Date.now(),
          };
          newCheckpoints.set(cp.id, checkPoint);
          saveCheckpoint(cp.id, checkPoint);
        });
        setCheckpoints(newCheckpoints);
      }

      setState({
        status: 'success',
        slides: slides.length > 0 ? slides : [
          { title: '演示文稿', content: prompt },
          { title: '核心内容', content: '请连接到后端服务以获取AI生成内容' },
          { title: '感谢观看', content: '' },
        ],
        progress: 100,
      });
    } catch (err) {
      if (controller.signal.aborted) return;
      setState({
        status: 'error',
        error: err instanceof Error ? err.message : '生成失败，请检查后端服务是否启动',
      });
    }
  }, [prompt, mode]);

  /**
   * 更新单个检查点状态
   */
  const updateCheckpoint = useCallback((checkpointId: string, status: Checkpoint['status'], data?: unknown) => {
    setCheckpoints(prev => {
      const next = new Map(prev);
      const cp = next.get(checkpointId);
      if (cp) {
        const updated = { ...cp, status, data, timestamp: Date.now() };
        next.set(checkpointId, updated);
        saveCheckpoint(checkpointId, updated);
      }
      return next;
    });
  }, []);

  /**
   * 提交检查点决策到后端
   */
  const confirmCheckpoint = useCallback(async (checkpointId: string, action: 'confirm' | 'edit' | 'regenerate' | 'select' = 'confirm') => {
    if (!sessionId) {
      updateCheckpoint(checkpointId, 'completed');
      return;
    }
    try {
      const result = await submitCheckpointAction({
        session_id: sessionId,
        checkpoint_id: checkpointId,
        action,
      });
      updateCheckpoint(checkpointId, 'completed');
      if (result.next_checkpoint) {
        const flow = await getCheckpointFlow(sessionId);
        const newCheckpoints = new Map<string, Checkpoint>();
        flow.checkpoints.forEach((cp) => {
          const checkPoint: Checkpoint = {
            id: cp.id,
            name: cp.title,
            description: cp.description,
            status: cp.status === 'active' ? 'in_progress' : cp.status as Checkpoint['status'],
            timestamp: Date.now(),
          };
          newCheckpoints.set(cp.id, checkPoint);
        });
        setCheckpoints(newCheckpoints);
      }
    } catch (err) {
      console.error('Checkpoint action failed:', err);
    }
  }, [sessionId, updateCheckpoint]);

  /**
   * 重置状态
   */
  const reset = useCallback(() => {
    setPrompt('');
    setState({ status: 'idle' });
    setSessionId('');
    clearAllCheckpoints();
    setCheckpoints(new Map());
    abortRef.current?.abort();
  }, []);

  return {
    mode,
    state,
    prompt,
    setPrompt,
    updateMode,
    generate,
    reset,
    checkpoints,
    updateCheckpoint,
    confirmCheckpoint,
    sessionId,
  };
}

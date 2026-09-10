import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useGeneration } from '@/generationStore';
import { Checkpoint } from '@/types';
import * as apiModule from '@/api';
import * as checkpointsModule from '@/checkpoints';

vi.mock('@/api');
vi.mock('@/checkpoints');

describe('useGeneration hook', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('initial state', () => {
    it('should initialize with default mode rapid', () => {
      const { result } = renderHook(() => useGeneration());
      expect(result.current.mode).toBe('rapid');
    });

    it('should initialize with idle state', () => {
      const { result } = renderHook(() => useGeneration());
      expect(result.current.state.status).toBe('idle');
    });

    it('should initialize with empty prompt', () => {
      const { result } = renderHook(() => useGeneration());
      expect(result.current.prompt).toBe('');
    });

    it('should initialize with empty checkpoints', () => {
      const { result } = renderHook(() => useGeneration());
      expect(result.current.checkpoints.size).toBe(0);
    });

    it('should initialize with empty sessionId', () => {
      const { result } = renderHook(() => useGeneration());
      expect(result.current.sessionId).toBe('');
    });
  });

  describe('updateMode', () => {
    it('should update mode to collaborative', () => {
      const { result } = renderHook(() => useGeneration());
      act(() => { result.current.updateMode('collaborative'); });
      expect(result.current.mode).toBe('collaborative');
    });

    it('should update mode to mastery', () => {
      const { result } = renderHook(() => useGeneration());
      act(() => { result.current.updateMode('mastery'); });
      expect(result.current.mode).toBe('mastery');
    });

    it('should update mode to rapid', () => {
      const { result } = renderHook(() => useGeneration());
      act(() => { result.current.updateMode('rapid'); });
      expect(result.current.mode).toBe('rapid');
    });
  });

  describe('generate function - validation', () => {
    it('should set error when prompt is empty', async () => {
      const { result } = renderHook(() => useGeneration());
      
      await act(async () => {
        await result.current.generate();
      });
      
      expect(result.current.state.status).toBe('error');
      expect(result.current.state.error).toContain('请输入演示文稿主题');
    });

    it('should set error when prompt is whitespace only', async () => {
      const { result } = renderHook(() => useGeneration());
      
      await act(async () => {
        result.current.setPrompt('   ');
        await result.current.generate();
      });
      
      expect(result.current.state.status).toBe('error');
      expect(result.current.state.error).toContain('请输入演示文稿主题');
    });
  });

  describe('generate function - success scenarios', () => {
    it('should handle successful rapid mode generation', async () => {
      vi.mocked(apiModule.generateSlides).mockResolvedValue({
        session_id: 'sess-123',
        status: 'completed',
        data: {
          slides: [
            { title: 'Slide 1', content: 'Content 1' },
            { title: 'Slide 2', content: 'Content 2' },
          ],
          intent: { theme: 'tech' },
        },
      });

      const { result } = renderHook(() => useGeneration());
      
      act(() => { result.current.setPrompt('Test presentation'); });
      act(() => { result.current.updateMode('rapid'); });
      
      await act(async () => {
        await result.current.generate();
      });

      expect(result.current.state.status).toBe('success');
      expect(result.current.sessionId).toBe('sess-123');
      expect(result.current.state.slides).toHaveLength(2);
    });

    it('should handle mastery mode with checkpoint creation', async () => {
      vi.mocked(apiModule.generateSlides).mockResolvedValue({
        session_id: 'sess-456',
        status: 'completed',
        data: {
          slides: [{ title: 'Title', content: 'Content' }],
        },
      });

      const { result } = renderHook(() => useGeneration());
      
      act(() => { result.current.setPrompt('Full control presentation'); });
      act(() => { result.current.updateMode('mastery'); });
      
      await act(async () => {
        await result.current.generate();
      });

      expect(result.current.state.status).toBe('success');
      expect(result.current.sessionId).toBe('sess-456');
      expect(result.current.checkpoints.size).toBe(8);
      
      const checkpointKeys = Array.from(result.current.checkpoints.keys());
      expect(checkpointKeys).toContain('outline_structure');
      expect(checkpointKeys).toContain('final_review');
    });

    it('should set default slides when API returns empty slides', async () => {
      vi.mocked(apiModule.generateSlides).mockResolvedValue({
        session_id: 'sess-789',
        status: 'completed',
        data: { slides: [] },
      });

      const { result } = renderHook(() => useGeneration());
      
      act(() => { result.current.setPrompt('Empty response test'); });
      
      await act(async () => {
        await result.current.generate();
      });

      expect(result.current.state.status).toBe('success');
      expect(result.current.state.slides).toHaveLength(3);
      expect(result.current.state.slides[0].title).toBe('演示文稿');
    });

    it('should attach intent notes to first slide', async () => {
      const intent = { theme: 'business', tone: 'formal' };
      vi.mocked(apiModule.generateSlides).mockResolvedValue({
        session_id: 'sess-notes',
        status: 'completed',
        data: {
          slides: [{ title: 'Title', content: 'Content' }],
          intent,
        },
      });

      const { result } = renderHook(() => useGeneration());
      
      act(() => { result.current.setPrompt('Intent test'); });
      
      await act(async () => {
        await result.current.generate();
      });

      expect(result.current.state.slides).toBeDefined();
      expect(result.current.state.slides![0].notes).toBe(JSON.stringify(intent, null, 2));
    });
  });

  describe('generate function - checkpoint response', () => {
    it('should handle checkpoint status from backend', async () => {
      vi.mocked(apiModule.generateSlides).mockResolvedValue({
        session_id: 'sess-cp',
        status: 'checkpoint',
        checkpoints: [
          { id: 'cp-1', title: 'First', description: 'Desc 1', data: {} },
          { id: 'cp-2', title: 'Second', description: 'Desc 2', data: null },
        ],
        message: 'Please review checkpoints',
      });

      const { result } = renderHook(() => useGeneration());
      
      act(() => { result.current.setPrompt('Checkpoint test'); });
      
      await act(async () => {
        await result.current.generate();
      });

      expect(result.current.state.status).toBe('loading');
      expect(result.current.checkpoints.size).toBe(2);
      expect(result.current.state.error).toContain('Please review');
    });
  });

  describe('generate function - error handling', () => {
    it('should handle API errors', async () => {
      vi.mocked(apiModule.generateSlides).mockRejectedValue(new Error('Network error'));

      const { result } = renderHook(() => useGeneration());
      
      act(() => { result.current.setPrompt('Error test'); });
      
      await act(async () => {
        await result.current.generate();
      });

      expect(result.current.state.status).toBe('error');
      expect(result.current.state.error).toContain('Network error');
    });

    it('should handle non-Error exceptions', async () => {
      vi.mocked(apiModule.generateSlides).mockRejectedValue('String error');

      const { result } = renderHook(() => useGeneration());
      
      act(() => { result.current.setPrompt('String error test'); });
      
      await act(async () => {
        await result.current.generate();
      });

      expect(result.current.state.status).toBe('error');
      expect(result.current.state.error).toBe('生成失败，请检查后端服务是否启动');
    });
  });

  describe('generate function - abort', () => {
    it('should abort previous generation when called again', async () => {
      let resolveFirst: (() => void) | null = null;
      vi.mocked(apiModule.generateSlides).mockImplementation(() => {
        return new Promise((resolve) => {
          resolveFirst = () => resolve({
            session_id: 'sess-abort-1',
            status: 'completed',
            data: { slides: [] },
          });
        });
      });

      const { result } = renderHook(() => useGeneration());
      
      act(() => { result.current.setPrompt('First test'); });
      
      // Start first generation (async)
      act(() => {
        result.current.generate();
      });
      
      // Start second generation (should abort first)
      vi.mocked(apiModule.generateSlides).mockResolvedValue({
        session_id: 'sess-abort-2',
        status: 'completed',
        data: { slides: [] },
      });
      
      act(() => { result.current.setPrompt('Second test'); });
      await act(async () => {
        await result.current.generate();
      });
      
      // Second generation should complete
      expect(result.current.state.status).toBe('success');
      expect(result.current.sessionId).toBe('sess-abort-2');
      
      // Resolve first pending promise - should not affect state
      resolveFirst?.();
    });
  });

  describe('updateCheckpoint', () => {
    it('should update checkpoint status and call saveCheckpoint', async () => {
      const { result } = renderHook(() => useGeneration());
      
      await act(async () => {
        const checkpoint: Checkpoint = {
          id: 'cp-test',
          name: 'Test CP',
          status: 'pending',
          timestamp: Date.now(),
        };
        result.current.checkpoints.set('cp-test', checkpoint);
      });

      await act(async () => {
        result.current.updateCheckpoint('cp-test', 'in_progress', { key: 'value' });
      });

      expect(result.current.checkpoints.get('cp-test')?.status).toBe('in_progress');
      expect(result.current.checkpoints.get('cp-test')?.data).toEqual({ key: 'value' });
      expect(checkpointsModule.saveCheckpoint).toHaveBeenCalledWith('cp-test', expect.objectContaining({
        status: 'in_progress',
      }));
    });

    it('should not throw when updating non-existent checkpoint', async () => {
      const { result } = renderHook(() => useGeneration());
      
      await act(async () => {
        result.current.updateCheckpoint('non-existent', 'completed');
      });

      expect(result.current.checkpoints.size).toBe(0);
    });
  });

  describe('confirmCheckpoint', () => {
    it('should skip API call when no sessionId', async () => {
      const { result } = renderHook(() => useGeneration());
      
      await act(async () => {
        await result.current.confirmCheckpoint('cp-1');
      });

      expect(apiModule.submitCheckpointAction).not.toHaveBeenCalled();
    });

    it('should call API when sessionId exists', async () => {
      vi.mocked(apiModule.submitCheckpointAction).mockResolvedValue({
        next_checkpoint: 'cp-2',
        session_id: 'sess-confirm',
        status: 'ok',
      });

      const { result } = renderHook(() => useGeneration());
      
      // First generate to set sessionId
      vi.mocked(apiModule.generateSlides).mockResolvedValue({
        session_id: 'sess-confirm',
        status: 'completed',
        data: { slides: [] },
      });
      
      act(() => { result.current.setPrompt('Session test'); });
      
      await act(async () => {
        await result.current.generate();
      });

      await act(async () => {
        await result.current.confirmCheckpoint('cp-1', 'confirm');
      });

      expect(apiModule.submitCheckpointAction).toHaveBeenCalledWith({
        session_id: 'sess-confirm',
        checkpoint_id: 'cp-1',
        action: 'confirm',
      });
    });

    it('should handle different actions', async () => {
      vi.mocked(apiModule.submitCheckpointAction).mockResolvedValue({
        next_checkpoint: null,
        session_id: 'sess-action',
        status: 'ok',
      });

      const { result } = renderHook(() => useGeneration());
      
      // First generate to set sessionId
      vi.mocked(apiModule.generateSlides).mockResolvedValue({
        session_id: 'sess-action',
        status: 'completed',
        data: { slides: [] },
      });
      
      act(() => { result.current.setPrompt('Action test'); });
      
      await act(async () => {
        await result.current.generate();
      });

      await act(async () => {
        await result.current.confirmCheckpoint('cp-edit', 'edit');
      });

      expect(apiModule.submitCheckpointAction).toHaveBeenCalledWith(expect.objectContaining({
        action: 'edit',
      }));
    });

    it('should fetch checkpoint flow when next_checkpoint returned', async () => {
      vi.mocked(apiModule.submitCheckpointAction).mockResolvedValue({
        next_checkpoint: 'cp-next',
        session_id: 'sess-flow',
        status: 'ok',
      });
      vi.mocked(apiModule.getCheckpointFlow).mockResolvedValue({
        session_id: 'sess-flow',
        mode: 'mastery',
        checkpoints: [
          { id: 'cp-next', title: 'Next', description: 'Desc', status: 'active' },
        ],
      });

      const { result } = renderHook(() => useGeneration());
      
      // First generate to set sessionId
      vi.mocked(apiModule.generateSlides).mockResolvedValue({
        session_id: 'sess-flow',
        status: 'completed',
        data: { slides: [] },
      });
      
      act(() => { result.current.setPrompt('Flow test'); });
      
      await act(async () => {
        await result.current.generate();
      });

      await act(async () => {
        await result.current.confirmCheckpoint('cp-1');
      });

      expect(apiModule.getCheckpointFlow).toHaveBeenCalledWith('sess-flow');
      expect(result.current.checkpoints.get('cp-next')?.status).toBe('in_progress');
    });
  });

  describe('reset', () => {
    it('should clear all state', async () => {
      const { result } = renderHook(() => useGeneration());
      
      act(() => { result.current.setPrompt('Test'); });
      
      await act(async () => {
        await result.current.reset();
      });

      expect(result.current.prompt).toBe('');
      expect(result.current.state.status).toBe('idle');
      expect(result.current.sessionId).toBe('');
      expect(result.current.checkpoints.size).toBe(0);
    });

    it('should call clearAllCheckpoints', async () => {
      const { result } = renderHook(() => useGeneration());
      
      await act(async () => {
        await result.current.reset();
      });

      expect(checkpointsModule.clearAllCheckpoints).toHaveBeenCalled();
    });

    it('should abort pending generation', async () => {
      let resolvePromise: (() => void) | null = null;
      vi.mocked(apiModule.generateSlides).mockReturnValue(new Promise((resolve) => {
        resolvePromise = () => resolve({
          session_id: 'sess-abort-reset',
          status: 'completed',
          data: { slides: [] },
        });
      }));

      const { result } = renderHook(() => useGeneration());
      
      act(() => { result.current.setPrompt('Abort reset test'); });
      
      // Start generation
      const genPromise = act(async () => {
        result.current.generate();
      });
      
      // Immediately reset (should abort)
      await act(async () => {
        await result.current.reset();
      });
      
      // Now resolve the pending promise
      resolvePromise?.();
      
      // State should be idle (from reset), not success (from aborted generation)
      expect(result.current.state.status).toBe('idle');
      
      // Wait for the promise to settle
      await genPromise;
    });
  });

  describe('state transitions', () => {
    it('should go from idle to loading to success', async () => {
      vi.mocked(apiModule.generateSlides).mockResolvedValue({
        session_id: 'sess-transition',
        status: 'completed',
        data: { slides: [] },
      });

      const { result } = renderHook(() => useGeneration());
      
      act(() => { result.current.setPrompt('Transition test'); });
      
      await act(async () => {
        await result.current.generate();
      });

      expect(result.current.state.status).toBe('success');
      expect(result.current.state.progress).toBe(100);
    });

    it('should show loading progress during generation', async () => {
      vi.mocked(apiModule.generateSlides).mockResolvedValue({
        session_id: 'sess-progress',
        status: 'completed',
        data: { slides: [] },
      });

      const { result } = renderHook(() => useGeneration());
      
      act(() => { result.current.setPrompt('Progress test'); });
      
      expect(result.current.state.status).toBe('idle');
      
      await act(async () => {
        await result.current.generate();
      });

      expect(result.current.state.status).toBe('success');
    });
  });
});

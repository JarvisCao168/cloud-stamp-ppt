import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { GenerationResult, CheckpointAction } from '@/api';

// Mock DOM APIs
const mockCreateElement = vi.fn();

vi.stubGlobal('document', { createElement: mockCreateElement });

vi.stubGlobal('AbortSignal', {
  timeout: (ms: number) => ({ timeout: ms }),
});

describe('API Functions', () => {
  let generateSlides: (prompt: string, mode: string) => Promise<GenerationResult>;
  let getSession: (sessionId: string) => Promise<Record<string, unknown>>;
  let submitCheckpointAction: (action: CheckpointAction) => Promise<Record<string, unknown>>;
  let getCheckpointFlow: (sessionId: string) => Promise<Record<string, unknown>>;
  let exportPresentation: (sessionId: string, options: { format: string; title?: string; quality?: string }) => Promise<Record<string, unknown>>;
  let EXPORT_FORMATS: Array<{ type: string; name: string; icon: string; description: string }>;

  const mockFetch = vi.fn();
  global.fetch = mockFetch;

  beforeEach(async () => {
    vi.clearAllMocks();
    mockCreateElement.mockClear();
    const mod = await import('@/api');
    generateSlides = mod.generateSlides;
    getSession = mod.getSession;
    submitCheckpointAction = mod.submitCheckpointAction;
    getCheckpointFlow = mod.getCheckpointFlow;
    exportPresentation = mod.exportPresentation;
    EXPORT_FORMATS = mod.EXPORT_FORMATS;
  });

  describe('EXPORT_FORMATS', () => {
    it('should have 4 export formats', () => {
      expect(EXPORT_FORMATS).toHaveLength(4);
    });

    it('should have html format', () => {
      const htmlFormat = EXPORT_FORMATS.find(f => f.type === 'html');
      expect(htmlFormat).toBeDefined();
      expect(htmlFormat?.name).toBe('HTML');
    });

    it('should have pptx format', () => {
      const pptxFormat = EXPORT_FORMATS.find(f => f.type === 'pptx');
      expect(pptxFormat).toBeDefined();
      expect(pptxFormat?.name).toBe('PPTX');
    });

    it('should have pdf format', () => {
      const pdfFormat = EXPORT_FORMATS.find(f => f.type === 'pdf');
      expect(pdfFormat).toBeDefined();
      expect(pdfFormat?.name).toBe('PDF');
    });

    it('should have png format', () => {
      const pngFormat = EXPORT_FORMATS.find(f => f.type === 'png');
      expect(pngFormat).toBeDefined();
      expect(pngFormat?.name).toBe('PNG');
    });
  });

  describe('MODE_MAP', () => {
    it('should map rapid to quick', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ session_id: 'test', status: 'completed', message: 'ok' }),
      });
      
      await generateSlides('test prompt', 'rapid');
      
      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(body.mode).toBe('quick');
    });

    it('should map collaborative to collaborative', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ session_id: 'test', status: 'completed', message: 'ok' }),
      });
      
      await generateSlides('test prompt', 'collaborative');
      
      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(body.mode).toBe('collaborative');
    });

    it('should map mastery to full_control', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ session_id: 'test', status: 'completed', message: 'ok' }),
      });
      
      await generateSlides('test prompt', 'mastery');
      
      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(body.mode).toBe('full_control');
    });
  });

  describe('generateSlides', () => {
    it('should call correct API endpoint', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ session_id: 'sess-123', status: 'completed', message: 'success', data: { slides: [] } }),
      });

      await generateSlides('test prompt', 'rapid');
      
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/generation/create',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        })
      );
    });

    it('should return parsed response', async () => {
      const mockResponse = {
        session_id: 'sess-123',
        status: 'completed',
        message: 'success',
        data: { slides: [{ title: 'Test', content: 'Content' }] },
      };
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await generateSlides('test prompt', 'rapid');
      
      expect(result).toEqual(mockResponse);
      expect(result.session_id).toBe('sess-123');
      expect(result.status).toBe('completed');
    });

    it('should throw on HTTP error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => ({ detail: 'Server error' }),
      });

      await expect(generateSlides('test prompt', 'rapid'))
        .rejects.toThrow('Server error');
    });

    it('should include timeout signal', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ session_id: 'test', status: 'completed', message: 'ok' }),
      });

      await generateSlides('test prompt', 'rapid');
      
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/generation/create',
        expect.objectContaining({
          signal: expect.any(Object),
        })
      );
    });
  });

  describe('getSession', () => {
    it('should call correct endpoint with session ID', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ session_id: 'sess-123', status: 'in_progress' }),
      });

      await getSession('sess-123');
      
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/generation/session/sess-123'
      );
    });

    it('should encode special characters in session ID', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      });

      await getSession('sess/123');
      
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/generation/session/sess%2F123'
      );
    });

    it('should throw on error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
      });

      await expect(getSession('nonexistent'))
        .rejects.toThrow('获取会话失败');
    });
  });

  describe('submitCheckpointAction', () => {
    it('should call correct endpoint with action', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: 'ok', session_id: 'sess-123' }),
      });

      await submitCheckpointAction({
        session_id: 'sess-123',
        checkpoint_id: 'cp-1',
        action: 'confirm',
      });
      
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/generation/checkpoint/sess-123/cp-1/action',
        expect.objectContaining({
          method: 'POST',
        })
      );
    });

    it('should send correct action body', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      });

      await submitCheckpointAction({
        session_id: 'sess-123',
        checkpoint_id: 'cp-1',
        action: 'edit',
        data: { title: 'New Title' },
      });
      
      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(body.session_id).toBe('sess-123');
      expect(body.checkpoint_id).toBe('cp-1');
      expect(body.action).toBe('edit');
      expect(body.data).toEqual({ title: 'New Title' });
    });
  });

  describe('getCheckpointFlow', () => {
    it('should call correct endpoint', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          session_id: 'sess-123',
          mode: 'full_control',
          current_checkpoint: 'cp-1',
          checkpoints: [],
        }),
      });

      await getCheckpointFlow('sess-123');
      
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/checkpoints/flow/sess-123'
      );
    });
  });

  describe('exportPresentation', () => {
    it('should call correct endpoint for PPTX', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ filename: 'test.pptx', url: '/download/test.pptx', format: 'pptx' }),
      });

      await exportPresentation('sess-123', { format: 'pptx' });
      
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/export/pptx',
        expect.objectContaining({
          method: 'POST',
        })
      );
    });

    it('should call correct endpoint for PDF', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ filename: 'test.pdf', url: '/download/test.pdf', format: 'pdf' }),
      });

      await exportPresentation('sess-123', { format: 'pdf' });
      
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/export/pdf',
        expect.objectContaining({
          method: 'POST',
        })
      );
    });

    it('should call correct endpoint for HTML', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ filename: 'test.html', url: '/download/test.html', format: 'html' }),
      });

      await exportPresentation('sess-123', { format: 'html' });
      
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/export/html',
        expect.objectContaining({
          method: 'POST',
        })
      );
    });

    it('should call correct endpoint for PNG', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ filename: 'test.png', url: '/download/test.png', format: 'png' }),
      });

      await exportPresentation('sess-123', { format: 'png' });
      
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/export/png',
        expect.objectContaining({
          method: 'POST',
        })
      );
    });

    it('should include default options', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      });

      await exportPresentation('sess-123', { format: 'pptx' });
      
      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(body.session_id).toBe('sess-123');
      expect(body.format).toBe('pptx');
      expect(body.title).toBe('演示文稿');
      expect(body.quality).toBe('hd');
    });

    it('should use custom options when provided', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      });

      await exportPresentation('sess-123', {
        format: 'pdf',
        title: '我的演示',
        quality: 'sd'
      });

      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(body.title).toBe('我的演示');
      expect(body.quality).toBe('sd');
    });

    it('should include numberingStyleId in body when provided', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      });

      await exportPresentation('sess-123', {
        format: 'pptx',
        numberingStyleId: 'numeric-dot',
      });

      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(body.numbering_style_id).toBe('numeric-dot');
    });

    it('should not include numbering_style_id when not provided', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      });

      await exportPresentation('sess-123', { format: 'pptx' });

      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(body).not.toHaveProperty('numbering_style_id');
    });

    it('should throw on error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => ({ detail: '导出失败' }),
      });

      await expect(exportPresentation('sess-123', { format: 'pptx' }))
        .rejects.toThrow('导出失败');
    });
  });
});

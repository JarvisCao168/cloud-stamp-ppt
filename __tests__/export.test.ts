import { describe, it, expect, vi, beforeEach } from 'vitest';
// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('export.ts', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('EXPORT_FORMATS', () => {
    it('should define 4 export formats', async () => {
      const { EXPORT_FORMATS } = await import('@/export');
      expect(EXPORT_FORMATS).toHaveLength(4);
    });

    it('should have all required format types', async () => {
      const { EXPORT_FORMATS } = await import('@/export');
      const types = EXPORT_FORMATS.map(f => f.type);
      expect(types).toContain('html');
      expect(types).toContain('pptx');
      expect(types).toContain('pdf');
      expect(types).toContain('png');
    });

    it('should have format names matching types', async () => {
      const { EXPORT_FORMATS } = await import('@/export');
      const nameMap: Record<string, string> = {
        html: 'HTML',
        pptx: 'PPTX',
        pdf: 'PDF',
        png: 'PNG',
      };
      EXPORT_FORMATS.forEach(f => {
        expect(f.name).toBe(nameMap[f.type]);
      });
    });

    it('should have format icons', async () => {
      const { EXPORT_FORMATS } = await import('@/export');
      EXPORT_FORMATS.forEach(f => {
        expect(f.icon).toBeDefined();
        expect(typeof f.icon).toBe('string');
      });
    });

    it('should have format descriptions', async () => {
      const { EXPORT_FORMATS } = await import('@/export');
      EXPORT_FORMATS.forEach(f => {
        expect(f.description).toBeDefined();
        expect(typeof f.description).toBe('string');
        expect(f.description.length).toBeGreaterThan(0);
      });
    });
  });

  describe('exportPresentationToFile', () => {
    it('should call exportPresentation with correct parameters', async () => {
      const { exportPresentationToFile } = await import('@/export');
      
      const mockResult = {
        filename: 'test.pptx',
        url: '/api/export/download/test.pptx',
        format: 'pptx',
        size_bytes: 1024,
      };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResult,
      });

      const result = await exportPresentationToFile([], { format: 'pptx' }, 'session-123');
      
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/export/pptx',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            session_id: 'session-123',
            format: 'pptx',
            title: '演示文稿',
            quality: 'hd',
          }),
        })
      );
      expect(result).toEqual(mockResult);
    });

    it('should use custom title when provided', async () => {
      const { exportPresentationToFile } = await import('@/export');
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ filename: 'my-ppt.pptx', url: '/api/export/my-ppt.pptx', format: 'pptx' }),
      });

      await exportPresentationToFile([], { format: 'pptx', title: '我的演示' }, 'session-1');
      
      const callArgs = mockFetch.mock.calls[0][1];
      const body = JSON.parse(callArgs.body);
      expect(body.title).toBe('我的演示');
    });

    it('should throw on API error', async () => {
      const { exportPresentationToFile } = await import('@/export');
      
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => ({ detail: '导出失败' }),
      });

      await expect(
        exportPresentationToFile([], { format: 'pdf' }, 'session-1')
      ).rejects.toThrow('导出失败');
    });

    it('should use default quality when not provided', async () => {
      const { exportPresentationToFile } = await import('@/export');
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ filename: 'test.pdf', url: '/api/export/test.pdf', format: 'pdf' }),
      });

      await exportPresentationToFile([], { format: 'pdf' }, 'session-1');
      
      const callArgs = mockFetch.mock.calls[0][1];
      const body = JSON.parse(callArgs.body);
      expect(body.quality).toBe('hd');
    });

    it('should use provided quality option', async () => {
      const { exportPresentationToFile } = await import('@/export');
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ filename: 'test.pdf', url: '/api/export/test.pdf', format: 'pdf' }),
      });

      await exportPresentationToFile([], { format: 'pdf', quality: 'sd' }, 'session-1');
      
      const callArgs = mockFetch.mock.calls[0][1];
      const body = JSON.parse(callArgs.body);
      expect(body.quality).toBe('sd');
    });

    it('should handle network error gracefully', async () => {
      const { exportPresentationToFile } = await import('@/export');
      
      mockFetch.mockRejectedValueOnce(new Error('Network Error'));

      await expect(
        exportPresentationToFile([], { format: 'html' }, 'session-1')
      ).rejects.toThrow('Network Error');
    });
  });

  describe('exportToHTML', () => {
    it('should generate valid HTML with slides', async () => {
      const { exportToHTML } = await import('@/export');
      
      const slides = [
        { title: '封面', content: '云章PPT智能体', image: undefined, notes: undefined },
        { title: '目录', content: '1. 简介 2. 功能', image: undefined, notes: '测试备注' },
      ];

      const blob = await exportToHTML(slides);
      expect(blob).toBeInstanceOf(Blob);
      expect(blob.type).toBe('text/html');

      const html = await blob.text();
      expect(html).toContain('<!DOCTYPE html>');
      expect(html).toContain('<h2>封面</h2>');
      expect(html).toContain('<h2>目录</h2>');
      expect(html).toContain('云章PPT智能体');
      expect(html).toContain('测试备注');
    });

    it('should escape HTML special characters', async () => {
      const { exportToHTML } = await import('@/export');
      
      const slides = [
        { title: '<script>alert("xss")</script>', content: 'Test & More', image: undefined, notes: undefined },
      ];

      const blob = await exportToHTML(slides);
      const html = await blob.text();
      
      expect(html).not.toContain('<script>alert("xss")</script>');
      expect(html).toContain('&lt;script&gt;');
      expect(html).toContain('&amp;');
    });

    it('should handle empty slides array', async () => {
      const { exportToHTML } = await import('@/export');
      
      const blob = await exportToHTML([]);
      const html = await blob.text();
      
      expect(html).toContain('<!DOCTYPE html>');
      expect(html).not.toContain('<section class="slide">');
    });

    it('should include image tag when image URL is provided', async () => {
      const { exportToHTML } = await import('@/export');
      
      const slides = [
        { title: '配图页', content: '以下是图表', image: 'https://example.com/chart.png', notes: undefined },
      ];

      const blob = await exportToHTML(slides);
      const html = await blob.text();
      
      expect(html).toContain('<img src="https://example.com/chart.png"');
      expect(html).toContain('alt="配图页"');
    });

    it('should not include image tag when image is undefined', async () => {
      const { exportToHTML } = await import('@/export');
      
      const slides = [
        { title: '纯文本页', content: '无图片', image: undefined, notes: undefined },
      ];

      const blob = await exportToHTML(slides);
      const html = await blob.text();
      
      expect(html).not.toContain('<img');
    });

    it('should generate correct CSS styling', async () => {
      const { exportToHTML } = await import('@/export');
      
      const slides = [
        { title: '测试', content: '内容', image: undefined, notes: undefined },
      ];

      const blob = await exportToHTML(slides);
      const html = await blob.text();
      
      expect(html).toContain('min-height: 100vh');
      expect(html).toContain('padding: 4rem');
      expect(html).toContain('font-size: 3rem');
      expect(html).toContain('font-size: 1.5rem');
    });

    it('should include print media query', async () => {
      const { exportToHTML } = await import('@/export');
      
      const slides = [
        { title: '测试', content: '内容', image: undefined, notes: undefined },
      ];

      const blob = await exportToHTML(slides);
      const html = await blob.text();
      
      expect(html).toContain('@media print');
      expect(html).toContain('page-break-after: always');
    });

    it('should set lang attribute to zh-CN', async () => {
      const { exportToHTML } = await import('@/export');
      
      const slides = [
        { title: '测试', content: '内容', image: undefined, notes: undefined },
      ];

      const blob = await exportToHTML(slides);
      const html = await blob.text();
      
      expect(html).toContain('lang="zh-CN');
    });
  });
});

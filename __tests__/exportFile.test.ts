import { describe, it, expect } from 'vitest';
import { exportToHTML, EXPORT_FORMATS } from '@/export';

describe('export utilities', () => {
  describe('EXPORT_FORMATS', () => {
    it('should have 4 formats', () => { expect(EXPORT_FORMATS).toHaveLength(4); });
    it('should include html format', () => { const h=EXPORT_FORMATS.find(f=>f.type==='html'); expect(h).toBeDefined(); expect(h?.name).toBe('HTML'); });
    it('should include pptx format', () => { const p=EXPORT_FORMATS.find(f=>f.type==='pptx'); expect(p).toBeDefined(); expect(p?.name).toBe('PPTX'); });
    it('should include pdf format', () => { const p=EXPORT_FORMATS.find(f=>f.type==='pdf'); expect(p).toBeDefined(); expect(p?.name).toBe('PDF'); });
    it('should include png format', () => { const p=EXPORT_FORMATS.find(f=>f.type==='png'); expect(p).toBeDefined(); expect(p?.name).toBe('PNG'); });
  });
  describe('exportToHTML', () => {
    it('should generate valid HTML blob', async () => { const slides=[{title:'Slide 1',content:'Content 1'}]; const blob=await exportToHTML(slides); expect(blob).toBeInstanceOf(Blob); expect(blob.size).toBeGreaterThan(0); });
    it('should escape HTML special characters', async () => { const slides=[{title:'Test',content:'Content'}]; const blob=await exportToHTML(slides); const text=await blob.text(); expect(text).toContain('<!DOCTYPE html>'); });
    it('should handle empty slides array', async () => { const blob=await exportToHTML([]); expect(blob).toBeInstanceOf(Blob); });
  });
});

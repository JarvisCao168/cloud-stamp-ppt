import { SlideData } from '@/types';
import { ExportOptions, exportPresentation } from './api';

/**
 * 导出演示文稿（代理到后端服务）
 * @param slides 幻灯片数据（当前未使用，由 sessionId 标识）
 * @param options 导出选项
 * @param sessionId 后端会话 ID（由 generateSlides 返回）
 */
export async function exportPresentationToFile(
  slides: SlideData[],
  options: ExportOptions,
  sessionId: string
): Promise<{ filename: string; url: string; format: string }> {
  const result = await exportPresentation(sessionId, options);
  return result;
}

/**
 * 生成本地 HTML 导出（无后端时的降级方案）
 */
export async function exportToHTML(slides: SlideData[]): Promise<Blob> {
  const slidesHTML = slides.map((slide, index) => `
    <section class="slide" data-slide="${index}">
      <h2>${escapeHtml(slide.title)}</h2>
      <div class="content">${escapeHtml(slide.content)}</div>
      ${slide.image ? `<img src="${escapeHtml(slide.image)}" alt="${escapeHtml(slide.title)}" class="slide-image" />` : ''}
      ${slide.notes ? `<div class="notes">${escapeHtml(slide.notes)}</div>` : ''}
    </section>
  `).join('\n');

  const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>演示文稿</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
    .slide {
      min-height: 100vh;
      padding: 4rem;
      display: flex;
      flex-direction: column;
      justify-content: center;
      page-break-after: always;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
    }
    .slide h2 {
      font-size: 3rem;
      margin-bottom: 2rem;
    }
    .slide .content {
      font-size: 1.5rem;
      line-height: 1.8;
      opacity: 0.9;
    }
    .slide-image {
      max-width: 100%;
      margin-top: 2rem;
      border-radius: 8px;
    }
    .notes {
      margin-top: 3rem;
      padding: 1rem;
      background: rgba(255,255,255,0.1);
      border-radius: 8px;
      font-size: 1rem;
    }
    @media print {
      .slide { page-break-after: always; }
    }
  </style>
</head>
<body>
  ${slidesHTML}
</body>
</html>`;

  return new Blob([html], { type: 'text/html' });
}

function escapeHtml(text: string): string {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

export const EXPORT_FORMATS = [
  { type: 'html' as const, name: 'HTML', icon: '🌐', description: 'Web格式，浏览器直接打开' },
  { type: 'pptx' as const, name: 'PPTX', icon: '📊', description: 'PowerPoint 格式（需后端服务）' },
  { type: 'pdf' as const, name: 'PDF', icon: '📄', description: '便携文档格式（需后端服务）' },
  { type: 'png' as const, name: 'PNG', icon: '🖼️', description: '图片格式（需后端服务）' },
] as const;

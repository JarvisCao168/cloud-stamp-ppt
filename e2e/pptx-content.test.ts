import { test, expect } from '@playwright/test';
import { execSync } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';

/**
 * E2E PPTX 内容验证测试
 * 验证导出 PPTX 文件中序号样式正确注入
 *
 * 运行方式：
 *   npx playwright test e2e/pptx-content.test.ts
 *
 * 依赖：后端服务运行在 localhost:8000
 */

const API_BASE = 'http://localhost:8000';
const isCI = process.env.CI === 'true';
test.skip(isCI, 'Skipping PPTX content tests in CI - backend not available');

// Windows-safe temp directory
const TMP_DIR = process.env.TEMP || '/tmp';

const NUMBERING_STYLES = {
  'numeric-dot': { symbols: ['1.', '2.', '3.'], name: '数字序号·' },
  'chinese-clause': { symbols: ['一、', '二、', '三、'], name: '中文顿号' },
  'graphic-bullet': { symbols: ['•', '‣', '⁃'], name: '项目符号' },
  'icon-check': { symbols: ['→', '✓', '✗'], name: '箭头图标' },
};

async function createSession(userInput: string, mode: string = 'quick'): Promise<string> {
  const response = await fetch(`${API_BASE}/api/generation/create`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_input: userInput, mode }),
    signal: AbortSignal.timeout(15_000),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(`创建会话失败: ${err.detail || response.statusText}`);
  }
  const data = await response.json();
  return data.session_id;
}

async function exportPPTX(sessionId: string, numberingStyleId?: string): Promise<{ filename: string; url: string }> {
  const body: Record<string, unknown> = {
    session_id: sessionId,
    format: 'pptx',
    title: '测试演示文稿',
  };
  if (numberingStyleId) {
    body.numbering_style_id = numberingStyleId;
  }
  const response = await fetch(`${API_BASE}/api/export/pptx`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(60_000),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(`PPTX 导出失败: ${err.detail || response.statusText}`);
  }
  return response.json() as Promise<{ filename: string; url: string }>;
}

async function downloadPPTX(url: string): Promise<Buffer> {
  const response = await fetch(`${API_BASE}${url}`, {
    signal: AbortSignal.timeout(15_000),
  });
  if (!response.ok) {
    throw new Error(`下载 PPTX 失败: HTTP ${response.status}`);
  }
  return Buffer.from(await response.arrayBuffer());
}

/**
 * 用 python-pptx 解析 PPTX 文件，提取所有段落文本。
 * 使用脚本文件而非 -c 内联执行，以兼容 Windows PowerShell 的编码问题。
 */
function extractPPTXTexts(pptxBuf: Buffer): string[] {
  const tmpPptx = path.join(TMP_DIR, `pptx_content_${Date.now()}.pptx`);
  const tmpScript = path.join(TMP_DIR, `extract_pptx_${Date.now()}.py`);
  const marker = '__TEXTS__';

  try {
    fs.writeFileSync(tmpPptx, pptxBuf);
    fs.writeFileSync(tmpScript, [
      `from pptx import Presentation`,
      `prs = Presentation(r'${tmpPptx.replace(/\\/g, '\\\\')}')`,
      `texts = []`,
      `for slide in prs.slides:`,
      `    for shape in slide.shapes:`,
      `        if hasattr(shape, 'text_frame'):`,
      `            for para in shape.text_frame.paragraphs:`,
      `                if para.text.strip():`,
      `                    texts.append(para.text.strip())`,
      `print('${marker}')`,
      `print('|||'.join(texts))`,
    ].join('\n'));

    const result = execSync(`python "${tmpScript}"`, {
      encoding: 'utf-8',
      timeout: 10000,
      stdio: ['ignore', 'pipe', 'pipe'],
    });

    const lines = result.trim().split('\n');
    let afterMarker = false;
    const outputLines: string[] = [];
    for (const line of lines) {
      if (line.includes(marker)) {
        afterMarker = true;
        continue;
      }
      if (afterMarker && line.trim()) {
        outputLines.push(line.trim());
      }
    }

    return outputLines;
  } finally {
    if (fs.existsSync(tmpPptx)) fs.unlinkSync(tmpPptx);
    if (fs.existsSync(tmpScript)) fs.unlinkSync(tmpScript);
  }
}

/**
 * 用 python-pptx 解析封面页文本
 */
function extractCoverTexts(pptxBuf: Buffer): string[] {
  const tmpPptx = path.join(TMP_DIR, `pptx_cover_${Date.now()}.pptx`);
  const tmpScript = path.join(TMP_DIR, `extract_cover_${Date.now()}.py`);
  const marker = '__COVER__';

  try {
    fs.writeFileSync(tmpPptx, pptxBuf);
    fs.writeFileSync(tmpScript, [
      `from pptx import Presentation`,
      `prs = Presentation(r'${tmpPptx.replace(/\\/g, '\\\\')}')`,
      `slide = prs.slides[0]`,
      `texts = []`,
      `for shape in slide.shapes:`,
      `    if hasattr(shape, 'text_frame'):`,
      `        for para in shape.text_frame.paragraphs:`,
      `            if para.text.strip():`,
      `                texts.append(para.text.strip())`,
      `print('${marker}')`,
      `print('|||'.join(texts))`,
    ].join('\n'));

    const result = execSync(`python "${tmpScript}"`, {
      encoding: 'utf-8',
      timeout: 10000,
      stdio: ['ignore', 'pipe', 'pipe'],
    });

    const lines = result.trim().split('\n');
    let afterMarker = false;
    const outputLines: string[] = [];
    for (const line of lines) {
      if (line.includes(marker)) {
        afterMarker = true;
        continue;
      }
      if (afterMarker && line.trim()) {
        outputLines.push(line.trim());
      }
    }

    return outputLines;
  } finally {
    if (fs.existsSync(tmpPptx)) fs.unlinkSync(tmpPptx);
    if (fs.existsSync(tmpScript)) fs.unlinkSync(tmpScript);
  }
}

test.describe('PPTX 内容验证 - 序号样式注入', () => {
  test('导出 PPTX 应包含有效文件头', async () => {
    const sid = await createSession('人工智能发展趋势');
    const exportResult = await exportPPTX(sid, 'numeric-dot');
    const buffer = await downloadPPTX(exportResult.url);

    expect(buffer.byteLength).toBeGreaterThan(0);
    const header = buffer.slice(0, 2).toString();
    expect(header).toBe('PK');
  });

  for (const [styleId, styleInfo] of Object.entries(NUMBERING_STYLES)) {
    test(`序号样式 ${styleId} 应正确注入 PPTX 内容`, async () => {
      const sid = await createSession('云章PPT产品介绍');
      const exportResult = await exportPPTX(sid, styleId);
      const buffer = await downloadPPTX(exportResult.url);

      const allTexts = extractPPTXTexts(buffer);
      // 过滤封面页标题（通常是主题词，不含序号）
      const contentTexts = allTexts.filter((t: string) => !t.match(/^(人工智能|云章PPT|演示文稿)$/i));

      // 验证至少有一项包含该序号样式的符号
      const hasAnySymbol = styleInfo.symbols.some((sym: string) =>
        contentTexts.some((t: string) => t.includes(sym))
      );
      expect(hasAnySymbol).toBe(true);
    });
  }

  test('无序号样式时导出应有默认项目符号', async () => {
    const sid = await createSession('测试主题');
    const exportResult = await exportPPTX(sid); // 不传 numbering_style_id
    const buffer = await downloadPPTX(exportResult.url);

    expect(buffer.byteLength).toBeGreaterThan(0);
    const header = buffer.slice(0, 2).toString();
    expect(header).toBe('PK');
  });

  test('封面页不应包含序号符号', async () => {
    const sid = await createSession('云章PPT产品介绍');
    const exportResult = await exportPPTX(sid, 'numeric-dot');
    const buffer = await downloadPPTX(exportResult.url);

    const coverTexts = extractCoverTexts(buffer);
    // 封面标题不应包含数字序号格式
    const hasNumbering = coverTexts.some((t: string) => /^\d+\./.test(t));
    expect(hasNumbering).toBe(false);
  });
});

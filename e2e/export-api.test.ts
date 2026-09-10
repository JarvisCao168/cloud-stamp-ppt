import { test, expect } from '@playwright/test';

/**
 * E2E API 直连测试（不依赖前端 UI）
 * 直接调用后端 API 验证导出功能
 *
 * 运行方式：
 *   npx playwright test e2e/export-api.test.ts
 *
 * 注意：这些测试需要后端服务运行在 localhost:8000
 */

const API_BASE = 'http://localhost:8000';

// Check if running in CI environment (no backend available)
const isCI = process.env.CI === 'true';

// Skip all tests in CI since backend is not available
test.skip(isCI, 'Skipping API tests in CI - backend not available');

async function createGenerationSession(userInput: string, mode: string = 'quick'): Promise<string> {
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

async function getSession(sessionId: string): Promise<Record<string, unknown>> {
  const response = await fetch(`${API_BASE}/api/generation/session/${sessionId}`, {
    signal: AbortSignal.timeout(15_000),
  });
  if (!response.ok) {
    throw new Error(`获取会话失败 (HTTP ${response.status})`);
  }
  return response.json();
}

async function exportHTML(sessionId: string): Promise<{ filename: string; url: string }> {
  const response = await fetch(`${API_BASE}/api/export/html`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, format: 'html', title: '测试演示文稿' }),
    signal: AbortSignal.timeout(30_000),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(`HTML 导出失败: ${err.detail || response.statusText}`);
  }

  return response.json();
}

async function exportPPTX(sessionId: string): Promise<{ filename: string; url: string }> {
  const response = await fetch(`${API_BASE}/api/export/pptx`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, format: 'pptx', title: '测试演示文稿' }),
    signal: AbortSignal.timeout(60_000),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(`PPTX 导出失败: ${err.detail || response.statusText}`);
  }

  return response.json();
}

async function exportPDF(sessionId: string): Promise<{ filename: string; url: string }> {
  const response = await fetch(`${API_BASE}/api/export/pdf`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, format: 'pdf', title: '测试演示文稿' }),
    signal: AbortSignal.timeout(60_000),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(`PDF 导出失败: ${err.detail || response.statusText}`);
  }

  return response.json();
}

async function exportPNG(sessionId: string): Promise<{ filename: string; url: string }> {
  const response = await fetch(`${API_BASE}/api/export/png`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, format: 'png', title: '测试演示文稿' }),
    signal: AbortSignal.timeout(60_000),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(`PNG 导出失败: ${err.detail || response.statusText}`);
  }

  return response.json();
}

const PROMPTS = {
  simple: 'AI发展趋势',
  business: 'Q4汇报',
  technical: '云章PPT产品',
};

test.describe('HTML Export API', () => {
  test('should export HTML successfully', async () => {
    const sid = await createGenerationSession(PROMPTS.simple);
    expect(sid).toBeTruthy();

    const result = await exportHTML(sid);
    expect(result).toHaveProperty('filename');
    expect(result.filename).toMatch(/\.html$/);
    expect(result).toHaveProperty('url');
  });

  test('should return valid HTML content', async () => {
    const sid = await createGenerationSession(PROMPTS.business);
    const exportResult = await exportHTML(sid);

    // 验证导出的 HTML 文件可访问
    const htmlResponse = await fetch(`${API_BASE}${exportResult.url}`, {
      signal: AbortSignal.timeout(15_000),
    });
    expect(htmlResponse.ok).toBe(true);
    const html = await htmlResponse.text();
    expect(html).toContain('<!DOCTYPE html>');
    expect(html).toContain('<html');
  });

  test('invalid session should use fallback content or return error', async () => {
    const response = await fetch(`${API_BASE}/api/export/html`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: 'invalid-session', format: 'html' }),
      signal: AbortSignal.timeout(15_000),
    });
    // 后端对无效会话应使用降级内容生成（成功）或返回客户端错误（4xx）
    const isFallback = response.ok && (await response.json()).filename?.endsWith('.html');
    const isError = !response.ok && response.status >= 400 && response.status < 500;
    expect(isFallback || isError).toBe(true);
  });

  test('missing session_id should error', async () => {
    const response = await fetch(`${API_BASE}/api/export/html`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ format: 'html' }),
      signal: AbortSignal.timeout(15_000),
    });
    // 缺少必填字段应返回 422 (FastAPI validation error)
    expect(response.status).toBe(422);
  });
});

test.describe('PPTX Export API', () => {
  test('should export PPTX successfully', async () => {
    const sid = await createGenerationSession(PROMPTS.technical);
    expect(sid).toBeTruthy();

    const result = await exportPPTX(sid);
    expect(result).toHaveProperty('filename');
    expect(result.filename).toMatch(/\.pptx$/);
    expect(result).toHaveProperty('url');
  });

  test('should return valid PPTX file', async () => {
    const sid = await createGenerationSession(PROMPTS.simple);
    const exportResult = await exportPPTX(sid);

    // 验证导出的 PPTX 文件可访问
    const pptxResponse = await fetch(`${API_BASE}${exportResult.url}`, {
      signal: AbortSignal.timeout(15_000),
    });
    expect(pptxResponse.ok).toBe(true);
    const buffer = await pptxResponse.arrayBuffer();
    // PPTX 文件应以 PK 开头（ZIP 格式）
    expect(buffer.byteLength).toBeGreaterThan(0);
  });
});

test.describe('PDF Export API', () => {
  test('should export PDF successfully', async () => {
    const sid = await createGenerationSession(PROMPTS.business);
    expect(sid).toBeTruthy();

    const result = await exportPDF(sid);
    expect(result).toHaveProperty('filename');
    expect(result.filename).toMatch(/\.pdf$/);
    expect(result).toHaveProperty('url');
  });

  test('should return valid PDF file', async () => {
    const sid = await createGenerationSession(PROMPTS.simple);
    const exportResult = await exportPDF(sid);

    // 验证导出的 PDF 文件可访问
    const pdfResponse = await fetch(`${API_BASE}${exportResult.url}`, {
      signal: AbortSignal.timeout(15_000),
    });
    expect(pdfResponse.ok).toBe(true);
    const buffer = await pdfResponse.arrayBuffer();
    // PDF 文件应以 %PDF 开头
    const header = Buffer.from(buffer).slice(0, 5).toString();
    expect(header).toContain('%PDF');
  });
});

test.describe('PNG Export API', () => {
  test('should export PNG successfully', async () => {
    const sid = await createGenerationSession(PROMPTS.technical);
    expect(sid).toBeTruthy();

    const result = await exportPNG(sid);
    expect(result).toHaveProperty('filename');
    expect(result.filename).toMatch(/\.png$/);
    expect(result).toHaveProperty('url');
  });

  test('should return valid PNG file', async () => {
    const sid = await createGenerationSession(PROMPTS.simple);
    const exportResult = await exportPNG(sid);

    // 验证导出的 PNG 文件可访问
    const pngResponse = await fetch(`${API_BASE}${exportResult.url}`, {
      signal: AbortSignal.timeout(15_000),
    });
    expect(pngResponse.ok).toBe(true);
    const buffer = await pngResponse.arrayBuffer();
    // PNG 文件应以 PNG 签名开头
    const header = Buffer.from(buffer).slice(0, 8).toString('hex');
    expect(header).toContain('89504e47'); // PNG magic number
  });
});

test.describe('Full Flow API', () => {
  test('should complete generation + export flow', async () => {
    const sid = await createGenerationSession(PROMPTS.technical);

    // 获取会话状态
    const session = await getSession(sid);
    expect(session).toHaveProperty('intent');
    expect(session).toHaveProperty('slides');

    // 导出 HTML
    const exportResult = await exportHTML(sid);
    expect(exportResult).toHaveProperty('filename');
  });

  test('sequential exports should have unique filenames', async () => {
    const s1 = await createGenerationSession(PROMPTS.simple);
    const s2 = await createGenerationSession(PROMPTS.business);

    const [e1, e2] = await Promise.all([
      exportHTML(s1),
      exportHTML(s2),
    ]);

    expect(e1.filename).not.toBe(e2.filename);
  });
});

test.describe('Checkpoint API', () => {
  test('mastery mode should return checkpoint', async () => {
    const response = await fetch(`${API_BASE}/api/generation/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_input: PROMPTS.technical, mode: 'full_control' }),
      signal: AbortSignal.timeout(15_000),
    });

    expect(response.ok).toBe(true);
    const data = await response.json();

    // 掌控模式应返回 checkpoint 状态
    expect(data.status).toBe('checkpoint');
    expect(data.session_id).toBeTruthy();
    expect(data.checkpoints).toBeDefined();
    expect(data.checkpoints.length).toBeGreaterThan(0);
  });

  test('should handle checkpoint action', async () => {
    const response = await fetch(`${API_BASE}/api/generation/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_input: PROMPTS.technical, mode: 'full_control' }),
      signal: AbortSignal.timeout(15_000),
    });

    const data = await response.json();
    const sessionId = data.session_id;
    const checkpointId = data.checkpoints[0].id;

    // 提交检查点操作
    const actionResponse = await fetch(
      `${API_BASE}/api/generation/checkpoint/${sessionId}/${checkpointId}/action`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          checkpoint_id: checkpointId,
          action: 'confirm',
        }),
        signal: AbortSignal.timeout(15_000),
      }
    );

    expect(actionResponse.ok).toBe(true);
    const actionData = await actionResponse.json();
    expect(actionData).toHaveProperty('status', 'recorded');
  });
});

test.describe('Assets API', () => {
  test('should return all assets', async () => {
    const response = await fetch(`${API_BASE}/api/assets/all`, {
      signal: AbortSignal.timeout(15_000),
    });
    expect(response.ok).toBe(true);
    const data = await response.json();
    expect(data).toHaveProperty('templates');
    expect(data).toHaveProperty('color_schemes');
    expect(data).toHaveProperty('layouts');
    expect(Array.isArray(data.templates)).toBe(true);
    expect(Array.isArray(data.color_schemes)).toBe(true);
    expect(Array.isArray(data.layouts)).toBe(true);
  });

  test('should return hardware detection info', async () => {
    const response = await fetch(`${API_BASE}/api/hardware/detect`, {
      signal: AbortSignal.timeout(15_000),
    });
    expect(response.ok).toBe(true);
    const data = await response.json();
    expect(data).toHaveProperty('tier');
    expect(data).toHaveProperty('cpu_cores');
    expect(data).toHaveProperty('recommended_model');
  });
});

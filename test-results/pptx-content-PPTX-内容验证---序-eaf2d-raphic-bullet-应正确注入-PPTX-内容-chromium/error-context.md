# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: pptx-content.test.ts >> PPTX 内容验证 - 序号样式注入 >> 序号样式 graphic-bullet 应正确注入 PPTX 内容
- Location: e2e\pptx-content.test.ts:190:9

# Error details

```
TypeError: fetch failed
```

# Test source

```ts
  1   | import { test, expect } from '@playwright/test';
  2   | import { execSync } from 'child_process';
  3   | import * as fs from 'fs';
  4   | import * as path from 'path';
  5   | 
  6   | /**
  7   |  * E2E PPTX 内容验证测试
  8   |  * 验证导出 PPTX 文件中序号样式正确注入
  9   |  *
  10  |  * 运行方式：
  11  |  *   npx playwright test e2e/pptx-content.test.ts
  12  |  *
  13  |  * 依赖：后端服务运行在 localhost:8000
  14  |  */
  15  | 
  16  | const API_BASE = 'http://localhost:8000';
  17  | const isCI = process.env.CI === 'true';
  18  | test.skip(isCI, 'Skipping PPTX content tests in CI - backend not available');
  19  | 
  20  | // Windows-safe temp directory
  21  | const TMP_DIR = process.env.TEMP || '/tmp';
  22  | 
  23  | const NUMBERING_STYLES = {
  24  |   'numeric-dot': { symbols: ['1.', '2.', '3.'], name: '数字序号·' },
  25  |   'chinese-clause': { symbols: ['一、', '二、', '三、'], name: '中文顿号' },
  26  |   'graphic-bullet': { symbols: ['•', '‣', '⁃'], name: '项目符号' },
  27  |   'icon-check': { symbols: ['→', '✓', '✗'], name: '箭头图标' },
  28  | };
  29  | 
  30  | async function createSession(userInput: string, mode: string = 'quick'): Promise<string> {
> 31  |   const response = await fetch(`${API_BASE}/api/generation/create`, {
      |                    ^ TypeError: fetch failed
  32  |     method: 'POST',
  33  |     headers: { 'Content-Type': 'application/json' },
  34  |     body: JSON.stringify({ user_input: userInput, mode }),
  35  |     signal: AbortSignal.timeout(15_000),
  36  |   });
  37  |   if (!response.ok) {
  38  |     const err = await response.json().catch(() => ({}));
  39  |     throw new Error(`创建会话失败: ${err.detail || response.statusText}`);
  40  |   }
  41  |   const data = await response.json();
  42  |   return data.session_id;
  43  | }
  44  | 
  45  | async function exportPPTX(sessionId: string, numberingStyleId?: string): Promise<{ filename: string; url: string }> {
  46  |   const body: Record<string, unknown> = {
  47  |     session_id: sessionId,
  48  |     format: 'pptx',
  49  |     title: '测试演示文稿',
  50  |   };
  51  |   if (numberingStyleId) {
  52  |     body.numbering_style_id = numberingStyleId;
  53  |   }
  54  |   const response = await fetch(`${API_BASE}/api/export/pptx`, {
  55  |     method: 'POST',
  56  |     headers: { 'Content-Type': 'application/json' },
  57  |     body: JSON.stringify(body),
  58  |     signal: AbortSignal.timeout(60_000),
  59  |   });
  60  |   if (!response.ok) {
  61  |     const err = await response.json().catch(() => ({}));
  62  |     throw new Error(`PPTX 导出失败: ${err.detail || response.statusText}`);
  63  |   }
  64  |   return response.json() as Promise<{ filename: string; url: string }>;
  65  | }
  66  | 
  67  | async function downloadPPTX(url: string): Promise<Buffer> {
  68  |   const response = await fetch(`${API_BASE}${url}`, {
  69  |     signal: AbortSignal.timeout(15_000),
  70  |   });
  71  |   if (!response.ok) {
  72  |     throw new Error(`下载 PPTX 失败: HTTP ${response.status}`);
  73  |   }
  74  |   return Buffer.from(await response.arrayBuffer());
  75  | }
  76  | 
  77  | /**
  78  |  * 用 python-pptx 解析 PPTX 文件，提取所有段落文本。
  79  |  * 使用脚本文件而非 -c 内联执行，以兼容 Windows PowerShell 的编码问题。
  80  |  */
  81  | function extractPPTXTexts(pptxBuf: Buffer): string[] {
  82  |   const tmpPptx = path.join(TMP_DIR, `pptx_content_${Date.now()}.pptx`);
  83  |   const tmpScript = path.join(TMP_DIR, `extract_pptx_${Date.now()}.py`);
  84  |   const marker = '__TEXTS__';
  85  | 
  86  |   try {
  87  |     fs.writeFileSync(tmpPptx, pptxBuf);
  88  |     fs.writeFileSync(tmpScript, [
  89  |       `from pptx import Presentation`,
  90  |       `prs = Presentation(r'${tmpPptx.replace(/\\/g, '\\\\')}')`,
  91  |       `texts = []`,
  92  |       `for slide in prs.slides:`,
  93  |       `    for shape in slide.shapes:`,
  94  |       `        if hasattr(shape, 'text_frame'):`,
  95  |       `            for para in shape.text_frame.paragraphs:`,
  96  |       `                if para.text.strip():`,
  97  |       `                    texts.append(para.text.strip())`,
  98  |       `print('${marker}')`,
  99  |       `print('|||'.join(texts))`,
  100 |     ].join('\n'));
  101 | 
  102 |     const result = execSync(`python "${tmpScript}"`, {
  103 |       encoding: 'utf-8',
  104 |       timeout: 10000,
  105 |       stdio: ['ignore', 'pipe', 'pipe'],
  106 |     });
  107 | 
  108 |     const lines = result.trim().split('\n');
  109 |     let afterMarker = false;
  110 |     const outputLines: string[] = [];
  111 |     for (const line of lines) {
  112 |       if (line.includes(marker)) {
  113 |         afterMarker = true;
  114 |         continue;
  115 |       }
  116 |       if (afterMarker && line.trim()) {
  117 |         outputLines.push(line.trim());
  118 |       }
  119 |     }
  120 | 
  121 |     return outputLines;
  122 |   } finally {
  123 |     if (fs.existsSync(tmpPptx)) fs.unlinkSync(tmpPptx);
  124 |     if (fs.existsSync(tmpScript)) fs.unlinkSync(tmpScript);
  125 |   }
  126 | }
  127 | 
  128 | /**
  129 |  * 用 python-pptx 解析封面页文本
  130 |  */
  131 | function extractCoverTexts(pptxBuf: Buffer): string[] {
```
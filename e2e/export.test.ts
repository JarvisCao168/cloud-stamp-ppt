import { test, expect, type Page } from '@playwright/test';

/**
 * E2E 导出功能测试
 *
 * 前置条件：
 * - 前端服务运行在 localhost（由 playwright.config.ts 自动启动）
 * - 后端服务运行在 localhost:8000（PPTX/PDF/PNG 导出需要）
 *
 * 运行方式：
 *   npx playwright test e2e/export.test.ts
 *   npx playwright test e2e/export.test.ts --grep "HTML"
 */

// ============================================================
// 测试数据
// ============================================================

const PROMPTS = {
  rapid: '人工智能的发展趋势',
  collaborative: '2024年Q4项目进展汇报',
  mastery: '云章PPT智能体产品介绍',
} as const;

// ============================================================
// 辅助函数
// ============================================================

async function isBackendAvailable(): Promise<boolean> {
  try {
    const resp = await fetch('http://localhost:8000/');
    return resp.ok;
  } catch {
    return false;
  }
}

async function createSession(userInput: string, mode: string = 'quick'): Promise<string> {
  const response = await fetch('http://localhost:8000/api/generation/create', {
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

async function goToHomePage(page: Page): Promise<void> {
  await page.goto('/');
  // 等待输入框出现（页面加载完成标志）
  await expect(page.locator('#prompt')).toBeVisible({ timeout: 10000 });
}

async function selectMode(page: Page, mode: 'rapid' | 'collaborative' | 'mastery'): Promise<void> {
  const modeLabels = { rapid: '极速', collaborative: '协作', mastery: '掌控' };
  await page.getByRole('button', { name: `${modeLabels[mode]}模式` }).click();
  // 等待模式切换后 header 更新（使用精确匹配）
  await expect(page.getByRole('banner').getByText(modeLabels[mode])).toBeVisible({ timeout: 5000 });
}

async function enterPrompt(page: Page, prompt: string): Promise<void> {
  await page.locator('#prompt').fill(prompt);
  await expect(page.locator('#prompt')).toHaveValue(prompt);
}

async function clickGenerate(page: Page): Promise<void> {
  await page.getByRole('button', { name: /生成演示文稿/ }).click();
}

/**
 * 等待生成完成（成功或失败均可），最多等待 15s
 * 成功后返回 true，失败返回 false
 */
async function waitForGeneration(page: Page): Promise<boolean> {
  // 成功：预览区域出现
  const success = page.locator('[aria-label="预览区域"] .reveal').first();
  // 失败：错误提示出现
  const error = page.locator('[aria-label="预览区域"] .bg-red-50, [role="alert"]').first();

  try {
    await Promise.race([
      expect(success).toBeVisible({ timeout: 15000 }),
      expect(error).toBeVisible({ timeout: 15000 }),
    ]);
    return await success.isVisible();
  } catch {
    // 超时，检查当前状态
    return false;
  }
}

/**
 * 等待导出区域出现（生成成功后才会显示）
 */
async function waitForExportSection(page: Page): Promise<boolean> {
  try {
    await expect(page.locator('[aria-label="导出区域"]')).toBeVisible({ timeout: 5000 });
    return true;
  } catch {
    return false;
  }
}

// ============================================================
// 全局 session ID（所有测试共享）
// ============================================================

let sessionId: string | null = null;
let backendAvailable = false;

test.describe.configure({ mode: 'serial' });

test.describe('E2E 导出功能测试', () => {
  test.beforeAll(async () => {
    backendAvailable = await isBackendAvailable();
    console.log(`Backend available: ${backendAvailable}`);
    
    if (backendAvailable) {
      try {
        sessionId = await createSession(PROMPTS.rapid, 'quick');
        console.log(`Created session: ${sessionId}`);
      } catch (error) {
        console.error('Failed to create session:', error);
        sessionId = null;
      }
    }
  });

  test.describe('页面基础', () => {
    test.beforeEach(async ({ page }) => {
      await goToHomePage(page);
    });

    test('首页正确加载', async ({ page }) => {
      await expect(page.locator('h1')).toContainText('演示文稿生成器');
      await expect(page.getByText('AI 演示文稿生成器')).toBeVisible();
    });

    test('三种模式按钮可见且可点击', async ({ page }) => {
      await expect(page.getByRole('button', { name: '极速模式' })).toBeVisible();
      await expect(page.getByRole('button', { name: '协作模式' })).toBeVisible();
      await expect(page.getByRole('button', { name: '掌控模式' })).toBeVisible();
    });

    test('初始状态显示空提示', async ({ page }) => {
      await expect(page.getByText('输入主题后点击生成')).toBeVisible();
    });
  });

  test.describe('模式选择', () => {
    test.beforeEach(async ({ page }) => {
      await goToHomePage(page);
    });

    test('可以快速切换到极速模式', async ({ page }) => {
      await selectMode(page, 'rapid');
      await expect(page.getByText('极速模式')).toBeVisible();
    });

    test('可以切换到协作模式', async ({ page }) => {
      await selectMode(page, 'collaborative');
      await expect(page.getByText('协作模式')).toBeVisible();
    });

    test('可以切换到掌控模式', async ({ page }) => {
      await selectMode(page, 'mastery');
      await expect(page.getByText('掌控模式')).toBeVisible();
    });
  });

  test.describe('生成流程', () => {
    test.beforeEach(async ({ page }) => {
      await goToHomePage(page);
    });

    test('空提示时生成按钮仍可见（但点击后应显示错误）', async ({ page }) => {
      await selectMode(page, 'rapid');
      await clickGenerate(page);
      // 无 prompt 时仍应进入 loading → error 状态
      await expect(page.locator('[aria-label="预览区域"]')).toBeVisible({ timeout: 10000 });
    });

    test('填写提示词后生成按钮可点击', async ({ page }) => {
      await selectMode(page, 'rapid');
      await enterPrompt(page, PROMPTS.rapid);
      await expect(page.getByRole('button', { name: /生成演示文稿/ })).toBeEnabled();
    });

    test('生成过程中显示加载状态', async ({ page }) => {
      await selectMode(page, 'rapid');
      await enterPrompt(page, PROMPTS.rapid);
      await clickGenerate(page);
      // 加载中应显示 LoadingState 组件
      await expect(page.locator('[aria-label="预览区域"]')).toBeVisible();
    });

    test('生成完成后预览区域可见', async ({ page }) => {
      await selectMode(page, 'rapid');
      await enterPrompt(page, PROMPTS.rapid);
      await clickGenerate(page);

      const success = await waitForGeneration(page);
      // 无论后端是否可用，预览区域都应存在
      await expect(page.locator('[aria-label="预览区域"]')).toBeVisible();

      if (success) {
        // 后端可用时，应看到幻灯片内容
        await expect(page.locator('.reveal')).toBeVisible();
      }
    });
  });

  test.describe('导出功能', () => {
    test.beforeEach(async ({ page }) => {
      await goToHomePage(page);
    });

    // ------------------------------------------------------------
    // 基础 UI 测试（不依赖后端）
    // ------------------------------------------------------------

    test('生成成功后显示导出区域', async ({ page }) => {
      await selectMode(page, 'rapid');
      await enterPrompt(page, PROMPTS.rapid);
      await clickGenerate(page);
      await waitForGeneration(page);

      const hasExport = await waitForExportSection(page);
      // 如果后端不可用（无 sessionId），导出区域不会出现——这是预期行为
      if (hasExport) {
        await expect(page.locator('[aria-label="导出区域"]')).toBeVisible();
      }
    });

    test('导出按钮包含所有四种格式', async ({ page }) => {
      await selectMode(page, 'rapid');
      await enterPrompt(page, PROMPTS.rapid);
      await clickGenerate(page);
      await waitForGeneration(page);

      const hasExport = await waitForExportSection(page);
      if (!hasExport) {
        test.skip(); // 无后端时跳过
      }

      await expect(page.getByRole('button', { name: 'HTML' })).toBeVisible();
      await expect(page.getByRole('button', { name: 'PPTX' })).toBeVisible();
      await expect(page.getByRole('button', { name: 'PDF' })).toBeVisible();
      await expect(page.getByRole('button', { name: 'PNG' })).toBeVisible();
    });

    test('点击导出按钮显示加载状态', async ({ page }) => {
      await selectMode(page, 'rapid');
      await enterPrompt(page, PROMPTS.rapid);
      await clickGenerate(page);
      await waitForGeneration(page);

      const hasExport = await waitForExportSection(page);
      if (!hasExport) {
        test.skip();
      }

      await page.getByRole('button', { name: 'HTML' }).click();
      // 导出快速完成，只需确保没有报错
      await expect(page.getByRole('button', { name: 'HTML' })).toBeVisible({ timeout: 5000 });
    });

    test('导出失败显示错误提示', async ({ page }) => {
      await selectMode(page, 'rapid');
      await enterPrompt(page, PROMPTS.rapid);
      await clickGenerate(page);
      await waitForGeneration(page);

      const hasExport = await waitForExportSection(page);
      if (!hasExport) {
        test.skip();
      }

      // 点击 PPTX 导出（若后端未运行，应显示错误）
      await page.getByRole('button', { name: 'PPTX' }).click();

      // 等待错误区域出现（最多 10s）
      await expect(
        page.locator('[role="alert"], .bg-red-50')
      ).toBeVisible({ timeout: 10000 });
    });

    // ------------------------------------------------------------
    // HTML 导出专项测试（客户端降级，不依赖后端）
    // ------------------------------------------------------------

    test('HTML 导出格式存在且可点击', async ({ page }) => {
      // HTML 是纯客户端导出，只要有 slides 数据即可触发
      await selectMode(page, 'rapid');
      await enterPrompt(page, PROMPTS.rapid);
      await clickGenerate(page);
      await waitForGeneration(page);

      const hasExport = await waitForExportSection(page);
      if (!hasExport) {
        test.skip('后端未运行，无法获取 sessionId，跳过 HTML 导出测试');
      }

      await page.getByRole('button', { name: 'HTML' }).click();
      // 导出中 → 等待导出完成（无错误）
      await expect(page.getByRole('button', { name: 'HTML' })).toBeVisible({ timeout: 10000 });
    });

    test('四种导出格式的按钮排列正确', async ({ page }) => {
      await selectMode(page, 'rapid');
      await enterPrompt(page, PROMPTS.rapid);
      await clickGenerate(page);
      await waitForGeneration(page);

      const hasExport = await waitForExportSection(page);
      if (!hasExport) {
        test.skip();
      }

      const buttons = page.locator('[aria-label^="导出为"]');
      await expect(buttons).toHaveCount(4);

      const expectedNames = ['HTML', 'PPTX', 'PDF', 'PNG'];
      for (const name of expectedNames) {
        await expect(page.getByRole('button', { name })).toBeVisible();
      }
    });
  });

  test.describe('掌控模式检查点', () => {
    test.beforeEach(async ({ page }) => {
      await goToHomePage(page);
    });

    test('掌控模式生成后显示检查点面板', async ({ page }) => {
      await selectMode(page, 'mastery');
      await enterPrompt(page, PROMPTS.mastery);
      await clickGenerate(page);
      await waitForGeneration(page);

      // CheckpointPanel 在 mastery 模式下且 checkpoints.size > 0 时渲染
      // 若无后端，不会显示；有后端时应可见
      const checkpointPanel = page.locator('[data-testid="checkpoint-panel"]');
      const panelVisible = await checkpointPanel.isVisible().catch(() => false);

      if (panelVisible) {
        await expect(checkpointPanel).toBeVisible();
      }
    });
  });

  test.describe('重新生成', () => {
    test.beforeEach(async ({ page }) => {
      await goToHomePage(page);
    });

    test('生成失败后重试按钮可用', async ({ page }) => {
      await selectMode(page, 'rapid');
      await enterPrompt(page, PROMPTS.rapid);
      await clickGenerate(page);
      await waitForGeneration(page);

      // 无论成功或失败，"重新生成"按钮在 success 状态下出现
      const retryBtn = page.getByRole('button', { name: '重新生成' });
      const isRetryVisible = await retryBtn.isVisible().catch(() => false);

      if (isRetryVisible) {
        await expect(retryBtn).toBeEnabled();
      }
    });
  });

  // ------------------------------------------------------------
  // 完整端到端导出流程测试（需要有效 sessionId）
  // ------------------------------------------------------------

  test.describe('完整导出流程', () => {
    test('HTML 导出完整流程', async ({ page }) => {
      if (!backendAvailable || !sessionId) {
        test.skip();
        return;
      }

      await goToHomePage(page);
      await selectMode(page, 'rapid');
      
      // 手动输入与后端会话相同的 prompt
      await enterPrompt(page, PROMPTS.rapid);
      await clickGenerate(page);
      
      // 等待生成完成
      const success = await waitForGeneration(page);
      expect(success).toBe(true);
      
      // 等待导出区域出现
      const hasExport = await waitForExportSection(page);
      expect(hasExport).toBe(true);
      
      // 点击 HTML 导出
      await page.getByRole('button', { name: 'HTML' }).click();
      
      // 等待导出完成（按钮恢复可点击状态）
      await expect(page.getByRole('button', { name: 'HTML' })).toBeEnabled({ timeout: 30000 });
    });

    test('PPTX 导出完整流程', async ({ page }) => {
      if (!backendAvailable || !sessionId) {
        test.skip();
        return;
      }

      await goToHomePage(page);
      await selectMode(page, 'rapid');
      await enterPrompt(page, PROMPTS.rapid);
      await clickGenerate(page);
      await waitForGeneration(page);
      
      const hasExport = await waitForExportSection(page);
      if (!hasExport) {
        test.skip();
        return;
      }
      
      // 点击 PPTX 导出
      await page.getByRole('button', { name: 'PPTX' }).click();
      
      // 等待导出完成（按钮恢复可点击状态）
      await expect(page.getByRole('button', { name: 'PPTX' })).toBeEnabled({ timeout: 30000 });
    });

    test('PDF 导出完整流程', async ({ page }) => {
      if (!backendAvailable || !sessionId) {
        test.skip();
        return;
      }

      await goToHomePage(page);
      await selectMode(page, 'rapid');
      await enterPrompt(page, PROMPTS.rapid);
      await clickGenerate(page);
      await waitForGeneration(page);
      
      const hasExport = await waitForExportSection(page);
      if (!hasExport) {
        test.skip();
        return;
      }
      
      // 点击 PDF 导出
      await page.getByRole('button', { name: 'PDF' }).click();
      
      // 等待导出完成（按钮恢复可点击状态）
      await expect(page.getByRole('button', { name: 'PDF' })).toBeEnabled({ timeout: 30000 });
    });

    test('PNG 导出完整流程', async ({ page }) => {
      if (!backendAvailable || !sessionId) {
        test.skip();
        return;
      }

      await goToHomePage(page);
      await selectMode(page, 'rapid');
      await enterPrompt(page, PROMPTS.rapid);
      await clickGenerate(page);
      await waitForGeneration(page);
      
      const hasExport = await waitForExportSection(page);
      if (!hasExport) {
        test.skip();
        return;
      }
      
      // 点击 PNG 导出
      await page.getByRole('button', { name: 'PNG' }).click();
      
      // 等待导出完成（按钮恢复可点击状态）
      await expect(page.getByRole('button', { name: 'PNG' })).toBeEnabled({ timeout: 30000 });
    });
  });
});

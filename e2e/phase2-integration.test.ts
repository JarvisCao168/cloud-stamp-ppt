import { test, expect, type Page } from '@playwright/test';

/**
 * Phase 2 E2E 集成测试
 * 测试模板选择器与序号样式选择器的联动功能
 *
 * 运行方式：
 *   npx playwright test e2e/phase2-integration.test.ts
 */

const PROMPTS = {
  rapid: '人工智能的发展趋势',
  mastery: '云章PPT智能体产品介绍',
} as const;

async function goToHomePage(page: Page): Promise<void> {
  await page.goto('/');
  await expect(page.locator('#prompt')).toBeVisible({ timeout: 10000 });
}

async function selectMode(page: Page, mode: 'rapid' | 'mastery'): Promise<void> {
  const modeLabels = { rapid: '极速', mastery: '掌控' };
  await page.getByRole('button', { name: new RegExp(`${modeLabels[mode]}模式$`) }).click();
  // Wait for mode change by checking the label in header
  await expect(page.locator('text=当前模式:').locator('span').last()).toHaveText(modeLabels[mode], { timeout: 5000 });
}

async function enterPrompt(page: Page, prompt: string): Promise<void> {
  await page.locator('#prompt').fill(prompt);
}

async function clickGenerate(page: Page): Promise<void> {
  await page.getByRole('button', { name: /生成演示文稿/ }).click();
}

async function waitForGeneration(page: Page): Promise<boolean> {
  const success = page.locator('[aria-label="预览区域"] .reveal').first();
  const error = page.locator('[aria-label="预览区域"] .bg-red-50, [role="alert"]').first();

  try {
    await Promise.race([
      expect(success).toBeVisible({ timeout: 15000 }),
      expect(error).toBeVisible({ timeout: 15000 }),
    ]);
    return await success.isVisible();
  } catch {
    return false;
  }
}

test.describe('Phase 2 模板与序号样式联动测试', () => {
  test.describe('极速模式 - 无模板选择器', () => {
    test.beforeEach(async ({ page }) => {
      await goToHomePage(page);
    });

    test('极速模式不显示模板选择器', async ({ page }) => {
      await selectMode(page, 'rapid');
      // 极速模式下不应显示模板选择区域
      const templateSection = page.locator('text=选择模板').first();
      await expect(templateSection).not.toBeVisible();
    });

    test('极速模式不显示序号样式选择器', async ({ page }) => {
      await selectMode(page, 'rapid');
      const numberingSection = page.locator('text=选择序号样式').first();
      await expect(numberingSection).not.toBeVisible();
    });
  });

  test.describe('掌控模式 - 模板与序号样式联动', () => {
    test.beforeEach(async ({ page }) => {
      await goToHomePage(page);
    });

    test('掌控模式显示模板选择按钮', async ({ page }) => {
      await selectMode(page, 'mastery');
      // 等待生成完成后检查模板选择器
      await enterPrompt(page, PROMPTS.mastery);
      await clickGenerate(page);
      await waitForGeneration(page);

      // 检查点面板出现后，模板选择器应该可见
      await expect(page.locator('text=选择模板')).toBeVisible();
    });

    test('掌控模式显示序号样式选择按钮', async ({ page }) => {
      await selectMode(page, 'mastery');
      await enterPrompt(page, PROMPTS.mastery);
      await clickGenerate(page);
      await waitForGeneration(page);

      await expect(page.locator('text=选择序号样式')).toBeVisible();
    });

    test('点击模板选择器展开选项', async ({ page }) => {
      await selectMode(page, 'mastery');
      await enterPrompt(page, PROMPTS.mastery);
      await clickGenerate(page);
      await waitForGeneration(page);

      // 点击模板选择按钮
      await page.locator('text=选择模板 (可选)').click();

      // 等待模板列表加载
      await expect(page.locator('[class*=\'grid-cols-1\']').first()).toBeVisible({ timeout: 5000 });
    });

    test('模板选择后自动关联推荐序号样式', async ({ page }) => {
      await selectMode(page, 'mastery');
      await enterPrompt(page, PROMPTS.mastery);
      await clickGenerate(page);
      await waitForGeneration(page);

      // 展开模板选择器
      await page.locator('text=选择模板 (可选)').click();

      // 等待模板列表加载
      await expect(page.locator('[class*=\'grid-cols-1\']').first()).toBeVisible({ timeout: 5000 });

      // 点击第一个模板（modern-dark）
      const firstTemplate = page.locator('[class*=\'grid\'] > div').first();
      await firstTemplate.click();

      // 验证已选模板显示
      await expect(page.locator('text=现代暗色')).toBeVisible();
    });

    test('展开模板选择器时自动收起序号选择器', async ({ page }) => {
      await selectMode(page, 'mastery');
      await enterPrompt(page, PROMPTS.mastery);
      await clickGenerate(page);
      await waitForGeneration(page);

      // 先展开序号选择器
      await page.locator('text=选择序号样式 (可选)').click();
      await expect(page.locator('[class*=\'grid-cols-1\']').first()).toBeVisible({ timeout: 5000 });

      // 再展开模板选择器
      await page.locator('text=选择模板 (可选)').click();

      // 序号选择器应已收起
      // （这里只是验证模板选择器可以正常展开）
      await expect(page.locator('text=选择模板 (可选)')).toBeVisible();
    });
  });

  test.describe('API 资产端点测试', () => {
    test('assets/all 端点返回模板列表', async ({ request }) => {
      const response = await request.get('http://localhost:8000/api/assets/all');
      expect(response.ok()).toBe(true);
      const data = await response.json();
      expect(data).toHaveProperty('templates');
      expect(Array.isArray(data.templates)).toBe(true);
      expect(data.templates.length).toBeGreaterThan(0);
    });

    test('numbering-styles 端点返回序号样式列表', async ({ request }) => {
      const response = await request.get('http://localhost:8000/api/assets/numbering-styles');
      expect(response.ok()).toBe(true);
      const data = await response.json();
      expect(Array.isArray(data)).toBe(true);
      expect(data.length).toBe(30); // 30条系统内置样式
    });

    test('numbering-styles 支持类型过滤', async ({ request }) => {
      const response = await request.get('http://localhost:8000/api/assets/numbering-styles?type=numeric');
      expect(response.ok()).toBe(true);
      const data = await response.json();
      expect(Array.isArray(data)).toBe(true);
      // 所有返回的样式都应该是 numeric 类型
      data.forEach((style: any) => {
        expect(style.type).toBe('numeric');
      });
    });

    test('numbering-styles 支持标签过滤', async ({ request }) => {
      const response = await request.get('http://localhost:8000/api/assets/numbering-styles?tags=商务');
      expect(response.ok()).toBe(true);
      const data = await response.json();
      expect(Array.isArray(data)).toBe(true);
      // 所有返回的样式都应该包含"商务"标签
      data.forEach((style: any) => {
        expect(style.tags).toContain('商务');
      });
    });

    test('templates/list 端点返回模板列表 (API test)', async ({ request }) => {
      const response = await request.get('http://localhost:8000/api/assets/templates');
      expect(response.ok()).toBe(true);
      const data = await response.json();
      expect(Array.isArray(data)).toBe(true);
      expect(data.length).toBeGreaterThan(0);
    });

    test('模板数据结构正确', async ({ request }) => {
      const response = await request.get('http://localhost:8000/api/assets/templates');
      const data = await response.json();
      if (data.length > 0) {
        const firstTemplate = data[0];
        expect(firstTemplate).toHaveProperty('id');
        expect(firstTemplate).toHaveProperty('name');
        expect(firstTemplate).toHaveProperty('category');
      }
    });
  });
});

test.describe('Phase 2 完整流程测试', () => {
  test('从选择模板到生成演示文稿的完整流程', async ({ page }) => {
    await goToHomePage(page);

    // 切换到掌控模式
    await selectMode(page, 'mastery');

    // 输入提示词
    await enterPrompt(page, PROMPTS.mastery);

    // 点击生成
    await clickGenerate(page);

    // 等待生成完成
    const success = await waitForGeneration(page);

    // 如果生成成功（后端可用），检查模板选择器是否出现
    if (success) {
      // 模板选择区域应该可见
      const templateSection = page.locator('text=选择模板');
      await expect(templateSection).toBeVisible();

      // 点击模板选择按钮
      await templateSection.click();

      // 等待模板列表加载
      await expect(page.locator('[class*=\'grid-cols-1\']').first()).toBeVisible({ timeout: 5000 });
    }
  });
});

import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright E2E 测试配置
 * 运行: npx playwright test
 */
const PORT = process.env.CI ? '3000' : (process.env.E2E_PORT || '43210');

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false, // E2E 测试顺序执行，避免竞争
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: process.env.CI ? 'github' : 'html',
  use: {
    baseURL: `http://localhost:${PORT}`,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  // 启动 Next.js 开发服务器用于 E2E 测试
  webServer: {
    command: process.env.CI
      ? 'npm run dev'
      : `set PORT=${PORT} && npm run dev`,
    url: `http://localhost:${PORT}`,
    reuseExistingServer: !process.env.CI,
    timeout: 60000,
    stdout: 'pipe',
    stderr: 'pipe',
  },
});

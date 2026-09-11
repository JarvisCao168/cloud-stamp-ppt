# 云章PPT智能体系统

AI 驱动的 PPT 智能生成平台，支持三种操作模式（极速/协作/掌控），提供 HTML/PPTX/PDF/PNG 多格式导出。

[![CI](https://github.com/WORKSPACE/yunzhang-ppt/actions/workflows/ci.yml/badge.svg)](https://github.com/WORKSPACE/yunzhang-ppt/actions)
![Coverage](https://img.shields.io/badge/coverage-93.57%25-brightgreen)
![License](https://img.shields.io/badge/license-MIT-blue)

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端框架 | Next.js 15 (App Router) |
| UI 库 | React 19 + TypeScript 5 |
| 样式 | TailwindCSS 4 |
| 测试 | Vitest + Testing Library（单元）+ Playwright（E2E） |
| 容器化 | Docker + Docker Compose |
| CI/CD | GitHub Actions |

## 快速开始

```bash
# 安装依赖
npm install

# 启动开发服务器（前端 localhost:3000）
npm run dev

# 启动后端（需 uvicorn 环境）
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Docker 一键启动（需 Docker Desktop）
docker-compose up -d
```

## 三种操作模式

| 模式 | 说明 | 适用场景 |
|------|------|---------|
| **极速模式** | AI 自动生成完整 PPT，无需人工干预 | 快速原型、日常汇报 |
| **协作模式** | AI 生成初稿后，人工确认关键检查点 | 正式报告、团队协作 |
| **掌控模式** | 全链路人工审核，每个检查点需手动确认 | 重要演示、对外发布 |

## 导出格式

- **HTML** — 网页演示，支持 reveal.js 全屏放映
- **PPTX** — PowerPoint 原生格式
- **PDF** — 打印/分发标准格式
- **PNG** — 单页图片导出

## 项目结构

```
D:\yzppt\
├── app/                          # Next.js 应用目录
│   ├── page.tsx                  # 主页面
│   ├── layout.tsx                # 布局组件
│   ├── api.ts                    # API 客户端（统一封装）
│   ├── export.ts                 # 导出引擎
│   ├── generationStore.ts        # 生成状态管理（Zustand）
│   ├── checkpoints.ts            # 检查点逻辑
│   └── components/               # UI 组件
│       ├── ModeSelector.tsx
│       ├── CheckpointPanel.tsx
│       ├── RevealContainer.tsx
│       ├── LoadingState.tsx
│       └── ErrorMessage.tsx
├── __mocks__/                    # Mock 数据
├── __tests__/                    # 单元测试（Vitest）
├── e2e/                          # E2E 测试（Playwright）
├── public/                       # 静态资源
├── .github/workflows/ci.yml      # CI 流水线
├── Dockerfile                    # 前端生产镜像
├── docker-compose.yml            # 前后端编排
└── package.json
```

## 测试

```bash
# 运行所有单元测试
npm run test

# 运行测试并生成覆盖率报告
npm run test:ci

# 运行 E2E 测试
npm run test:e2e

# E2E UI 模式（可视化交互）
npm run test:e2e:ui

# 构建验证（lint + tsc + build）
npm run build:verify
```

### 测试覆盖

| 模块 | 语句覆盖率 |
|------|-----------|
| `generationStore.ts` | 100% |
| `CheckpointPanel.tsx` | 100% |
| `ModeSelector.tsx` | 100% |
| `export.ts` | 100% |
| `checkpoints.ts` | 100% |
| `api.ts` | 96.87% |
| **整体** | **93.57%** |

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/api/assets/all` | 获取所有模板/配色/布局资产 |
| POST | `/api/generation/create` | 创建生成任务 |
| GET | `/api/generation/session/{id}` | 查询会话状态 |
| POST | `/api/generation/checkpoint/{sid}/{cid}/action` | 确认/拒绝检查点 |
| POST | `/api/export/html` | 导出 HTML |
| POST | `/api/export/pptx` | 导出 PPTX |
| POST | `/api/export/pdf` | 导出 PDF |
| POST | `/api/export/png` | 导出 PNG |

> 开发模式下，前端通过 `next.config.ts` 代理 `/api/*` → `localhost:8000`

## 环境变量

```bash
# .env.local（可选，本地开发）
NEXT_PUBLIC_API_BASE=http://localhost:8000
AI_API_KEY=your-key-here    # 后端 AI 服务密钥
```

## 部署

### Vercel（推荐）

一键部署到 Vercel，自动连接 GitHub 仓库实现 CI/CD。

### Docker

```bash
docker-compose up -d
# 前端: http://localhost:3000
# 后端: http://localhost:8000
```

## 文档索引

### 核心文档
- `README.md` — 项目概览与快速开始
- `DEVELOPMENT.md` — 开发规范与架构说明
- `TEAM-CHARTER.md` — 团队章程与协作规则
- `STATUS.md` — 当前状态与进度追踪
- `TODOLIST.md` — 任务清单
- `BLOCKERS.md` — 阻塞问题记录

### 研究文档（docs/）
- `competitive-analysis-v2.md` — 竞品分析报告（Kimi PPT 8.3分登顶）
- `kimi-ppt-review.md` — Kimi PPT 详细评测
- `ai-ppt-competitive-analysis.md` — AI PPT 竞品综合分析
- `market-research-report-integrated.md` — 市场调研综合报告
- `user-feedback-summary-round4.md` — 用户反馈总结（170+条）
- `user-feedback-raw.csv` — 原始反馈数据

## 团队

| 成员 | 角色 | 职责 |
|------|------|------|
| Hermes | 组长 | 任务分解、进度控制、验收交付 |
| Claude | 首席架构师 | 核心逻辑攻坚、复杂重构、Bug 排查 |
| Codex | 工程总监 | 自动化测试、CI/CD、覆盖率保障 |

---

*本文档由云章PPT智能体开发工作组维护*

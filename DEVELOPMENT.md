# 云章PPT智能体系统 - 开发规范

**版本**: v1.0  
**更新日期**: 2025-09-10

---

## 技术栈

- **前端框架**: Next.js 15 (App Router)
- **UI库**: React 19
- **语言**: TypeScript 5
- **样式**: TailwindCSS 4
- **测试**: Vitest + Testing Library
- **容器化**: Docker + Docker Compose
- **CI/CD**: GitHub Actions

---

## 项目结构

```
D:\yzppt\
├── app/                    # Next.js应用目录
│   ├── page.tsx           # 主页面
│   ├── layout.tsx         # 布局组件
│   ├── api.ts             # API客户端
│   ├── checkpoints.ts     # 检查点逻辑
│   ├── export.ts          # 导出引擎
│   ├── generationStore.ts # 生成状态管理
│   └── components/        # UI组件
├── __tests__/             # 测试文件
├── __mocks__/             # Mock数据
├── public/                # 静态资源
├── .github/workflows/     # CI配置
├── package.json
├── tsconfig.json
├── docker-compose.yml
└── Dockerfile
```

---

## 编码规范

### TypeScript
- 使用严格模式 (`strict: true`)
- 避免使用 `any`，优先使用 `unknown`
- 组件Props必须定义接口

### React
- 使用Function Components + Hooks
- 避免在组件内定义外部函数
- 使用React 19最佳实践

### 测试
- 每个模块必须有对应测试
- 覆盖率目标：核心模块 ≥60%
- 使用Testing Library进行组件测试

---

## 工作流程

### 1. 开发流程
1. 从master拉取最新代码
2. 创建功能分支 `feature/xxx`
3. 开发并编写测试
4. 提交PR，等待审查
5. 合并到master

### 2. 测试流程
```bash
# 运行测试
npm run test

# 运行测试并生成覆盖率报告
npm run test:ci

# 构建验证
npm run build:verify
```

### 3. 部署流程
```bash
# 本地开发
npm run dev

# Docker启动
docker-compose up -d

# 生产构建
npm run build && docker build -t yzppt .
```

---

## API规范

### 前端API调用
- 所有API调用通过 `app/api.ts` 统一封装
- 错误处理统一返回 `ApiResult<T>` 类型
- 支持极速/协作/掌控三种模式

### 后端API路由
- 基础路径: `/api/`
- 生成接口: `/api/generation/create`
- 导出接口: `/api/export/*`
- 检查点: `/api/checkpoints/*`

---

## 质量标准

| 指标 | 目标 | 当前 |
|------|------|------|
| 测试覆盖率 | ≥60% | **93.57%** ✅ |
| ESLint错误 | 0 | **0** ✅ |
| TypeScript错误 | 0 | **0** ✅ |
| 测试通过率 | 100% | **100%** ✅ |

---

## 团队协作

### 沟通规则
- 每小时进度同步
- 问题及时升级
- 简洁高效沟通

### 任务分配
- Hermes: 统筹、核心开发
- Claude: 架构、代码审查
- Codex: 测试、CI/CD
- OpenCode: ~~前端组件~~ (已下线)

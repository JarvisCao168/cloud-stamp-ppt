# OpenCode 沟通问题诊断报告

## 问题现象
OpenCode 的消息持续显示错误：`Error: OpenCode exited with code 1: 命令行太长`

## 根本原因分析

### 1. Windows 命令行长度限制
- Windows 命令行参数总长度有限制（通常约 8191 字符）
- OpenCode 作为子代理被启动时，传入的参数（包括工作目录、配置文件路径等）可能超出限制
- 这是 Windows 平台的固有约束，不是 Hermes 的 bug

### 2. 当前项目状态
- **前端测试**: 79 个测试全部通过
- **后端服务**: ❌ 未运行（localhost:8000 拒绝连接）
- **导出功能**: 后端路由已实现 (`/api/export/html`, `/api/export/pptx`, `/api/export/pdf`)
- **API 代理**: Next.js 开发模式已配置 `/api/*` → `localhost:8000`

### 3. 影响范围
- OpenCode 无法接收和显示消息
- 团队协作中 OpenCode 的分工任务（导出 UI 集成）无法推进
- 其他代理（Claude, Codex）正常工作

## 解决方案建议

### 立即方案
1. **JARVIS 规则已生效**: 将长内容保存为 markdown 附件发送
2. **简化 OpenCode 的启动参数**: 减少传入的环境变量和配置路径长度

### 中期方案
1. 检查 OpenCode 的启动配置，精简参数
2. 考虑使用配置文件替代命令行参数传递大量配置
3. 评估是否需要在 WSL2 环境下运行以规避 Windows 命令行限制

### 后端启动建议
后端服务未运行，需要启动后才能进行端到端测试：
```bash
cd C:/Users/Administrator/Desktop/yunzhang-ppt
docker compose up -d
```

## 当前阻塞项
| 问题 | 状态 | 负责人 |
|------|------|--------|
| OpenCode 命令行长度限制 | 已知问题 | JARVIS/Hermes |
| 后端服务未启动 | 待处理 | Hermes |
| 导出功能端到端测试 | 阻塞于后端 | OpenCode |
| UI 组件测试补充 | 待进行 | Codex/OpenCode |

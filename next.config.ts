import type { NextConfig } from "next";

const isDev = process.env.NODE_ENV === 'development';

// 后端地址：默认 8001（当前运行中的后端实例，8000 有残留进程无法清理）。
// 可通过 NEXT_PUBLIC_BACKEND_URL 环境变量覆盖，例如 http://127.0.0.1:8000。
const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8001';

const nextConfig: NextConfig = {
  async rewrites() {
    // 开发环境：将 /api/* 代理到后端 FastAPI
    // 生产环境：由部署层（Nginx/Docker）处理反向代理
    if (isDev) {
      return [
        {
          source: '/api/:path*',
          destination: `${BACKEND_URL}/api/:path*`,
        },
      ];
    }
    return [];
  },
};

export default nextConfig;

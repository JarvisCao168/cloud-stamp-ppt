import type { NextConfig } from "next";

const isDev = process.env.NODE_ENV === 'development';

const nextConfig: NextConfig = {
  async rewrites() {
    // 开发环境：将 /api/* 代理到后端 FastAPI
    // 生产环境：由部署层（Nginx/Docker）处理反向代理
    if (isDev) {
      return [
        {
          source: '/api/:path*',
          destination: 'http://localhost:8000/api/:path*',
        },
      ];
    }
    return [];
  },
};

export default nextConfig;

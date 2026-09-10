"""云章PPT后端启动脚本。

用法:
  python start_backend.py          # 后台启动（无 reload）
  python start_backend.py --reload # 开发模式（自动重载）

后端服务运行在 http://localhost:8000
API 文档: http://localhost:8000/docs
"""

import sys
import os

# 将 backend/ 添加到 Python 路径
BACKEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import uvicorn


def start(reload: bool = False):
    """启动 FastAPI 后端服务。"""
    cmd = [
        sys.executable, "-m", "uvicorn",
        "app.main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--app-dir", BACKEND_DIR,
    ]
    if reload:
        cmd.append("--reload")

    print(f"Starting backend at http://localhost:8000")
    print(f"App dir: {BACKEND_DIR}")
    print(f"Command: {' '.join(cmd)}")
    print()

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, app_dir=BACKEND_DIR, reload=reload)


if __name__ == "__main__":
    reload = "--reload" in sys.argv
    start(reload=reload)

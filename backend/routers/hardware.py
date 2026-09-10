"""硬件检测接口路由。

GET /api/hardware/detect  — 返回当前设备信息（用于推荐模型）
"""

from __future__ import annotations

import os
from fastapi import APIRouter

from backend.types import HardwareInfo

router = APIRouter()


@router.get("/hardware/detect", response_model=HardwareInfo)
async def detect_hardware() -> HardwareInfo:
    cpu_count = os.cpu_count() or 4
    mem_gb = _get_memory_gb()

    if cpu_count >= 16 and mem_gb >= 32:
        tier = "high"
        model = "claude-opus-5"
    elif cpu_count >= 8 and mem_gb >= 16:
        tier = "medium"
        model = "claude-sonnet-5"
    else:
        tier = "low"
        model = "claude-haiku-4-5-2051001"

    return HardwareInfo(
        tier=tier,
        cpu_cores=cpu_count,
        recommended_model=model,
    )


def _get_memory_gb() -> int:
    """获取系统总内存（GB），跨平台兼容。"""
    try:
        import psutil
        return psutil.virtual_memory().total // (1024 ** 3)
    except ImportError:
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_uint64),
                    ("ullAvailPhys", ctypes.c_uint64),
                    ("ullTotalPageFile", ctypes.c_uint64),
                    ("ullAvailPageFile", ctypes.c_uint64),
                    ("ullTotalVirtual", ctypes.c_uint64),
                    ("ullAvailVirtual", ctypes.c_uint64),
                    ("ullAvailExtendedVirtual", ctypes.c_uint64),
                ]
            info = MEMORYSTATUSEX()
            info.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            kernel32.GlobalMemoryStatusEx(ctypes.byref(info))
            return info.ullTotalPhys // (1024 ** 3)
        except Exception:
            return 8

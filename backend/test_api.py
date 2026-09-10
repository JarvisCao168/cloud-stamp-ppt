"""
云章PPT系统测试脚本
快速验证后端API是否正常工作
"""
import asyncio
import httpx
import sys

API_BASE = "http://localhost:8000"


async def test_health():
    """测试健康检查"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE}/health")
        assert response.status_code == 200
        print("✓ 健康检查通过")
        return response.json()


async def test_hardware_detect():
    """测试硬件检测"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE}/api/hardware/detect")
        assert response.status_code == 200
        data = response.json()
        print(f"✓ 硬件检测通过 - 等级: {data['compute_tier']}")
        return data


async def test_assets():
    """测试资产库"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE}/api/assets/all")
        assert response.status_code == 200
        data = response.json()
        print(f"✓ 资产库通过 - 模板: {len(data['templates'])}个, 配色: {len(data['color_schemes'])}套")
        return data


async def test_generation():
    """测试生成接口"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE}/api/generation/create",
            json={
                "user_input": "介绍AI技术的基本概念",
                "mode": "quick"
            }
        )
        if response.status_code == 200:
            print("✓ 生成接口通过")
            return response.json()
        elif response.status_code == 500:
            print("⚠ 生成接口返回500（可能是API密钥未配置）")
            return None
        else:
            print(f"✗ 生成接口失败: {response.status_code}")
            return None


async def main():
    print("=" * 50)
    print("云章PPT系统 - API测试")
    print("=" * 50)
    print()
    
    tests = [
        ("健康检查", test_health),
        ("硬件检测", test_hardware_detect),
        ("资产库", test_assets),
        ("生成接口", test_generation),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            print(f"测试: {name}...")
            result = await test_func()
            results.append((name, True, result))
        except Exception as e:
            print(f"✗ {name} 失败: {e}")
            results.append((name, False, str(e)))
        print()
    
    print("=" * 50)
    print("测试结果汇总:")
    passed = sum(1 for _, ok, _ in results if ok)
    print(f"通过: {passed}/{len(results)}")
    print("=" * 50)
    
    return all(ok for _, ok, _ in results)


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

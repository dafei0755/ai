"""
快速检查 Playwright 浏览器是否已正确安装
"""
import sys


def check_playwright_installation():
    """检查 Playwright 和 Chromium 浏览器安装状态"""
    print("=" * 60)
    print("Playwright 安装状态检查")
    print("=" * 60)

    # 1. 检查 Python 版本
    print(f"\n1. Python 版本: {sys.version}")
    print(f"   平台: {sys.platform}")

    # 2. 检查 Playwright 包
    try:
        import playwright

        print(f"\n2. ✅ Playwright 已安装")
        try:
            print(f"   版本: {playwright.__version__}")
        except AttributeError:
            print(f"   版本: (无法获取版本号)")
    except ImportError:
        print(f"\n2. ❌ Playwright 未安装")
        print("   安装命令: pip install playwright")
        return False

    # 3. 检查 Chromium 浏览器
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            executable = p.chromium.executable_path
            print(f"\n3. ✅ Chromium 浏览器已安装")
            print(f"   路径: {executable}")
    except Exception as e:
        print(f"\n3. ❌ Chromium 浏览器未安装或无法访问")
        print(f"   错误: {e}")
        print("   安装命令: python -m playwright install chromium")
        return False

    # 4. 检查事件循环策略（Python 3.13+）
    if sys.version_info >= (3, 13) and sys.platform == "win32":
        import asyncio

        policy = type(asyncio.get_event_loop_policy()).__name__
        print(f"\n4. 事件循环策略: {policy}")
        if policy == "WindowsProactorEventLoopPolicy":
            print("   ⚠️ 当前使用 ProactorEventLoop（不支持子进程）")
            print("   建议: 在 server.py 开头设置 WindowsSelectorEventLoopPolicy")
        elif policy == "WindowsSelectorEventLoopPolicy":
            print("   ✅ 当前使用 SelectorEventLoop（支持子进程）")

    print("\n" + "=" * 60)
    print("✅ 所有检查通过！Playwright 已正确安装。")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = check_playwright_installation()
    sys.exit(0 if success else 1)

"""
测试 Playwright 浏览器池初始化和 PDF 生成功能

验证点：
1. Playwright 浏览器池能否正常初始化
2. Chromium 浏览器是否已安装
3. PDF 生成功能是否正常工作
4. 服务器启动集成测试
"""
import asyncio
import sys
from pathlib import Path

# [WARN] 关键：必须在所有异步导入之前设置
# Playwright 需要子进程支持，必须使用 Proactor 而非 Selector
if sys.platform == "win32" and sys.version_info >= (3, 13):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    print("[OK] WindowsProactorEventLoopPolicy set for Python 3.13+ Windows (supports subprocesses)")


async def test_browser_pool():
    """测试浏览器池初始化"""
    print("\n" + "=" * 60)
    print("[EMOJI] 测试1: Playwright 浏览器池初始化")
    print("=" * 60)

    try:
        from intelligent_project_analyzer.api.html_pdf_generator import get_browser_pool

        # 获取浏览器池实例
        pool = get_browser_pool()
        print("[OK] 浏览器池实例创建成功")

        # 初始化浏览器
        await pool.initialize()
        print("[OK] Playwright 浏览器池初始化成功")

        # 获取浏览器实例
        browser = await pool.get_browser()
        print(f"[OK] 获取浏览器实例成功: {browser}")
        print(f"   - 浏览器类型: {browser.browser_type.name}")
        print(f"   - 是否连接: {browser.is_connected()}")

        return True

    except Exception as e:
        print(f"[FAIL] 浏览器池初始化失败: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_pdf_generation():
    """测试 PDF 生成功能"""
    print("\n" + "=" * 60)
    print("[EMOJI] 测试2: PDF 生成功能")
    print("=" * 60)

    try:
        from intelligent_project_analyzer.api.html_pdf_generator import get_browser_pool

        # 创建测试 HTML 内容
        test_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>测试 PDF</title>
            <style>
                body { font-family: 'Microsoft YaHei', sans-serif; padding: 40px; }
                h1 { color: #2c3e50; }
                p { line-height: 1.8; }
            </style>
        </head>
        <body>
            <h1>Playwright PDF 生成测试</h1>
            <p>这是一个测试 PDF 文档，用于验证 Playwright 浏览器池功能。</p>
            <p>测试时间: 2025-12-31</p>
            <ul>
                <li>中文字体渲染测试</li>
                <li>HTML 转 PDF 功能测试</li>
                <li>浏览器池性能测试</li>
            </ul>
        </body>
        </html>
        """

        # 使用浏览器池直接生成 PDF
        pool = get_browser_pool()
        browser = await pool.get_browser()

        output_path = Path("./test_playwright_output.pdf")
        print(f"[EMOJI] 正在生成 PDF: {output_path}")

        # 创建浏览器上下文和页面
        context = await browser.new_context()
        page = await context.new_page()

        # 设置 HTML 内容
        await page.set_content(test_html, wait_until="networkidle")

        # 生成 PDF
        await page.pdf(
            path=str(output_path),
            format="A4",
            print_background=True,
            margin={"top": "20mm", "right": "20mm", "bottom": "20mm", "left": "20mm"},
        )

        # 关闭上下文（不关闭浏览器，复用）
        await context.close()

        # 验证文件
        if output_path.exists():
            file_size = output_path.stat().st_size
            print(f"[OK] PDF 生成成功!")
            print(f"   - 文件路径: {output_path.absolute()}")
            print(f"   - 文件大小: {file_size:,} bytes")
            return True
        else:
            print(f"[FAIL] PDF 文件未生成")
            return False

    except Exception as e:
        print(f"[FAIL] PDF 生成失败: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("[EMOJI] Playwright 环境修复验证测试")
    print("=" * 60)
    print(f"Python 版本: {sys.version}")
    print(f"平台: {sys.platform}")

    results = []

    # 测试1: 浏览器池初始化
    result1 = await test_browser_pool()
    results.append(("浏览器池初始化", result1))

    # 测试2: PDF 生成
    result2 = await test_pdf_generation()
    results.append(("PDF 生成功能", result2))

    # 清理
    print("\n" + "=" * 60)
    print("[EMOJI] 清理资源")
    print("=" * 60)

    try:
        from intelligent_project_analyzer.api.html_pdf_generator import get_browser_pool

        pool = get_browser_pool()
        await pool.shutdown()
        print("[OK] 浏览器池已关闭")
    except Exception as e:
        print(f"[WARN] 清理失败: {e}")

    # 输出测试报告
    print("\n" + "=" * 60)
    print("[EMOJI] 测试报告")
    print("=" * 60)

    for name, result in results:
        status = "[OK] 通过" if result else "[FAIL] 失败"
        print(f"{status} - {name}")

    all_passed = all(r for _, r in results)

    print("\n" + "=" * 60)
    if all_passed:
        print("[EMOJI] 所有测试通过！Playwright 环境已修复")
    else:
        print("[WARN] 部分测试失败，请检查上述错误信息")
    print("=" * 60)

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

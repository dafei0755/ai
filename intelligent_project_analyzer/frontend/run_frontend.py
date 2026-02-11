"""
前端启动脚本

快速启动 Streamlit 前端应用
"""

import os
import sys
import subprocess
from pathlib import Path


def main():
    """主函数"""
    # 获取当前文件所在目录
    current_dir = Path(__file__).parent
    app_file = current_dir / "app.py"
    
    # 检查 app.py 是否存在
    if not app_file.exists():
        print(" 错误: 找不到 app.py 文件")
        print(f"   预期路径: {app_file}")
        sys.exit(1)
    
    # 检查环境变量
    env_file = current_dir.parent.parent / ".env"
    if not env_file.exists():
        print("️  警告: 未找到 .env 文件")
        print(f"   预期路径: {env_file}")
        print("   请确保已配置 OPENAI_API_KEY")
        print()
    
    # 打印启动信息
    print("=" * 60)
    print("   智能项目分析系统 - Streamlit 前端")
    print("=" * 60)
    print()
    print(f" 应用路径: {app_file}")
    print(f" 访问地址: http://localhost:8501")
    print()
    print(" 提示:")
    print("   - 按 Ctrl+C 停止服务")
    print("   - 修改代码后会自动重新加载")
    print()
    print("=" * 60)
    print()
    
    # 启动 Streamlit
    try:
        subprocess.run([
            "streamlit",
            "run",
            str(app_file),
            "--server.port=8501",
            "--server.headless=false"
        ])
    except KeyboardInterrupt:
        print("\n\n 应用已停止")
    except FileNotFoundError:
        print(" 错误: 未找到 streamlit 命令")
        print("   请先安装: pip install streamlit")
        sys.exit(1)
    except Exception as e:
        print(f" 启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()


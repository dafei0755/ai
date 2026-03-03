# -*- coding: utf-8 -*-
"""
生成 CHANGELOG 的包装脚本
解决 Windows 编码问题
"""
import os
import subprocess
import sys

# 设置环境变量
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["LC_ALL"] = "zh_CN.UTF-8"

# gitchangelog 路径
GITCHANGELOG = r"C:\Users\SF\AppData\Roaming\Python\Python313\Scripts\gitchangelog.exe"


def main():
    """运行 gitchangelog"""
    try:
        # 输出文件路径（如果命令行指定）
        output_file = None
        args = sys.argv[1:]

        # 检查是否指定输出文件
        if len(args) > 0 and not args[0].startswith("-"):
            output_file = args[0]
            args = args[1:]

        # 运行 gitchangelog
        result = subprocess.run(
            [GITCHANGELOG] + args, capture_output=True, text=True, encoding="utf-8", errors="replace"  # 替换无法解码的字符
        )

        # 保存或输出结果
        if output_file:
            # 保存到文件
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(result.stdout)
            print(f"✓ CHANGELOG saved to {output_file}")
        else:
            # 输出到控制台（使用 UTF-8 BOM 避免 Windows 编码问题）
            sys.stdout.buffer.write("\ufeff".encode("utf-8"))  # UTF-8 BOM
            sys.stdout.buffer.write(result.stdout.encode("utf-8"))

        if result.stderr:
            sys.stderr.write(result.stderr)

        sys.exit(result.returncode)

    except FileNotFoundError:
        print(f"Error: gitchangelog not found at {GITCHANGELOG}")
        print("Please check the path or install gitchangelog:")
        print("  pip install gitchangelog pystache --user")
        sys.exit(1)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

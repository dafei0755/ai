"""直接测试 decouple 读取的内容"""
import sys
import os

# 确保从项目目录读取 .env
project_dir = r"d:\11-20\langgraph-design"
os.chdir(project_dir)

from decouple import config

print("=" * 60)
print("decouple 配置读取测试")
print("=" * 60)
print(f"当前工作目录: {os.getcwd()}")
print()

# 读取配置
username = config("WORDPRESS_ADMIN_USERNAME", default="NOT_FOUND")
password = config("WORDPRESS_ADMIN_PASSWORD", default="NOT_FOUND")

print(f"WORDPRESS_ADMIN_USERNAME = {username}")
print(f"WORDPRESS_ADMIN_PASSWORD = {password}")
print(f"密码长度 = {len(password)} 字符")

# 显示密码的详细信息
if password != "NOT_FOUND":
    print(f"\n密码详细分析:")
    print(f"  首尾3字符: {password[:3]}...{password[-3:]}")
    print(f"  是否以单引号开头: {password.startswith(chr(39))}")
    print(f"  是否以单引号结尾: {password.endswith(chr(39))}")
    print(f"  包含特殊字符 % : {'%' in password}")
    print(f"  包含特殊字符 @ : {'@' in password}")
    print(f"  包含特殊字符 # : {'#' in password}")
    print(f"  包含特殊字符 & : {'&' in password}")
    print(f"  包含特殊字符 ! : {'!' in password}")

    # 显示 ASCII 值以调试不可见字符
    print(f"\n密码前5个字符的 ASCII 值:")
    for i, char in enumerate(password[:5]):
        print(f"  [{i}] '{char}' = ASCII {ord(char)}")

print("=" * 60)

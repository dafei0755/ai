"""快速检查 DeepSeek API Key 配置"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

key = os.getenv("DEEPSEEK_API_KEY", "")

if not key:
    print("❌ DEEPSEEK_API_KEY 未设置")
elif key.startswith("your_"):
    print(f"⚠️ DEEPSEEK_API_KEY 是占位符: {key}")
elif key.startswith("sk-"):
    print(f"✅ DEEPSEEK_API_KEY 已配置 (sk-...{key[-8:]})")
else:
    print(f"❓ DEEPSEEK_API_KEY 格式不明: {key[:10]}...")

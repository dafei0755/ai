"""
验证API Key泄露清理
"""
import os
import sys
from pathlib import Path

# 设置UTF-8输出
if sys.platform == "win32":
    import codecs

    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

# 泄露的keys (已撤销)
leaked_keys = ["sk-or-v1-[REDACTED-ALREADY-REVOKED-KEY-1]", "sk-or-v1-[REDACTED-ALREADY-REVOKED-KEY-2]"]

print("=" * 80)
print("验证API Key泄露清理")
print("=" * 80)

# 排除的目录
exclude_dirs = {".git", "__pycache__", "node_modules", ".next", "venv", "env"}

found_leaks = []

for root, dirs, files in os.walk("."):
    # 排除特定目录
    dirs[:] = [d for d in dirs if d not in exclude_dirs]

    for file in files:
        # 只检查文本文件
        if file.endswith((".py", ".md", ".txt", ".env", ".json", ".yaml", ".yml", ".sh", ".bat")):
            file_path = os.path.join(root, file)

            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                    for key in leaked_keys:
                        if key in content:
                            found_leaks.append((file_path, key))

            except Exception as e:
                pass

if found_leaks:
    print("\n❌ 发现泄露的keys:\n")
    for file_path, key in found_leaks:
        print(f"   文件: {file_path}")
        print(f"   Key: {key[:20]}...{key[-10:]}\n")
else:
    print("\n✅ 工作目录已清理，未发现泄露的keys")

print("\n" + "=" * 80)
print("检查完成")
print("=" * 80)

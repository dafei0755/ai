#!/usr/bin/env python3
"""
更新搜索配置脚本 - v7.237
自动将专业搜索模式配置添加到 .env 文件中
"""

import os
import sys


def update_env_config():
    """更新 .env 配置文件"""
    env_file = ".env"

    # 需要添加的配置
    search_configs = [
        "# 🆕 v7.237: 专业搜索质量优化配置",
        "ENABLE_DESIGN_PROFESSIONAL_MODE=true",
        "MIN_SEARCH_RELEVANCE=0.75",
        "PRIORITIZE_CASE_STUDIES=true",
        "ENHANCE_SCENARIO_KEYWORDS=true",
        "FILTER_COMMERCIAL_CONTENT=true",
        "",
    ]

    if not os.path.exists(env_file):
        print(f"❌ 错误: {env_file} 文件不存在")
        return False

    # 读取现有配置
    with open(env_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 检查是否已存在配置
    has_config = any("ENABLE_DESIGN_PROFESSIONAL_MODE" in line for line in lines)

    if has_config:
        print("✅ 专业搜索配置已存在，无需重复添加")
        return True

    # 寻找插入位置（在 LLM 配置之后）
    insert_index = 0
    for i, line in enumerate(lines):
        if "LLM 配置" in line or "# 🔧 LLM" in line:
            # 找到下一个空行或配置段
            for j in range(i + 1, len(lines)):
                if lines[j].strip() == "" or lines[j].startswith("#"):
                    insert_index = j + 1
                    break
            break

    # 如果没找到合适位置，添加到文件开头
    if insert_index == 0:
        insert_index = 3

    # 插入新配置
    for config in reversed(search_configs):
        lines.insert(insert_index, config + "\n")

    # 写回文件
    with open(env_file, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print("✅ 专业搜索配置已添加到 .env 文件")
    return True


def main():
    print("🔧 [v7.237] 更新搜索质量配置...")

    if update_env_config():
        print("\n🎉 配置更新完成！")
        print("📋 已添加的配置项:")
        print("  - ENABLE_DESIGN_PROFESSIONAL_MODE=true")
        print("  - MIN_SEARCH_RELEVANCE=0.75")
        print("  - PRIORITIZE_CASE_STUDIES=true")
        print("  - ENHANCE_SCENARIO_KEYWORDS=true")
        print("  - FILTER_COMMERCIAL_CONTENT=true")
        print("\n🚀 重启服务后配置将生效")
    else:
        print("❌ 配置更新失败")
        sys.exit(1)


if __name__ == "__main__":
    main()

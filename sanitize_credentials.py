#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""批量脱敏文档中的真实凭证"""

import os
from pathlib import Path

# 凭证映射
REPLACEMENTS = {
    '8pdwoxj8': 'YOUR_WORDPRESS_USERNAME',
    'M2euRVQMdpzJp%*KLtD0#kK1': 'YOUR_WORDPRESS_PASSWORD',
    '$d4@5fg54ll_t_45gH': 'YOUR_JWT_SECRET_KEY',
}

def sanitize_file(file_path):
    """脱敏单个文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        for old_value, new_value in REPLACEMENTS.items():
            content = content.replace(old_value, new_value)

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"[OK] Sanitized: {file_path.name}")
            return True
        return False
    except Exception as e:
        print(f"[ERROR] Failed {file_path.name}: {e}")
        return False

def main():
    """主函数"""
    base_path = Path(__file__).parent
    processed_count = 0

    # 查找所有 .md 文件
    for md_file in base_path.rglob('*.md'):
        if sanitize_file(md_file):
            processed_count += 1

    print(f"\n[OK] Completed! Processed {processed_count} files")

if __name__ == "__main__":
    main()

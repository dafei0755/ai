# 🤖 自动化修复记录系统

> 从机制上确保每次修复（成功或失败）都被记录，避免重复犯错

---

## 📋 系统概述

**目标**: 建立自动化机制，记录每次代码修复的完整上下文，无论成功与否，形成可检索的知识库，供后续参考。

**核心原则**:
- ✅ **全量记录**: 成功和失败的修复都记录
- 🔍 **可检索**: 通过错误类型、文件路径快速查找
- 📊 **结构化**: 统一的数据格式，便于分析
- 🔄 **持续学习**: AI助手和开发者都能从历史中学习

---

## 🏗️ 系统架构

```
┌─────────────────┐
│  代码修复开始    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 自动捕获上下文   │ ← Git commit info, error logs, 修复前代码
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  执行修复操作    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  自动化测试验证  │ ← pytest, 代码检查, 服务启动测试
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌───────┐ ┌───────┐
│ 成功  │ │ 失败  │
└───┬───┘ └───┬───┘
    │         │
    └────┬────┘
         │
         ▼
┌─────────────────┐
│ 记录到知识库    │ ← .github/historical_fixes/*.md + fixes_db.json
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 更新文档索引    │ ← CHANGELOG.md, README.md, 索引文件
└─────────────────┘
```

---

## 📁 文件结构

```
.github/
├── historical_fixes/          # 详细修复案例文档
│   ├── index.json            # 索引文件（可搜索）
│   ├── 2026-01-02_dimension_selector_special_scenes_fix.md
│   └── 2026-01-02_unicode_encoding_fix.md
├── failed_fixes/             # 失败的修复尝试（同样重要！）
│   ├── index.json
│   └── 2026-01-02_attempt1_wrong_approach.md
├── scripts/
│   ├── record_fix.py         # 记录修复的脚本
│   ├── validate_fix.py       # 验证修复的脚本
│   └── search_fix.py         # 搜索历史修复的工具
└── AUTOMATED_FIX_RECORDING_SYSTEM.md  # 本文档
```

---

## 🔧 实施方案

### 方案 1: Git Pre-commit Hook（推荐）

**触发时机**: 每次 `git commit` 前

**工作流程**:
1. 检测 commit message 中的关键词（如 `fix:`, `bugfix:`, `修复:`）
2. 自动提取相关信息：
   - 修改的文件列表
   - 代码 diff
   - 相关的错误日志（从最近的日志文件）
3. 运行自动化测试
4. 生成结构化记录

**实现代码**:

```bash
# .git/hooks/pre-commit
#!/bin/bash

# 检查 commit message 是否包含修复关键词
COMMIT_MSG=$(git log -1 --pretty=%B)

if [[ $COMMIT_MSG =~ (fix:|bugfix:|修复:) ]]; then
    echo "🔍 检测到修复提交，开始记录..."

    # 调用记录脚本
    python .github/scripts/record_fix.py \
        --commit-msg "$COMMIT_MSG" \
        --changed-files "$(git diff --cached --name-only)" \
        --diff "$(git diff --cached)"

    # 运行测试验证
    python .github/scripts/validate_fix.py

    if [ $? -ne 0 ]; then
        echo "⚠️ 修复验证失败，但仍将记录此次尝试"
        python .github/scripts/record_fix.py --status failed
    else
        echo "✅ 修复验证通过"
        python .github/scripts/record_fix.py --status success
    fi
fi
```

### 方案 2: GitHub Actions 自动化（适合团队）

**触发时机**: Push 到仓库后

**.github/workflows/record_fix.yml**:

```yaml
name: Record Fix

on:
  push:
    branches: [ main, develop, 'fix/**' ]

jobs:
  record:
    runs-on: ubuntu-latest
    if: contains(github.event.head_commit.message, 'fix:') || contains(github.event.head_commit.message, '修复:')

    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 2  # 获取前一个 commit 用于 diff

      - name: Extract Fix Context
        run: |
          echo "Commit: ${{ github.event.head_commit.message }}"
          git diff HEAD~1 HEAD > fix.diff

      - name: Run Tests
        id: test
        continue-on-error: true
        run: |
          python -m pytest tests/ -v

      - name: Record Fix
        env:
          FIX_STATUS: ${{ steps.test.outcome }}
        run: |
          python .github/scripts/record_fix.py \
            --commit "${{ github.sha }}" \
            --message "${{ github.event.head_commit.message }}" \
            --author "${{ github.event.head_commit.author.name }}" \
            --status "$FIX_STATUS" \
            --diff-file fix.diff

      - name: Update Documentation
        if: steps.test.outcome == 'success'
        run: |
          python .github/scripts/update_docs.py \
            --version-bump patch \
            --changelog-entry "$(cat .github/temp_fix_record.md)"

      - name: Commit Documentation Updates
        if: steps.test.outcome == 'success'
        run: |
          git config user.name "Fix Recorder Bot"
          git config user.email "bot@example.com"
          git add CHANGELOG.md README.md .github/historical_fixes/
          git commit -m "docs: auto-record fix from ${{ github.sha }}"
          git push
```

### 方案 3: Python 装饰器（代码级别）

**适用场景**: 在代码中自动记录修复逻辑

```python
# intelligent_project_analyzer/utils/fix_recorder.py

import functools
import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

class FixRecorder:
    """修复记录器装饰器"""

    FIXES_DIR = Path(".github/historical_fixes")
    FAILURES_DIR = Path(".github/failed_fixes")

    @staticmethod
    def record(
        issue_id: str,
        description: str,
        related_files: list[str] = None
    ):
        """
        装饰器：自动记录函数执行结果

        用法:
            @FixRecorder.record(
                issue_id="dimension_selector_param",
                description="修复 special_scenes 参数不匹配",
                related_files=["services/dimension_selector.py"]
            )
            def fix_dimension_selector():
                # 修复代码
                pass
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                start_time = datetime.now()
                context = {
                    "issue_id": issue_id,
                    "description": description,
                    "function": func.__name__,
                    "related_files": related_files or [],
                    "start_time": start_time.isoformat(),
                }

                try:
                    # 执行修复
                    result = func(*args, **kwargs)

                    # 记录成功
                    end_time = datetime.now()
                    context.update({
                        "status": "success",
                        "end_time": end_time.isoformat(),
                        "duration": (end_time - start_time).total_seconds(),
                        "result": str(result)[:500]  # 限制长度
                    })

                    FixRecorder._save_record(context, success=True)
                    return result

                except Exception as e:
                    # 记录失败
                    end_time = datetime.now()
                    context.update({
                        "status": "failed",
                        "end_time": end_time.isoformat(),
                        "duration": (end_time - start_time).total_seconds(),
                        "error": str(e),
                        "traceback": traceback.format_exc()
                    })

                    FixRecorder._save_record(context, success=False)
                    raise  # 重新抛出异常

            return wrapper
        return decorator

    @staticmethod
    def _save_record(context: dict, success: bool):
        """保存记录到文件"""
        target_dir = FixRecorder.FIXES_DIR if success else FixRecorder.FAILURES_DIR
        target_dir.mkdir(parents=True, exist_ok=True)

        # 生成文件名
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"{date_str}_{context['issue_id']}.json"
        filepath = target_dir / filename

        # 保存 JSON
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(context, f, indent=2, ensure_ascii=False)

        # 同时生成 Markdown 文档（可选）
        md_content = FixRecorder._generate_markdown(context)
        md_filepath = filepath.with_suffix('.md')
        with open(md_filepath, 'w', encoding='utf-8') as f:
            f.write(md_content)

        print(f"{'✅' if success else '❌'} Fix record saved: {filepath}")

    @staticmethod
    def _generate_markdown(context: dict) -> str:
        """生成 Markdown 格式的文档"""
        status_emoji = "✅" if context["status"] == "success" else "❌"

        return f"""# {status_emoji} {context['description']}

**Issue ID**: {context['issue_id']}
**Status**: {context['status']}
**Date**: {context['start_time']}
**Duration**: {context.get('duration', 0):.2f}s

## 相关文件

{chr(10).join(f"- `{f}`" for f in context['related_files'])}

## 执行函数

`{context['function']}()`

## 结果

{'**Success**: ' + context.get('result', 'N/A') if context['status'] == 'success' else '**Error**: ' + context.get('error', 'N/A')}

{'## Traceback' if context['status'] == 'failed' else ''}
{'```' if context['status'] == 'failed' else ''}
{context.get('traceback', '') if context['status'] == 'failed' else ''}
{'```' if context['status'] == 'failed' else ''}
"""


# 使用示例
@FixRecorder.record(
    issue_id="dimension_selector_special_scenes",
    description="添加 special_scenes 参数到 DimensionSelector",
    related_files=[
        "services/dimension_selector.py",
        "services/adaptive_dimension_generator.py"
    ]
)
def fix_dimension_selector_parameters():
    """修复维度选择器参数不匹配问题"""
    # 实际修复代码
    pass
```

---

## 📊 记录模板

### 成功修复记录模板

```markdown
# ✅ [Fix Title]

**Issue ID**: `fix-2026-01-02-001`
**Date**: 2026-01-02
**Status**: ✅ Success
**Author**: AI Assistant / Developer Name
**Duration**: 5m 30s

---

## 📋 问题描述

[简短描述问题现象]

**错误日志**:
```
[粘贴完整错误日志]
```

---

## 🔍 根因分析

[详细分析问题原因]

**涉及组件**:
- Component A
- Component B

**触发条件**:
- Condition 1
- Condition 2

---

## 🔧 修复方案

### 方案选择

考虑了以下方案：

1. **方案 A** ❌
   - 优点：...
   - 缺点：...
   - 为什么没选：...

2. **方案 B** ✅ (采用)
   - 优点：...
   - 缺点：...
   - 为什么选择：...

### 实施步骤

1. Step 1: ...
2. Step 2: ...
3. Step 3: ...

---

## 📝 代码变更

### 修改的文件

- `path/to/file1.py` (新增 50 行, 修改 10 行)
- `path/to/file2.py` (修改 5 行)

### 关键代码片段

```python
# 修复前
def old_function(param1):
    pass

# 修复后
def new_function(param1, param2=None):  # 新增参数
    if param2:
        # 新增逻辑
        pass
    pass
```

---

## ✅ 验证结果

### 自动化测试

```bash
pytest tests/ -v
# 结果：25 passed, 0 failed
```

### 手动测试

- [ ] 场景 1: 通过
- [ ] 场景 2: 通过
- [ ] 场景 3: 通过

### 性能影响

- 响应时间：无明显影响
- 内存占用：增加 ~2MB（可接受）

---

## 📚 经验教训

### 技术要点

- 要点 1: 接口设计时要考虑扩展性
- 要点 2: 添加详细日志便于调试

### 避坑指南

⚠️ **注意**: 在修改公共方法签名时，务必检查所有调用点

### 最佳实践

- 新增参数应设为可选（默认值），保持向后兼容
- 添加参数时同步更新文档字符串

---

## 🔗 相关资源

- Issue: #123
- PR: #456
- 相关文档: [link]
- 相关修复: fix-2026-01-01-005

---

## 🏷️ 标签

`parameter-mismatch` `interface-compatibility` `dimension-selector` `questionnaire`
```

### 失败修复记录模板

```markdown
# ❌ [Attempted Fix Title]

**Issue ID**: `fail-2026-01-02-001`
**Date**: 2026-01-02
**Status**: ❌ Failed
**Author**: AI Assistant / Developer Name
**Duration**: 10m

---

## 📋 问题描述

[描述要解决的问题]

---

## 🔧 尝试的方案

[描述尝试的修复方案]

### 实施步骤

1. Step 1: ...
2. Step 2: ...
3. Step 3: 在此步骤失败 ❌

---

## ❌ 失败原因

**错误信息**:
```
[错误日志]
```

**分析**:
- 原因 1: ...
- 原因 2: ...

---

## 💡 收获

### 这次尝试教会了我们什么

- 教训 1: ...
- 教训 2: ...

### 为什么这个方案不可行

- 原因 1: ...
- 原因 2: ...

### 建议的替代方案

- 方案 A: ...
- 方案 B: ...

---

## 🔗 相关资源

- 后续成功修复: fix-2026-01-02-002
```

---

## 🔍 检索和查询系统

### 索引文件格式

**.github/historical_fixes/index.json**:

```json
{
  "version": "1.0",
  "last_updated": "2026-01-02T16:00:00",
  "total_fixes": 156,
  "total_failures": 23,
  "fixes": [
    {
      "id": "fix-2026-01-02-001",
      "title": "DimensionSelector Special Scenes Parameter Missing",
      "date": "2026-01-02",
      "status": "success",
      "tags": ["parameter-mismatch", "interface-compatibility"],
      "files": [
        "intelligent_project_analyzer/services/dimension_selector.py",
        "intelligent_project_analyzer/services/adaptive_dimension_generator.py"
      ],
      "error_type": "TypeError",
      "error_message": "got an unexpected keyword argument 'special_scenes'",
      "path": ".github/historical_fixes/2026-01-02_dimension_selector_special_scenes_fix.md"
    }
  ]
}
```

### 搜索脚本

**.github/scripts/search_fix.py**:

```python
#!/usr/bin/env python3
"""
搜索历史修复记录

用法:
    python search_fix.py --error "TypeError"
    python search_fix.py --file "dimension_selector.py"
    python search_fix.py --tag "parameter-mismatch"
    python search_fix.py --keyword "special_scenes"
"""

import json
import argparse
from pathlib import Path
from typing import List, Dict

def load_index() -> Dict:
    """加载索引文件"""
    index_path = Path(".github/historical_fixes/index.json")
    if not index_path.exists():
        return {"fixes": []}

    with open(index_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def search_fixes(
    error_type: str = None,
    file_pattern: str = None,
    tag: str = None,
    keyword: str = None
) -> List[Dict]:
    """搜索修复记录"""
    index = load_index()
    results = []

    for fix in index.get("fixes", []):
        match = True

        if error_type and fix.get("error_type") != error_type:
            match = False

        if file_pattern:
            if not any(file_pattern in f for f in fix.get("files", [])):
                match = False

        if tag and tag not in fix.get("tags", []):
            match = False

        if keyword:
            text = json.dumps(fix).lower()
            if keyword.lower() not in text:
                match = False

        if match:
            results.append(fix)

    return results

def main():
    parser = argparse.ArgumentParser(description="搜索历史修复记录")
    parser.add_argument("--error", help="错误类型 (如 TypeError)")
    parser.add_argument("--file", help="文件路径模式")
    parser.add_argument("--tag", help="标签")
    parser.add_argument("--keyword", help="关键词")

    args = parser.parse_args()

    results = search_fixes(
        error_type=args.error,
        file_pattern=args.file,
        tag=args.tag,
        keyword=args.keyword
    )

    if not results:
        print("❌ 未找到匹配的修复记录")
        return

    print(f"✅ 找到 {len(results)} 条记录:\n")

    for i, fix in enumerate(results, 1):
        print(f"{i}. [{fix['status']}] {fix['title']}")
        print(f"   日期: {fix['date']}")
        print(f"   文件: {', '.join(fix['files'][:2])}")
        print(f"   路径: {fix['path']}\n")

if __name__ == "__main__":
    main()
```

---

## 🤖 AI 助手集成

### 在 AI 对话中自动引用历史修复

**.github/ai_context/fix_history_prompt.md**:

```markdown
# AI 助手上下文：历史修复记录

在处理代码问题前，请先执行以下步骤：

1. **搜索相似问题**:
   ```bash
   python .github/scripts/search_fix.py --keyword "[错误关键词]"
   ```

2. **查看相关修复**:
   - 阅读匹配的修复文档
   - 了解之前的解决方案
   - 注意"失败的尝试"，避免重蹈覆辙

3. **记录新修复**:
   - 使用 `@FixRecorder.record()` 装饰器
   - 或手动创建修复文档
   - 更新 CHANGELOG.md

4. **验证修复**:
   - 运行自动化测试
   - 检查服务是否正常启动
   - 验证相关功能

5. **更新索引**:
   ```bash
   python .github/scripts/update_index.py
   ```
```

### VS Code 集成

**.vscode/tasks.json**:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Search Fix History",
      "type": "shell",
      "command": "python",
      "args": [
        ".github/scripts/search_fix.py",
        "--keyword",
        "${input:searchKeyword}"
      ],
      "problemMatcher": []
    },
    {
      "label": "Record Current Fix",
      "type": "shell",
      "command": "python",
      "args": [
        ".github/scripts/record_fix.py",
        "--interactive"
      ],
      "problemMatcher": []
    }
  ],
  "inputs": [
    {
      "id": "searchKeyword",
      "type": "promptString",
      "description": "输入搜索关键词"
    }
  ]
}
```

---

## 📈 数据分析和洞察

### 统计脚本

**.github/scripts/analyze_fixes.py**:

```python
#!/usr/bin/env python3
"""
分析修复记录，生成统计报告

输出:
- 最常见的错误类型
- 最频繁修改的文件
- 修复成功率
- 平均修复时间
"""

import json
from pathlib import Path
from collections import Counter
from datetime import datetime

def analyze():
    index = json.load(open(".github/historical_fixes/index.json"))
    fixes = index.get("fixes", [])

    # 统计错误类型
    error_types = Counter(f.get("error_type") for f in fixes if f.get("error_type"))

    # 统计文件
    all_files = []
    for f in fixes:
        all_files.extend(f.get("files", []))
    frequent_files = Counter(all_files)

    # 统计成功率
    total = len(fixes)
    success = sum(1 for f in fixes if f.get("status") == "success")

    # 生成报告
    report = f"""
# 📊 修复记录分析报告

**生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 总体统计

- 总修复次数: {total}
- 成功次数: {success}
- 失败次数: {total - success}
- 成功率: {success/total*100:.1f}%

## Top 5 错误类型

{chr(10).join(f"{i+1}. {err}: {count}次" for i, (err, count) in enumerate(error_types.most_common(5)))}

## Top 5 频繁修改文件

{chr(10).join(f"{i+1}. {file}: {count}次" for i, (file, count) in enumerate(frequent_files.most_common(5)))}

## 建议

- ⚠️ 重点关注高频错误类型和文件
- 📚 为高频问题创建专门的文档和工具
- 🔧 考虑重构频繁修改的文件
"""

    print(report)

    # 保存报告
    with open(".github/fix_analysis_report.md", 'w', encoding='utf-8') as f:
        f.write(report)

if __name__ == "__main__":
    analyze()
```

---

## 🚀 快速开始

### 1. 初始化系统

```bash
# 创建必要的目录
mkdir -p .github/historical_fixes
mkdir -p .github/failed_fixes
mkdir -p .github/scripts

# 复制脚本文件
cp templates/record_fix.py .github/scripts/
cp templates/search_fix.py .github/scripts/
cp templates/update_index.py .github/scripts/

# 初始化索引文件
echo '{"version": "1.0", "fixes": []}' > .github/historical_fixes/index.json
```

### 2. 配置 Git Hook（可选）

```bash
# 复制 pre-commit hook
cp .github/hooks/pre-commit .git/hooks/
chmod +x .git/hooks/pre-commit
```

### 3. 记录第一个修复

```bash
# 手动记录
python .github/scripts/record_fix.py \
  --issue-id "first-fix" \
  --description "初始化修复记录系统" \
  --status success

# 或使用装饰器（在代码中）
@FixRecorder.record(issue_id="...", description="...")
def my_fix():
    pass
```

### 4. 搜索历史修复

```bash
# 按错误类型搜索
python .github/scripts/search_fix.py --error TypeError

# 按文件搜索
python .github/scripts/search_fix.py --file dimension_selector

# 按关键词搜索
python .github/scripts/search_fix.py --keyword "special_scenes"
```

---

## 🎯 最佳实践

### DO ✅

1. **每次修复都记录**，无论成功与否
2. **详细记录失败尝试**，这些同样宝贵
3. **使用结构化模板**，保持一致性
4. **及时更新索引**，确保可搜索性
5. **定期分析数据**，发现模式和趋势
6. **在 PR 中引用相关修复**，建立关联

### DON'T ❌

1. ❌ 不要只记录成功的修复
2. ❌ 不要用模糊的描述
3. ❌ 不要忘记更新 CHANGELOG
4. ❌ 不要跳过验证步骤
5. ❌ 不要孤立地看待每个修复

---

## 🔮 未来扩展

### Phase 2: AI 辅助分析

- [ ] 使用 LLM 自动分析修复模式
- [ ] 智能推荐相似问题的解决方案
- [ ] 自动生成修复文档

### Phase 3: 实时监控

- [ ] 集成 Sentry/Loguru 实时捕获错误
- [ ] 自动匹配历史修复记录
- [ ] 推送通知到开发者

### Phase 4: 知识图谱

- [ ] 构建错误-修复-组件关系图谱
- [ ] 可视化展示系统薄弱点
- [ ] 预测性维护建议

---

## 📞 联系和反馈

如有问题或建议，请提交 Issue 或 PR。

**维护者**: AI Assistant Team
**最后更新**: 2026-01-02
